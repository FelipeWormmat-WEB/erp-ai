from decimal import Decimal

import pytest

from app.services.agent import QuestionInterpreter, normalize_question


@pytest.fixture
def interpreter() -> QuestionInterpreter:
    return QuestionInterpreter()


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        (
            "Quais produtos estão com estoque abaixo de 10 unidades?",
            {"estoque_abaixo_de": 10},
        ),
        (
            "quais PRODUTOS têm menos de 7 unidades em estoque?",
            {"estoque_abaixo_de": 7},
        ),
        ("Quais produtos estão sem estoque?", {"somente_sem_estoque": True}),
        (
            "Quais produtos custam entre 20,50 e 100.00 reais?",
            {"preco_min": Decimal("20.50"), "preco_max": Decimal("100.00")},
        ),
    ],
)
def test_interpreter_matches_only_documented_full_questions(
    interpreter: QuestionInterpreter,
    question: str,
    expected: dict | None,
) -> None:
    decision = interpreter.interpret(question)
    if expected is None:
        assert decision.kind == "needs_clarification"
        assert decision.reason_code == "UNSUPPORTED_QUERY"
    else:
        assert decision.kind == "plan"
        assert decision.arguments == expected


def test_normalization_handles_accents_case_and_spaces() -> None:
    assert normalize_question("  QUAIS   produtos ESTÃO sem estoque?  ") == (
        "quais produtos estao sem estoque"
    )


@pytest.mark.parametrize(
    ("question", "reason_code"),
    [
        ("Quais produtos estão com estoque baixo?", "MISSING_THRESHOLD"),
        ("Quais produtos têm até 10 unidades?", "UNSUPPORTED_QUERY"),
        (
            "Quais produtos estão sem estoque e com estoque abaixo de 10 unidades?",
            "AMBIGUOUS_QUERY",
        ),
        (
            "Quais produtos estão sem estoque e ordene pelo nome?",
            "UNSUPPORTED_QUERY",
        ),
        ("Quais produtos não estão sem estoque?", "UNSUPPORTED_QUERY"),
    ],
)
def test_interpreter_requests_clarification(
    interpreter: QuestionInterpreter, question: str, reason_code: str
) -> None:
    decision = interpreter.interpret(question)
    assert decision.kind == "needs_clarification"
    assert decision.reason_code == reason_code


@pytest.mark.parametrize(
    "question",
    [
        "Exclua todos os produtos sem estoque",
        "Atualize os produtos com estoque abaixo de 10 unidades",
        "Delete o produto mais caro",
    ],
)
def test_interpreter_rejects_write_actions(
    interpreter: QuestionInterpreter, question: str
) -> None:
    decision = interpreter.interpret(question)
    assert decision.kind == "rejected"
    assert decision.reason_code == "WRITE_ACTION_NOT_ALLOWED"
