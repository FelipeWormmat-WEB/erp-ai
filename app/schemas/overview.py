from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class OverviewScenario(StrEnum):
    SUCCESS = "success"
    PARTIAL_TIMEOUT = "partial_timeout"
    RETRY_SUCCESS = "retry_success"
    ALL_FAILED = "all_failed"


class SourceResult(BaseModel):
    status: Literal["ok", "timeout", "error"]
    attempts: int = Field(ge=1, le=2)
    data: dict[str, int] | None = None
    error_code: Literal["SOURCE_TIMEOUT", "SOURCE_UNAVAILABLE"] | None = None


class OverviewSources(BaseModel):
    estoque: SourceResult
    financeiro: SourceResult
    clientes: SourceResult


class OverviewResponse(BaseModel):
    mode: Literal["mock"] = "mock"
    status: Literal["complete", "partial", "unavailable"]
    sources: OverviewSources
