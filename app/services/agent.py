import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.agent import (
    AgentCompletedResponse,
    AgentGuidanceResponse,
    AgentInterpretation,
    AgentQueryArguments,
    AgentQueryRequest,
    AgentQueryResponse,
)
from app.schemas.products import ProductFilters
from app.services.products import product_service


EXAMPLES = [
    "Quais produtos estão com estoque abaixo de 10 unidades?",
    "Quais produtos estão sem estoque?",
    "Quais produtos custam entre 20 e 100 reais?",
]

WRITE_ACTION_PATTERN = re.compile(
    r"\b(apague|cadastre|crie|delete|edite|exclua|insira|remova|"
    r"atualize|altere)\b"
)

STOCK_BELOW_PATTERNS = (
    re.compile(
        r"quais produtos (?:estao )?(?:com )?estoque abaixo de "
        r"(?P<limit>\d+) unidades?"
    ),
    re.compile(
        r"quais produtos (?:(?:estao )?(?:com )?|tem )menos de "
        r"(?P<limit>\d+) unidades?(?: em estoque)?"
    ),
)
OUT_OF_STOCK_PATTERN = re.compile(
    r"quais produtos (?:estao )?(?:com )?sem estoque"
)
PRICE_RANGE_PATTERN = re.compile(
    r"quais produtos (?:custam|(?:estao )?com preco) entre "
    r"(?P<minimum>\d+(?:[.,]\d{1,2})?) e "
    r"(?P<maximum>\d+(?:[.,]\d{1,2})?)(?: reais?)?"
)
MISSING_THRESHOLD_PATTERN = re.compile(
    r"quais produtos (?:estao )?(?:com )?estoque baixo"
)


DecisionKind = Literal["plan", "needs_clarification", "rejected"]


@dataclass(frozen=True)
class InterpretationDecision:
    kind: DecisionKind
    arguments: dict[str, Any] | None = None
    reason_code: str | None = None
    message: str | None = None


def normalize_question(question: str) -> str:
    without_accents = "".join(
        character
        for character in unicodedata.normalize("NFKD", question)
        if not unicodedata.combining(character)
    )
    normalized = " ".join(without_accents.casefold().strip().split())
    return normalized.removesuffix("?").strip()


def parse_decimal(value: str) -> Decimal:
    return Decimal(value.replace(",", "."))


class QuestionInterpreter:
    def interpret(self, question: str) -> InterpretationDecision:
        normalized = normalize_question(question)

        if WRITE_ACTION_PATTERN.search(normalized):
            return InterpretationDecision(
                kind="rejected",
                reason_code="WRITE_ACTION_NOT_ALLOWED",
                message="O agente permite apenas consultas de produtos.",
            )

        for pattern in STOCK_BELOW_PATTERNS:
            if match := pattern.fullmatch(normalized):
                return InterpretationDecision(
                    kind="plan",
                    arguments={"estoque_abaixo_de": int(match["limit"])},
                )

        if OUT_OF_STOCK_PATTERN.fullmatch(normalized):
            return InterpretationDecision(
                kind="plan", arguments={"somente_sem_estoque": True}
            )

        if match := PRICE_RANGE_PATTERN.fullmatch(normalized):
            return InterpretationDecision(
                kind="plan",
                arguments={
                    "preco_min": parse_decimal(match["minimum"]),
                    "preco_max": parse_decimal(match["maximum"]),
                },
            )

        if MISSING_THRESHOLD_PATTERN.fullmatch(normalized):
            return InterpretationDecision(
                kind="needs_clarification",
                reason_code="MISSING_THRESHOLD",
                message="Informe o limite numérico do estoque.",
            )

        intent_markers = sum(
            marker in normalized
            for marker in (
                "estoque abaixo",
                "menos de",
                "sem estoque",
                "preco entre",
                "custam entre",
            )
        )
        if intent_markers > 1:
            return InterpretationDecision(
                kind="needs_clarification",
                reason_code="AMBIGUOUS_QUERY",
                message="Faça uma consulta por vez.",
            )

        return InterpretationDecision(
            kind="needs_clarification",
            reason_code="UNSUPPORTED_QUERY",
            message="A pergunta não corresponde a uma consulta suportada.",
        )


class ProductToolExecutor:
    async def execute(
        self,
        session: AsyncSession,
        raw_arguments: dict[str, Any],
        *,
        page: int,
        page_size: int,
    ) -> tuple[AgentQueryArguments, Any]:
        arguments = AgentQueryArguments(
            **raw_arguments,
            page=page,
            page_size=page_size,
        )
        filters = ProductFilters(**arguments.model_dump(exclude_none=True))
        result = await product_service.list(session, filters)
        return arguments, result


class AgentService:
    def __init__(
        self,
        interpreter: QuestionInterpreter,
        executor: ProductToolExecutor,
    ) -> None:
        self.interpreter = interpreter
        self.executor = executor

    async def query(
        self, session: AsyncSession, payload: AgentQueryRequest
    ) -> AgentQueryResponse:
        decision = self.interpreter.interpret(payload.question)
        if decision.kind != "plan":
            return AgentGuidanceResponse(
                status=decision.kind,
                reason_code=decision.reason_code,  # type: ignore[arg-type]
                message=decision.message or "Reformule a pergunta.",
                examples=EXAMPLES,
            )

        try:
            arguments, result = await self.executor.execute(
                session,
                decision.arguments or {},
                page=payload.page,
                page_size=payload.page_size,
            )
        except ValidationError:
            return AgentGuidanceResponse(
                status="needs_clarification",
                reason_code="UNSUPPORTED_QUERY",
                message="Os valores informados não formam uma consulta válida.",
                examples=EXAMPLES,
            )

        return AgentCompletedResponse(
            interpretation=AgentInterpretation(
                tool="consultar_produtos", arguments=arguments
            ),
            result=result,
        )


question_interpreter = QuestionInterpreter()
product_tool_executor = ProductToolExecutor()
agent_service = AgentService(question_interpreter, product_tool_executor)
