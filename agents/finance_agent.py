from langchain.agents import create_agent
# from langchain_openai import ChatOpenAI

# from tools.sql_tools import get_top_merchants



# def build_finance_agent(model, tools):
#     #  model = ChatOpenAI(
#     #     model=model_name
#     # )
#      return create_agent(
#         model=model,
#         tools=tools,
#         system_prompt="""
#         You are a financial analytics assistant.

#         Use the available SQL tools when the user asks about spending,
#         merchants, categories, summaries, or financial trends.

#         Be concise and business-friendly.
#         """
#     )