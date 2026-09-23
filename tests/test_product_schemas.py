from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.products import ProductCreate, ProductFilters, ProductPatch


def test_product_create_normalizes_valid_values() -> None:
    product = ProductCreate(
        nome="  Teclado USB  ",
        preco="79.90",
        quantidade_em_estoque=9,
    )

    assert product.nome == "Teclado USB"
    assert product.preco == Decimal("79.90")
    assert product.quantidade_em_estoque == 9


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("nome", "12345"),
        ("nome", " "),
        ("preco", "-0.01"),
        ("preco", "10.999"),
        ("quantidade_em_estoque", -1),
        ("quantidade_em_estoque", True),
    ],
)
def test_product_create_rejects_invalid_values(field: str, value: object) -> None:
    payload = {
        "nome": "Produto válido",
        "preco": "10.00",
        "quantidade_em_estoque": 1,
    }
    payload[field] = value

    with pytest.raises(ValidationError):
        ProductCreate.model_validate(payload)


def test_product_patch_rejects_empty_body_and_null() -> None:
    with pytest.raises(ValidationError):
        ProductPatch.model_validate({})

    with pytest.raises(ValidationError):
        ProductPatch.model_validate({"nome": None})


def test_product_filters_reject_inverted_price_range() -> None:
    with pytest.raises(ValidationError):
        ProductFilters(preco_min="100.00", preco_max="20.00")
