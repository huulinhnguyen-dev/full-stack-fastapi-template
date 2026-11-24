import uuid

from sqlmodel import Session

from app import crud
from app.models import Category, CategoryCreate
from tests.utils.user import create_random_user
from tests.utils.utils import random_lower_string


def create_random_category(
    db: Session, *, owner_id: uuid.UUID | None = None, name: str | None = None
) -> Category:
    if owner_id is None:
        owner_id = create_random_user(db).id
    category_in = CategoryCreate(name=name or random_lower_string())
    return crud.create_category(session=db, category_in=category_in, owner_id=owner_id)
