import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.api.dependencies import CurrentUser, DatabaseSession
from app.schemas.products import (
    ProductCreate,
    ProductFilters,
    ProductPage,
    ProductPatch,
    ProductPut,
    ProductRead,
)
from app.services.products import ProductNotFoundError, product_service


router = APIRouter(prefix="/products", tags=["Produtos"])


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: ProductCreate,
    response: Response,
    session: DatabaseSession,
    _: CurrentUser,
) -> ProductRead:
    product = await product_service.create(session, payload)
    response.headers["Location"] = f"/api/v1/products/{product.id}"
    return ProductRead.model_validate(product)


@router.get("", response_model=ProductPage)
async def list_products(
    filters: Annotated[ProductFilters, Query()],
    session: DatabaseSession,
    _: CurrentUser,
) -> ProductPage:
    return await product_service.list(session, filters)


@router.get("/{product_id}", response_model=ProductRead)
async def get_product(
    product_id: uuid.UUID,
    session: DatabaseSession,
    _: CurrentUser,
) -> ProductRead:
    try:
        product = await product_service.get(session, product_id)
    except ProductNotFoundError as exc:
        raise_product_not_found(exc)
    return ProductRead.model_validate(product)


@router.put("/{product_id}", response_model=ProductRead)
async def replace_product(
    product_id: uuid.UUID,
    payload: ProductPut,
    session: DatabaseSession,
    _: CurrentUser,
) -> ProductRead:
    try:
        product = await product_service.update(session, product_id, payload)
    except ProductNotFoundError as exc:
        raise_product_not_found(exc)
    return ProductRead.model_validate(product)


@router.patch("/{product_id}", response_model=ProductRead)
async def update_product(
    product_id: uuid.UUID,
    payload: ProductPatch,
    session: DatabaseSession,
    _: CurrentUser,
) -> ProductRead:
    try:
        product = await product_service.update(session, product_id, payload)
    except ProductNotFoundError as exc:
        raise_product_not_found(exc)
    return ProductRead.model_validate(product)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: uuid.UUID,
    session: DatabaseSession,
    _: CurrentUser,
) -> Response:
    try:
        await product_service.delete(session, product_id)
    except ProductNotFoundError as exc:
        raise_product_not_found(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def raise_product_not_found(exc: ProductNotFoundError) -> None:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Produto não encontrado",
    ) from exc
