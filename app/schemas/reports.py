from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_serializer


ReportThreshold = Annotated[StrictInt, Field(ge=1, le=2_147_483_647)]


class LowStockReportRequest(BaseModel):
    threshold: ReportThreshold = 10

    model_config = ConfigDict(extra="forbid")


class ReportAccepted(BaseModel):
    report_id: UUID
    status: Literal["pending"] = "pending"
    status_url: str


class LowStockItem(BaseModel):
    id: UUID
    nome: str
    preco: Decimal
    quantidade_em_estoque: int

    @field_serializer("preco")
    def serialize_price(self, value: Decimal) -> str:
        return format(value, ".2f")


class LowStockResult(BaseModel):
    threshold: int
    generated_at: datetime
    returned_count: int
    has_more: bool
    items: list[LowStockItem]


class StockReportRead(BaseModel):
    id: UUID
    threshold: int
    status: Literal["pending", "completed", "failed"]
    result: LowStockResult | None
    error_code: str | None
    created_at: datetime
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
