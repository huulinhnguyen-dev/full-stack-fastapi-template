import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app import crud
from app.models import Category, CategoryCreate, Item, ItemCreate
from tests.utils.category import create_random_category
from tests.utils.user import create_random_user
from tests.utils.utils import random_lower_string


def test_create_category(db: Session) -> None:
    user = create_random_user(db)
    name = random_lower_string()
    category_in = CategoryCreate(name=f"  {name}  ")
    category = crud.create_category(
        session=db, category_in=category_in, owner_id=user.id
    )
    assert category.name == name
    assert category.owner_id == user.id
    assert category.id is not None
    assert category.created_at is not None


def test_category_create_strips_name() -> None:
    assert CategoryCreate(name="  Work  ").name == "Work"


def test_category_create_rejects_blank_name() -> None:
    with pytest.raises(ValidationError):
        CategoryCreate(name="   ")


def test_category_create_rejects_too_long_name() -> None:
    with pytest.raises(ValidationError):
        CategoryCreate(name="x" * 256)


def test_get_category_by_name_is_case_insensitive(db: Session) -> None:
    category = create_random_category(db)
    found = crud.get_category_by_name(
        session=db, owner_id=category.owner_id, name=f" {category.name.upper()} "
    )
    assert found is not None
    assert found.id == category.id


def test_get_category_by_name_other_owner(db: Session) -> None:
    category = create_random_category(db)
    other_user = create_random_user(db)
    found = crud.get_category_by_name(
        session=db, owner_id=other_user.id, name=category.name
    )
    assert found is None


def test_same_name_for_different_owners(db: Session) -> None:
    name = random_lower_string()
    first = create_random_category(db, name=name)
    second = create_random_category(db, name=name)
    assert first.owner_id != second.owner_id
    assert first.name == second.name


def test_duplicate_name_violates_unique_index(db: Session) -> None:
    category = create_random_category(db, name=f"Work {random_lower_string()}")
    db.add(Category(name=category.name.lower(), owner_id=category.owner_id))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_delete_category_leaves_items_uncategorized(db: Session) -> None:
    category = create_random_category(db)
    item = crud.create_item(
        session=db,
        item_in=ItemCreate(title=random_lower_string(), category_id=category.id),
        owner_id=category.owner_id,
    )
    db.delete(category)
    db.commit()
    db.refresh(item)
    assert db.get(Item, item.id) is not None
    assert item.category_id is None


def test_delete_user_deletes_categories(db: Session) -> None:
    user = create_random_user(db)
    category = create_random_category(db, owner_id=user.id)
    category_id = category.id
    db.delete(user)
    db.commit()
    db.expire_all()
    assert db.get(Category, category_id) is None
