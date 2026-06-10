from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI

from config.settings import Settings
from tools.sql_tools import SqlTools
from tools.bedrock_kb_tools import BedrockKbTools
from graphs.finance_graph import build_finance_graph

import json
from fastapi.responses import StreamingResponse
from fastapi import HTTPException
from services.auth_service import AuthService
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

app = FastAPI(title="FinIntel Agent API")
auth_service = AuthService()
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    question: str
    business_id: str
    month: str
    conversation_history: list[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    answer: str
    route: str
    security_passed: bool
    security_result: str
    governance_passed: bool
    governance_result: str
    tool_result: str

class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    name: str

auth_service = AuthService()
bearer_scheme = HTTPBearer()

model = ChatOpenAI(model="gpt-4o-mini")

sql_tools = SqlTools(Settings.SQL_CONN_STR)

kb_tools = BedrockKbTools(
    knowledge_base_id=Settings.BEDROCK_KB_ID,
    region_name=Settings.AWS_REGION,
    aws_access_key_id=Settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=Settings.AWS_SECRET_ACCESS_KEY
)

graph_app = build_finance_graph(
    model=model,
    sql_tools=sql_tools,
    kb_tools=kb_tools,
)

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    token = credentials.credentials

    payload = auth_service.decode_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token.",
        )

    user = auth_service.get_user_by_id(payload["sub"])

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found.",
        )

    return user

@app.get("/")
def root():
    return {"message": "FinIntel Agent API is running"}

@app.post("/auth/login", response_model=LoginResponse)
def login(request: LoginRequest):
    user = auth_service.authenticate_user(
        request.username,
        request.password,
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password.",
        )

    token = auth_service.create_access_token(user)

    return LoginResponse(
        access_token=token,
        name=user["name"],
    )

@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, user: dict = Depends(get_current_user)):
    validate_business_access(user, request.business_id)
    result = graph_app.invoke(build_initial_state(request))

    return ChatResponse(
        answer=result["final_answer"],
        route=result["route"],
        security_passed=result["security_passed"],
        security_result=result["security_result"],
        governance_passed=result["governance_passed"],
        governance_result=result["governance_result"],
        tool_result=result["tool_result"],
    )

@app.post("/chat/stream")
def chat_stream(request: ChatRequest, user: dict = Depends(get_current_user)):
    validate_business_access(user, request.business_id)
    def event_generator():
        yield json.dumps({
            "type": "status",
            "message": "Starting FinIntel graph..."
        }) + "\n"

        state = build_initial_state(request)

        try:
            for event in graph_app.stream(state):
                node_name = list(event.keys())[0]
                node_output = event[node_name]

                yield json.dumps({
                    "type": "status",
                    "message": f"Completed node: {node_name}"
                }) + "\n"

                if node_name == "router":
                    yield json.dumps({
                        "type": "route",
                        "route": node_output.get("route")
                    }) + "\n"

                if node_name == "security":
                    yield json.dumps({
                        "type": "security",
                        "security_passed": node_output.get("security_passed"),
                        "security_result": node_output.get("security_result")
                    }) + "\n"

                if node_name in [
                    "top_merchants",
                    "monthly_summary",
                    "knowledge_base",
                    "combined_analysis",
                    "unknown",
                    "blocked",
                ]:
                    yield json.dumps({
                        "type": "tool_result",
                        "tool_result": node_output.get("tool_result")
                    }) + "\n"

                if node_name == "governance":
                    yield json.dumps({
                        "type": "governance",
                        "governance_passed": node_output.get("governance_passed"),
                        "governance_result": node_output.get("governance_result")
                    }) + "\n"

                if node_name == "final_response":
                    yield json.dumps({
                        "type": "final",
                        "answer": node_output.get("final_answer")
                    }) + "\n"

        except Exception as ex:
            yield json.dumps({
                "type": "error",
                "message": str(ex)
            }) + "\n"

    return StreamingResponse(
        event_generator(),
        media_type="application/x-ndjson",
    )
@app.get("/me/businesses")
def get_my_businesses(user = Depends(get_current_user)):
    # user = auth_service.get_current_user()

    return {
        "user_id": user["user_id"],
        "name": user["name"],
        "businesses": user["businesses"],
    }

def build_initial_state(request: ChatRequest):
    return {
        "question": request.question,
        "business_id": request.business_id,
        "month": request.month,
        "conversation_history": [
            msg.model_dump() for msg in request.conversation_history
        ],

        "route": "unknown",

        "security_result": "",
        "security_passed": False,

        "tool_result": "",

        "governance_result": "",
        "governance_passed": False,

        "final_answer": "",
    }
def validate_business_access(user: dict, business_id: str):
    # user = auth_service.get_current_user()

    if not auth_service.user_can_access_business(
        user_id=user["user_id"],
        business_id=business_id,
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to access this business.",
        )
