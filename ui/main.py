from nicegui import ui
import httpx
import json

API_URL = "http://127.0.0.1:8000/chat"
BUSINESSES_URL = "http://127.0.0.1:8000/me/businesses"
LOGIN_URL = "http://127.0.0.1:8000/auth/login"
CHAT_STREAM_URL = "http://127.0.0.1:8000/chat/stream"

access_token = None

business_options = {}

messages = []

async def login():
    global access_token

    payload = {
        "email": username_input.value,
        "password": password_input.value,
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(LOGIN_URL, json=payload)
            response.raise_for_status()
            data = response.json()

        access_token = data["access_token"]
        login_status.text = f"Logged in as {data['name']}"
        print (username_input.value, password_input.value)
        await load_businesses()

    except Exception as ex:
        login_status.text = f"Login failed: {str(ex)}"


def render_messages():
    chat_area.clear()

    for msg in messages:
        with chat_area:
            with ui.card().classes("w-full"):
                ui.label(msg["role"]).classes("text-bold")
                ui.markdown(msg["content"])


async def ask_agent():
    if not access_token:
        messages.append({
            "role": "assistant",
            "content": "Please log in first.",
        })
        render_messages()
        return
    
    question = question_input.value

    if not question:
        return

    question_input.value = ""

    history_for_api = messages[-10:]

    messages.append({
        "role": "user",
        "content": question,
    })

    messages.append({
        "role": "assistant",
        "content": "Thinking...",
    })

    render_messages()

    payload = {
        "question": question,
        "business_id": business_select.value,
        "month": month_input.value,
        "conversation_history": history_for_api,
    }

    try:
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST",
                # API_URL.replace("/chat", "/chat/stream"),
                CHAT_STREAM_URL,
                json=payload,
                headers=headers,
            ) as response:

                response.raise_for_status()

                partial_text = ""

                async for line in response.aiter_lines():
                    if not line:
                        continue

                    event = json.loads(line)

                    if event["type"] == "status":
                        partial_text += f"\n\n⏳ {event['message']}"

                    elif event["type"] == "route":
                        partial_text += f"\n\n🧭 Route: `{event['route']}`"

                    elif event["type"] == "security":
                        partial_text += f"\n\n🔐 Security: {event['security_result']}"

                    elif event["type"] == "governance":
                        partial_text += f"\n\n📋 Governance: {event['governance_result']}"

                    elif event["type"] == "tool_result":
                        partial_text += "\n\n🛠️ Tool completed."

                    elif event["type"] == "final":
                        partial_text += f"\n\n### Answer\n\n{event['answer']}"

                    elif event["type"] == "error":
                        partial_text += f"\n\n❌ Error: {event['message']}"

                    messages[-1] = {
                        "role": "assistant",
                        "content": partial_text,
                    }

    except Exception as ex:
        messages[-1] = {
            "role": "assistant",
            "content": f"Error: {str(ex)}",
        }
    render_messages()

async def load_businesses():
    if not access_token:
        return

    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(BUSINESSES_URL, headers=headers)
        response.raise_for_status()
        data = response.json()

    options = {
        b["business_id"]: b["business_name"]
        for b in data["businesses"]
    }

    business_select.options = options

    if options:
        business_select.value = next(iter(options.keys()))

    business_select.update()


# UI code using NiceGUI
ui.column().classes("w-full items-center gap-1")
ui.label("FinIntel Chat").classes("text-h4")
ui.label("LangGraph + SQL + Bedrock KB + LangSmith").classes("text-subtitle2")

username_input = ui.input("Email", value="demo@example.com").classes("w-full")
password_input = ui.input("Password", value="demo123", password=True).classes("w-full")
login_status = ui.label("")

ui.button("Login", on_click=login)

business_select = ui.select(
    label="Business",
    options={},
    ).classes("w-full")

month_input = ui.input(
    label="Month",
    value="2026-03",
).classes("w-full")

chat_area = ui.column().classes("w-full gap-2")

question_input = ui.input(
    placeholder="Ask about merchants, spending, policies, or trends..."
).classes("w-full")


with ui.row().classes("w-full"):
    question_input
    ui.button("Send", on_click=ask_agent)

question_input.on("keydown.enter", ask_agent)

ui.timer(0.1, load_businesses, once=True)

ui.run(title="FinIntel Chat", reload=False)