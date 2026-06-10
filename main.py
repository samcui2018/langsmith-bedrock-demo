from langchain_openai import ChatOpenAI

from config.settings import Settings
from tools.sql_tools import SqlTools
from tools.bedrock_kb_tools import BedrockKbTools
from graphs.finance_graph import build_finance_graph


def main():
    model = ChatOpenAI(model="gpt-4o-mini")

    sql_tools = SqlTools(Settings.SQL_CONN_STR)

    kb_tools = BedrockKbTools(
        knowledge_base_id=Settings.BEDROCK_KB_ID,
        region_name=Settings.AWS_REGION,
        aws_access_key_id=Settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=Settings.AWS_SECRET_ACCESS_KEY
    )
    print("Tools initialized")
    print(kb_tools.knowledge_base_id)
    app = build_finance_graph(
        model=model,
        sql_tools=sql_tools,
        kb_tools=kb_tools,
    )

    result = app.invoke({
        "question": "Why did spending increase this month?",
        "business_id": "BE90356D-20A8-439A-AADE-FD96E970652C",
        "month": "2026-03",

        "route": "unknown",

        "security_result": "",
        "security_passed": False,

        "tool_result": "",

        "governance_result": "",
        "governance_passed": False,

        "final_answer": "",
    })

    print(result["final_answer"])


if __name__ == "__main__":
    main()