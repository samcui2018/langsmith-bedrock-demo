from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage

from models.state import FinanceState


def build_finance_graph(model, sql_tools, kb_tools):
    graph = StateGraph(FinanceState)

    top_merchants_tool = sql_tools.get_top_merchants_tool()
    monthly_summary_tool = sql_tools.get_monthly_summary_tool()
    search_kb_tool = kb_tools.search_knowledge_base_tool()

    def format_history(history):
        if not history:
            return "No prior conversation."

        return "\n".join(
            f"{msg['role']}: {msg['content']}"
            for msg in history[-6:]
        )

    def router_node(state: FinanceState):
        question = state["question"].lower()
        history_text = format_history(state.get("conversation_history", [])).lower()
        combined_text = f"{history_text}\n{question}"

        if "top merchant" in combined_text or "merchant" in combined_text:
            route = "top_merchants"

        elif (
            "policy" in combined_text
            or "document" in combined_text
            or "knowledge base" in combined_text
            or "explain" in combined_text
            or "definition" in combined_text
        ):
            route = "knowledge_base"

        elif (
            "why" in combined_text
            or "reason" in combined_text
            or "increase" in combined_text
            or "decrease" in combined_text
            or "changed" in combined_text
            or "trend" in combined_text
        ):
            route = "combined_analysis"

        elif "summary" in combined_text or "summarize" in combined_text or "spending" in combined_text:
            route = "monthly_summary"

        else:
            route = "unknown"

        return {
            "route": route
        }

    def security_node(state: FinanceState):
        question = state["question"].lower()

        blocked_patterns = [
            "ignore previous instructions",
            "reveal system prompt",
            "show api key",
            "show access key",
            "drop table",
            "delete from",
            "update users",
        ]

        for pattern in blocked_patterns:
            if pattern in question:
                return {
                    "security_passed": False,
                    "security_result": f"Blocked due to unsafe request: {pattern}",
                }

        return {
            "security_passed": True,
            "security_result": "Security check passed.",
        }

    def route_after_security(state: FinanceState):
        if not state["security_passed"]:
            return "blocked"

        return state["route"]

    def top_merchants_node(state: FinanceState):
        result = top_merchants_tool.invoke({
            "business_id": state["business_id"],
            "month": state["month"],
            "limit": 5,
        })

        return {
            "tool_result": result
        }

    def monthly_summary_node(state: FinanceState):
        result = monthly_summary_tool.invoke({
            "business_id": state["business_id"],
            "month": state["month"],
        })

        return {
            "tool_result": result
        }

    def knowledge_base_node(state: FinanceState):
        result = search_kb_tool.invoke({
            "query": state["question"]
        })

        return {
            "tool_result": result
        }

    def combined_analysis_node(state: FinanceState):
        sql_result = monthly_summary_tool.invoke({
            "business_id": state["business_id"],
            "month": state["month"],
        })

        kb_result = search_kb_tool.invoke({
            "query": state["question"]
        })

        combined_result = f"""
        SQL result:
        {sql_result}

        Knowledge base result:
        {kb_result}
        """

        return {
            "tool_result": combined_result
        }

    def unknown_node(state: FinanceState):
        return {
            "tool_result": "I do not know which financial tool to use for this question."
        }

    def blocked_node(state: FinanceState):
        return {
            "tool_result": state["security_result"]
        }

    def governance_node(state: FinanceState):
        if not state["business_id"]:
            return {
                "governance_passed": False,
                "governance_result": "Missing business_id.",
            }

        if not state["month"]:
            return {
                "governance_passed": False,
                "governance_result": "Missing month.",
            }

        if "No" in state["tool_result"] and "found" in state["tool_result"]:
            return {
                "governance_passed": True,
                "governance_result": "Tool returned no data.",
            }

        return {
            "governance_passed": True,
            "governance_result": "Governance check passed.",
        }

    def final_response_node(state: FinanceState):
        history_text = format_history(state.get("conversation_history", []))
        prompt = f"""
        You are a financial analytics assistant.

        Conversation history:
        {history_text}

        Current user question:
        {state["question"]}

        Business ID:
        {state["business_id"]}

        Month:
        {state["month"]}

        Route:
        {state["route"]}

        Security result:
        {state["security_result"]}

        Governance result:
        {state["governance_result"]}

        Tool result:
        {state["tool_result"]}

        Write a concise business-friendly answer.
        Use the conversation history only for context.
        If the current question is a follow-up, connect it to the previous turn.
        If the question was blocked by security, politely explain that the request cannot be completed.
        If the tool returned no data, say that clearly.
        """

        response = model.invoke([
            HumanMessage(content=prompt)
        ])

        return {
            "final_answer": response.content
        }

    graph.add_node("router", router_node)
    graph.add_node("security", security_node)
    graph.add_node("top_merchants", top_merchants_node)
    graph.add_node("monthly_summary", monthly_summary_node)
    graph.add_node("knowledge_base", knowledge_base_node)
    graph.add_node("combined_analysis", combined_analysis_node)
    graph.add_node("unknown", unknown_node)
    graph.add_node("blocked", blocked_node)
    graph.add_node("governance", governance_node)
    graph.add_node("final_response", final_response_node)

    graph.set_entry_point("router")

    graph.add_edge("router", "security")

    graph.add_conditional_edges(
        "security",
        route_after_security,
        {
            "top_merchants": "top_merchants",
            "monthly_summary": "monthly_summary",
            "knowledge_base": "knowledge_base",
            "combined_analysis": "combined_analysis",
            "unknown": "unknown",
            "blocked": "blocked",
        },
    )

    graph.add_edge("top_merchants", "governance")
    graph.add_edge("monthly_summary", "governance")
    graph.add_edge("knowledge_base", "governance")
    graph.add_edge("combined_analysis", "governance")
    graph.add_edge("unknown", "governance")
    graph.add_edge("blocked", "governance")

    graph.add_edge("governance", "final_response")
    graph.add_edge("final_response", END)

    return graph.compile()