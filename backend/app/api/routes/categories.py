import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import func, select

from app import crud
from app.api.deps import CurrentUser, SessionDep
from app.models import (
    CategoriesPublic,
    Category,
    CategoryCreate,
    CategoryPublic,
    Message,
)

router = APIRouter(prefix="/categories", tags=["categories"])

DUPLICATE_NAME_DETAIL = "A category with this name already exists"


@router.get("/", response_model=CategoriesPublic)
def read_categories(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve categories.
    """
    # Categories are personal: no superuser branch
    count_statement = (
        select(func.count())
        .select_from(Category)
        .where(Category.owner_id == current_user.id)
    )
    count = session.exec(count_statement).one()
    statement = (
        select(Category)
        .where(Category.owner_id == current_user.id)
        .order_by(func.lower(Category.name))
        .offset(skip)
        .limit(limit)
    )
    categories = session.exec(statement).all()

    categories_public = [
        CategoryPublic.model_validate(category) for category in categories
    ]
    return CategoriesPublic(data=categories_public, count=count)


@router.post("/", response_model=CategoryPublic)
def create_category(
    *, session: SessionDep, current_user: CurrentUser, category_in: CategoryCreate
) -> Any:
    """
    Create new category.
    """
    existing = crud.get_category_by_name(
        session=session, owner_id=current_user.id, name=category_in.name
    )
    if existing:
        raise HTTPException(status_code=409, detail=DUPLICATE_NAME_DETAIL)
    try:
        category = crud.create_category(
            session=session, category_in=category_in, owner_id=current_user.id
        )
    except IntegrityError:
        # A concurrent request created the same name after the check above
        session.rollback()
        raise HTTPException(status_code=409, detail=DUPLICATE_NAME_DETAIL)
    return category


@router.delete("/{id}", response_model=Message)
def delete_category(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Message:
    """
    Delete a category. Items using it become uncategorized.
    """
    category = session.get(Category, id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    # Categories are personal: no superuser exception
    if category.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    # The database sets item.category_id to NULL (ON DELETE SET NULL)
    session.delete(category)
    session.commit()
    return Message(message="Category deleted successfully")
