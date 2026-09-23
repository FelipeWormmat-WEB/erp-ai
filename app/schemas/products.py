import math
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Annotated, Any
from uuid import UUID

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StrictInt,
    field_serializer,
    field_validator,
    model_validator,
)


MAX_PRICE = Decimal("9999999999.99")


def validate_product_name(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("nome deve ser texto")
    normalized = value.strip()
    if not 2 <= len(normalized) <= 120:
        raise ValueError("nome deve ter entre 2 e 120 caracteres")
    if not any(character.isalpha() for character in normalized):
        raise ValueError("nome deve conter ao menos uma letra")
    return normalized


def validate_price(value: Any) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise ValueError("preço inválido")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("preço deve ser finito")

    try:
        decimal_value = Decimal(str(value).strip())
    except (InvalidOperation, ValueError, AttributeError) as exc:
        raise ValueError("preço inválido") from exc

    if not decimal_value.is_finite():
        raise ValueError("preço deve ser finito")
    if decimal_value < 0 or decimal_value > MAX_PRICE:
        raise ValueError(f"preço deve estar entre 0 e {MAX_PRICE}")
    if decimal_value.as_tuple().exponent < -2:
        raise ValueError("preço deve ter no máximo duas casas decimais")
    return decimal_value


ProductName = Annotated[str, BeforeValidator(validate_product_name)]
ProductPrice = Annotated[Decimal, BeforeValidator(validate_price)]
StockQuantity = Annotated[StrictInt, Field(ge=0, le=2_147_483_647)]


class ProductCreate(BaseModel):
    nome: ProductName
    preco: ProductPrice
    quantidade_em_estoque: StockQuantity

    model_config = ConfigDict(extra="forbid")


class ProductPut(ProductCreate):
    pass


class ProductPatch(BaseModel):
    nome: ProductName | None = None
    preco: ProductPrice | None = None
    quantidade_em_estoque: StockQuantity | None = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_changed_fields(self) -> "ProductPatch":
        if not self.model_fields_set:
            raise ValueError("informe ao menos um campo para atualização")
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("campos informados não podem ser nulos")
        return self


class ProductRead(BaseModel):
    id: UUID
    nome: str
    preco: Decimal
    quantidade_em_estoque: int
    data_criacao: datetime
    data_atualizacao: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("preco")
    def serialize_price(self, value: Decimal) -> str:
        return format(value, ".2f")


class ProductPage(BaseModel):
    items: list[ProductRead]
    page: int
    page_size: int
    total: int
    total_pages: int


class ProductFilters(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    nome: str | None = Field(default=None, min_length=1, max_length=120)
    preco_min: ProductPrice | None = None
    preco_max: ProductPrice | None = None
    estoque_abaixo_de: int | None = Field(default=None, ge=0, le=2_147_483_647)
    somente_sem_estoque: bool = False

    model_config = ConfigDict(extra="forbid")

    @field_validator("nome")
    @classmethod
    def normalize_filter_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("filtro de nome não pode ser vazio")
        return normalized

    @model_validator(mode="after")
    def validate_price_range(self) -> "ProductFilters":
        if (
            self.preco_min is not None
            and self.preco_max is not None
            and self.preco_min > self.preco_max
        ):
            raise ValueError("preco_min não pode ser maior que preco_max")
        return self
