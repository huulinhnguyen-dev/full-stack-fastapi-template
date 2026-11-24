import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.models import Category, Item, ItemCreate
from tests.utils.category import create_random_category
from tests.utils.item import create_random_item
from tests.utils.utils import random_lower_string


def get_user_id(db: Session, email: str) -> uuid.UUID:
    user = crud.get_user_by_email(session=db, email=email)
    assert user is not None
    return user.id


def create_item_with_category(db: Session, category: Category) -> Item:
    item_in = ItemCreate(title=random_lower_string(), category_id=category.id)
    return crud.create_item(session=db, item_in=item_in, owner_id=category.owner_id)


def test_create_item(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    data = {"title": "Foo", "description": "Fighters"}
    response = client.post(
        f"{settings.API_V1_STR}/items/",
        headers=superuser_token_headers,
        json=data,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["title"] == data["title"]
    assert content["description"] == data["description"]
    assert "id" in content
    assert "owner_id" in content


def test_read_item(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    item = create_random_item(db)
    response = client.get(
        f"{settings.API_V1_STR}/items/{item.id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["title"] == item.title
    assert content["description"] == item.description
    assert content["id"] == str(item.id)
    assert content["owner_id"] == str(item.owner_id)


def test_read_item_not_found(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/items/{uuid.uuid4()}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 404
    content = response.json()
    assert content["detail"] == "Item not found"


def test_read_item_not_enough_permissions(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    item = create_random_item(db)
    response = client.get(
        f"{settings.API_V1_STR}/items/{item.id}",
        headers=normal_user_token_headers,
    )
    assert response.status_code == 403
    content = response.json()
    assert content["detail"] == "Not enough permissions"


def test_read_items(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    create_random_item(db)
    create_random_item(db)
    response = client.get(
        f"{settings.API_V1_STR}/items/",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    content = response.json()
    assert len(content["data"]) >= 2


def test_update_item(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    item = create_random_item(db)
    data = {"title": "Updated title", "description": "Updated description"}
    response = client.put(
        f"{settings.API_V1_STR}/items/{item.id}",
        headers=superuser_token_headers,
        json=data,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["title"] == data["title"]
    assert content["description"] == data["description"]
    assert content["id"] == str(item.id)
    assert content["owner_id"] == str(item.owner_id)


def test_update_item_not_found(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    data = {"title": "Updated title", "description": "Updated description"}
    response = client.put(
        f"{settings.API_V1_STR}/items/{uuid.uuid4()}",
        headers=superuser_token_headers,
        json=data,
    )
    assert response.status_code == 404
    content = response.json()
    assert content["detail"] == "Item not found"


def test_update_item_not_enough_permissions(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    item = create_random_item(db)
    data = {"title": "Updated title", "description": "Updated description"}
    response = client.put(
        f"{settings.API_V1_STR}/items/{item.id}",
        headers=normal_user_token_headers,
        json=data,
    )
    assert response.status_code == 403
    content = response.json()
    assert content["detail"] == "Not enough permissions"


def test_delete_item(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    item = create_random_item(db)
    response = client.delete(
        f"{settings.API_V1_STR}/items/{item.id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["message"] == "Item deleted successfully"


def test_delete_item_not_found(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.delete(
        f"{settings.API_V1_STR}/items/{uuid.uuid4()}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 404
    content = response.json()
    assert content["detail"] == "Item not found"


def test_delete_item_not_enough_permissions(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    item = create_random_item(db)
    response = client.delete(
        f"{settings.API_V1_STR}/items/{item.id}",
        headers=normal_user_token_headers,
    )
    assert response.status_code == 403
    content = response.json()
    assert content["detail"] == "Not enough permissions"


def test_create_item_with_category(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    owner_id = get_user_id(db, settings.EMAIL_TEST_USER)
    category = create_random_category(db, owner_id=owner_id)
    data = {"title": "Foo", "category_id": str(category.id)}
    response = client.post(
        f"{settings.API_V1_STR}/items/",
        headers=normal_user_token_headers,
        json=data,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["category_id"] == str(category.id)
    assert content["category"]["name"] == category.name


def test_create_item_without_category(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    response = client.post(
        f"{settings.API_V1_STR}/items/",
        headers=normal_user_token_headers,
        json={"title": "Foo"},
    )
    assert response.status_code == 200
    content = response.json()
    assert content["category_id"] is None
    assert content["category"] is None


def test_create_item_category_not_found(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    other_category = create_random_category(db)
    for category_id in (uuid.uuid4(), other_category.id):
        response = client.post(
            f"{settings.API_V1_STR}/items/",
            headers=normal_user_token_headers,
            json={"title": "Foo", "category_id": str(category_id)},
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Category not found"


def test_update_item_set_and_change_category(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    owner_id = get_user_id(db, settings.EMAIL_TEST_USER)
    item = crud.create_item(
        session=db, item_in=ItemCreate(title="Foo"), owner_id=owner_id
    )
    first = create_random_category(db, owner_id=owner_id)
    second = create_random_category(db, owner_id=owner_id)
    for category in (first, second):
        response = client.put(
            f"{settings.API_V1_STR}/items/{item.id}",
            headers=normal_user_token_headers,
            json={"category_id": str(category.id)},
        )
        assert response.status_code == 200
        content = response.json()
        assert content["category_id"] == str(category.id)
        assert content["category"]["name"] == category.name


def test_update_item_other_users_category(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    owner_id = get_user_id(db, settings.EMAIL_TEST_USER)
    category = create_random_category(db, owner_id=owner_id)
    item = create_item_with_category(db, category)
    other_category = create_random_category(db)
    response = client.put(
        f"{settings.API_V1_STR}/items/{item.id}",
        headers=normal_user_token_headers,
        json={"title": "Changed", "category_id": str(other_category.id)},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Category not found"
    response = client.get(
        f"{settings.API_V1_STR}/items/{item.id}",
        headers=normal_user_token_headers,
    )
    content = response.json()
    assert content["title"] == item.title
    assert content["category_id"] == str(category.id)


def test_update_item_superuser_cannot_assign_own_category(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    superuser_id = get_user_id(db, settings.FIRST_SUPERUSER)
    superuser_category = create_random_category(db, owner_id=superuser_id)
    item = create_random_item(db)
    response = client.put(
        f"{settings.API_V1_STR}/items/{item.id}",
        headers=superuser_token_headers,
        json={"category_id": str(superuser_category.id)},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Category not found"


def test_read_items_include_category(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    owner_id = get_user_id(db, settings.EMAIL_TEST_USER)
    category = create_random_category(db, owner_id=owner_id)
    item = create_item_with_category(db, category)
    response = client.get(
        f"{settings.API_V1_STR}/items/",
        headers=normal_user_token_headers,
    )
    assert response.status_code == 200
    items = {i["id"]: i for i in response.json()["data"]}
    assert items[str(item.id)]["category"]["name"] == category.name


def test_read_items_superuser_sees_other_users_category(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    category = create_random_category(db)
    item = create_item_with_category(db, category)
    response = client.get(
        f"{settings.API_V1_STR}/items/",
        headers=superuser_token_headers,
        params={"limit": 1000},
    )
    assert response.status_code == 200
    items = {i["id"]: i for i in response.json()["data"]}
    assert items[str(item.id)]["category"]["name"] == category.name


def test_read_item_without_category(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    item = create_random_item(db)
    response = client.get(
        f"{settings.API_V1_STR}/items/{item.id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["category_id"] is None
    assert content["category"] is None


def test_items_require_authentication(client: TestClient, db: Session) -> None:
    item = create_random_item(db)
    url = f"{settings.API_V1_STR}/items"
    assert client.get(f"{url}/").status_code == 401
    assert client.get(f"{url}/{item.id}").status_code == 401
    assert client.post(f"{url}/", json={"title": "Foo"}).status_code == 401
    assert client.put(f"{url}/{item.id}", json={"title": "Foo"}).status_code == 401


def test_items_invalid_input(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    item = create_random_item(db)
    url = f"{settings.API_V1_STR}/items"
    response = client.post(
        f"{url}/",
        headers=superuser_token_headers,
        json={"title": "Foo", "category_id": "not-a-uuid"},
    )
    assert response.status_code == 422
    response = client.put(
        f"{url}/{item.id}",
        headers=superuser_token_headers,
        json={"category_id": "not-a-uuid"},
    )
    assert response.status_code == 422
    response = client.get(f"{url}/{item.id}", headers=superuser_token_headers)
    assert response.json()["title"] == item.title
    response = client.get(f"{url}/?skip=abc", headers=superuser_token_headers)
    assert response.status_code == 422
    response = client.get(f"{url}/not-a-uuid", headers=superuser_token_headers)
    assert response.status_code == 422


def test_update_item_clear_category(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    owner_id = get_user_id(db, settings.EMAIL_TEST_USER)
    category = create_random_category(db, owner_id=owner_id)
    first = create_item_with_category(db, category)
    second = create_item_with_category(db, category)
    response = client.put(
        f"{settings.API_V1_STR}/items/{first.id}",
        headers=normal_user_token_headers,
        json={"category_id": None},
    )
    assert response.status_code == 200
    content = response.json()
    assert content["category_id"] is None
    assert content["category"] is None
    response = client.get(
        f"{settings.API_V1_STR}/items/{second.id}",
        headers=normal_user_token_headers,
    )
    assert response.json()["category_id"] == str(category.id)
    response = client.get(
        f"{settings.API_V1_STR}/categories/",
        headers=normal_user_token_headers,
    )
    assert str(category.id) in [c["id"] for c in response.json()["data"]]


def test_update_item_without_category_field_keeps_category(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    owner_id = get_user_id(db, settings.EMAIL_TEST_USER)
    category = create_random_category(db, owner_id=owner_id)
    item = create_item_with_category(db, category)
    response = client.put(
        f"{settings.API_V1_STR}/items/{item.id}",
        headers=normal_user_token_headers,
        json={"title": "new"},
    )
    assert response.status_code == 200
    content = response.json()
    assert content["title"] == "new"
    assert content["category_id"] == str(category.id)


def test_update_item_superuser_clears_other_users_category(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    category = create_random_category(db)
    item = create_item_with_category(db, category)
    response = client.put(
        f"{settings.API_V1_STR}/items/{item.id}",
        headers=superuser_token_headers,
        json={"category_id": None},
    )
    assert response.status_code == 200
    assert response.json()["category_id"] is None
