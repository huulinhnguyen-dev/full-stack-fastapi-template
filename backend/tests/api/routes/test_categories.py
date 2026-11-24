import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, func, select

from app import crud
from app.core.config import settings
from app.models import Category, ItemCreate
from tests.utils.category import create_random_category
from tests.utils.utils import random_lower_string


def get_user_id(db: Session, email: str) -> str:
    user = crud.get_user_by_email(session=db, email=email)
    assert user is not None
    return str(user.id)


def test_create_category(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    name = random_lower_string()
    response = client.post(
        f"{settings.API_V1_STR}/categories/",
        headers=normal_user_token_headers,
        json={"name": f"  {name}  "},
    )
    assert response.status_code == 200
    content = response.json()
    assert content["name"] == name
    assert content["owner_id"] == get_user_id(db, settings.EMAIL_TEST_USER)
    assert "id" in content
    assert "created_at" in content


def test_create_category_duplicate_name(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    name = f"Work {random_lower_string()}"
    response = client.post(
        f"{settings.API_V1_STR}/categories/",
        headers=normal_user_token_headers,
        json={"name": name},
    )
    assert response.status_code == 200
    response = client.post(
        f"{settings.API_V1_STR}/categories/",
        headers=normal_user_token_headers,
        json={"name": name.upper()},
    )
    assert response.status_code == 409
    content = response.json()
    assert content["detail"] == "A category with this name already exists"


def test_create_category_duplicate_race(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    name = random_lower_string()
    response = client.post(
        f"{settings.API_V1_STR}/categories/",
        headers=normal_user_token_headers,
        json={"name": name},
    )
    assert response.status_code == 200
    # Simulate a concurrent create that slips past the duplicate check
    monkeypatch.setattr(crud, "get_category_by_name", lambda **_: None)
    response = client.post(
        f"{settings.API_V1_STR}/categories/",
        headers=normal_user_token_headers,
        json={"name": name},
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "A category with this name already exists"


def test_create_category_same_name_as_other_user(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    other_category = create_random_category(db)
    response = client.post(
        f"{settings.API_V1_STR}/categories/",
        headers=normal_user_token_headers,
        json={"name": other_category.name},
    )
    assert response.status_code == 200


def test_create_category_invalid_name(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    for data in ({"name": "   "}, {"name": "x" * 256}, {}):
        response = client.post(
            f"{settings.API_V1_STR}/categories/",
            headers=normal_user_token_headers,
            json=data,
        )
        assert response.status_code == 422


def test_categories_require_authentication(client: TestClient) -> None:
    response = client.get(f"{settings.API_V1_STR}/categories/")
    assert response.status_code == 401
    response = client.post(f"{settings.API_V1_STR}/categories/", json={"name": "Work"})
    assert response.status_code == 401


def test_read_categories_invalid_query(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/categories/?skip=abc",
        headers=normal_user_token_headers,
    )
    assert response.status_code == 422


def test_read_categories_own_sorted(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    tag = random_lower_string()
    for name in (f"{tag} b", f"{tag} A", f"{tag} c"):
        response = client.post(
            f"{settings.API_V1_STR}/categories/",
            headers=normal_user_token_headers,
            json={"name": name},
        )
        assert response.status_code == 200
    other_category = create_random_category(db)

    response = client.get(
        f"{settings.API_V1_STR}/categories/",
        headers=normal_user_token_headers,
    )
    assert response.status_code == 200
    content = response.json()
    names = [category["name"] for category in content["data"]]
    assert [name for name in names if name.startswith(tag)] == [
        f"{tag} A",
        f"{tag} b",
        f"{tag} c",
    ]
    assert other_category.name not in names
    owner_id = get_user_id(db, settings.EMAIL_TEST_USER)
    assert all(category["owner_id"] == owner_id for category in content["data"])
    count = db.exec(
        select(func.count()).select_from(Category).where(Category.owner_id == owner_id)
    ).one()
    assert content["count"] == count


def test_read_categories_superuser_sees_only_own(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    normal_user_token_headers: dict[str, str],
) -> None:
    name = random_lower_string()
    response = client.post(
        f"{settings.API_V1_STR}/categories/",
        headers=normal_user_token_headers,
        json={"name": name},
    )
    assert response.status_code == 200
    response = client.get(
        f"{settings.API_V1_STR}/categories/",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    names = [category["name"] for category in response.json()["data"]]
    assert name not in names


def test_delete_category(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    owner_id = uuid.UUID(get_user_id(db, settings.EMAIL_TEST_USER))
    category = create_random_category(db, owner_id=owner_id)
    response = client.delete(
        f"{settings.API_V1_STR}/categories/{category.id}",
        headers=normal_user_token_headers,
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Category deleted successfully"
    response = client.get(
        f"{settings.API_V1_STR}/categories/",
        headers=normal_user_token_headers,
    )
    ids = [c["id"] for c in response.json()["data"]]
    assert str(category.id) not in ids


def test_delete_category_in_use_keeps_items(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    owner_id = uuid.UUID(get_user_id(db, settings.EMAIL_TEST_USER))
    category = create_random_category(db, owner_id=owner_id)
    items = [
        crud.create_item(
            session=db,
            item_in=ItemCreate(title=random_lower_string(), category_id=category.id),
            owner_id=owner_id,
        )
        for _ in range(2)
    ]
    response = client.delete(
        f"{settings.API_V1_STR}/categories/{category.id}",
        headers=normal_user_token_headers,
    )
    assert response.status_code == 200
    for item in items:
        response = client.get(
            f"{settings.API_V1_STR}/items/{item.id}",
            headers=normal_user_token_headers,
        )
        assert response.status_code == 200
        assert response.json()["category_id"] is None


def test_delete_category_not_found(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    response = client.delete(
        f"{settings.API_V1_STR}/categories/{uuid.uuid4()}",
        headers=normal_user_token_headers,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Category not found"


def test_delete_category_not_enough_permissions(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    superuser_token_headers: dict[str, str],
    db: Session,
) -> None:
    category = create_random_category(db)
    # No superuser exception: categories are personal
    for headers in (normal_user_token_headers, superuser_token_headers):
        response = client.delete(
            f"{settings.API_V1_STR}/categories/{category.id}",
            headers=headers,
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Not enough permissions"
    assert db.get(Category, category.id) is not None


def test_delete_category_invalid_input(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    response = client.delete(
        f"{settings.API_V1_STR}/categories/not-a-uuid",
        headers=normal_user_token_headers,
    )
    assert response.status_code == 422


def test_delete_category_requires_authentication(
    client: TestClient, db: Session
) -> None:
    category = create_random_category(db)
    response = client.delete(f"{settings.API_V1_STR}/categories/{category.id}")
    assert response.status_code == 401
