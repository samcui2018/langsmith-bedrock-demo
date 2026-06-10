from typing import TypedDict, Literal


class FinanceState(TypedDict):
    question: str
    business_id: str
    month: str

    route: Literal[
        "top_merchants",
        "monthly_summary",
        "knowledge_base",
        "combined_analysis",
        "unknown",
    ]

    security_result: str
    security_passed: bool

    tool_result: str

    governance_result: str
    governance_passed: bool

    final_answer: str