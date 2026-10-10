from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.products import ProductPage, ProductPrice


class AgentQueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    model_config = ConfigDict(extra="forbid")


class AgentQueryArguments(BaseModel):
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    estoque_abaixo_de: int | None = Field(
        default=None, ge=0, le=2_147_483_647
    )
    somente_sem_estoque: bool | None = None
    preco_min: ProductPrice | None = None
    preco_max: ProductPrice | None = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_single_read_intent(self) -> "AgentQueryArguments":
        intents = [
            self.estoque_abaixo_de is not None,
            self.somente_sem_estoque is True,
            self.preco_min is not None or self.preco_max is not None,
        ]
        if sum(intents) != 1:
            raise ValueError("informe exatamente um filtro de consulta")
        if (self.preco_min is None) != (self.preco_max is None):
            raise ValueError("a faixa de preço exige valor mínimo e máximo")
        if (
            self.preco_min is not None
            and self.preco_max is not None
            and self.preco_min > self.preco_max
        ):
            raise ValueError("o preço mínimo não pode ser maior que o máximo")
        return self


class AgentInterpretation(BaseModel):
    tool: Literal["consultar_produtos"]
    arguments: AgentQueryArguments


class AgentCompletedResponse(BaseModel):
    status: Literal["completed"] = "completed"
    interpretation: AgentInterpretation
    result: ProductPage


class AgentGuidanceResponse(BaseModel):
    status: Literal["needs_clarification", "rejected"]
    reason_code: Literal[
        "UNSUPPORTED_QUERY",
        "AMBIGUOUS_QUERY",
        "MISSING_THRESHOLD",
        "WRITE_ACTION_NOT_ALLOWED",
    ]
    message: str
    examples: list[str]


AgentQueryResponse = AgentCompletedResponse | AgentGuidanceResponse

