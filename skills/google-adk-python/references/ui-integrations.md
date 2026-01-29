# Python Backend & UI Integrations

## Table of Contents
- [FastAPI Backend](#fastapi-backend)
- [Flask Backend](#flask-backend)
- [Streamlit](#streamlit)
- [Slack Bot](#slack-bot)
- [Google PubSub Events](#google-pubsub-events)
- [Serving React/Next.js Frontends](#serving-reactnextjs-frontends)

## FastAPI Backend

Production-ready async API server with streaming support.

```python
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

app = FastAPI()

# Enable CORS for frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend origin
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = Agent(
    name="assistant",
    model="gemini-2.0-flash",
    instruction="You are a helpful assistant.",
    tools=[get_weather, search_web]
)

session_service = InMemorySessionService()  # Use Firestore in production
runner = Runner(
    agent=agent,
    app_name="fastapi_app",
    session_service=session_service
)


class ChatRequest(BaseModel):
    message: str
    session_id: str
    user_id: str = "default"


@app.post("/chat")
async def chat(request: ChatRequest):
    """Non-streaming chat endpoint."""
    new_message = types.Content(
        role="user", parts=[types.Part(text=request.message)]
    )
    events = []
    async for event in runner.run_async(
        user_id=request.user_id,
        session_id=request.session_id,
        new_message=new_message,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    events.append({"type": "content", "text": part.text})

    return {"events": events}


@app.get("/chat/stream")
async def chat_stream(message: str, session_id: str, user_id: str = "default"):
    """SSE streaming endpoint for real-time responses."""
    new_message = types.Content(
        role="user", parts=[types.Part(text=message)]
    )

    async def generate():
        async for event in runner.run_async(
            user_id=user_id, session_id=session_id, new_message=new_message
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        yield f"data: {part.text}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/health")
async def health():
    return {"status": "healthy"}
```

**Run:** `uvicorn main:app --host 0.0.0.0 --port 8000`

## Flask Backend

Simpler synchronous API server.

```python
from flask import Flask, request, jsonify
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
import os

app = Flask(__name__)

agent = Agent(
    name="assistant",
    model="gemini-2.0-flash",
    instruction="You are a helpful assistant."
)

session_service = InMemorySessionService()
runner = Runner(agent=agent, app_name="flask_app", session_service=session_service)


@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    new_message = types.Content(
        role="user", parts=[types.Part(text=data["message"])]
    )
    results = []
    for event in runner.run(
        user_id=data["user_id"],
        session_id=data["session_id"],
        new_message=new_message,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    results.append({"type": "content", "text": part.text})
    return jsonify({"events": results})


@app.route("/health")
def health():
    return "OK"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
```

**Run:** `gunicorn --bind :8080 --workers 1 --threads 8 main:app`

## Streamlit

Handle Streamlit's rerun behavior with cached resources.

```python
import streamlit as st
import uuid
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types


@st.cache_resource
def get_agent_resources():
    """Initialize ADK resources once, persisting across Streamlit reruns."""
    agent = Agent(
        name="assistant",
        model="gemini-2.0-flash",
        instruction="You are a helpful assistant.",
        tools=[get_weather, search_web]
    )
    session_service = InMemorySessionService()
    runner = Runner(
        agent=agent,
        app_name="streamlit_app",
        session_service=session_service
    )
    return runner, session_service


runner, session_service = get_agent_resources()

# Maintain conversation state across Streamlit reruns
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []

st.title("ADK Chat Assistant")

# Display conversation history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Handle new user input
if prompt := st.chat_input("Message"):
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""

        new_message = types.Content(
            role="user", parts=[types.Part(text=prompt)]
        )
        for event in runner.run(
            user_id="streamlit_user",
            session_id=st.session_state.session_id,
            new_message=new_message,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        full_response += part.text
                        response_placeholder.write(full_response)

        st.session_state.messages.append({
            "role": "assistant",
            "content": full_response
        })
```

**Run:** `streamlit run app.py`

**Key pattern:** Use `@st.cache_resource` to initialize Runner and SessionService exactly once. Streamlit reruns the entire script on each interaction; without caching, agent state resets.

## Slack Bot

```python
import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

app = App(token=os.environ["SLACK_BOT_TOKEN"])

agent = Agent(
    name="slack_assistant",
    model="gemini-2.0-flash",
    instruction="You are a helpful Slack assistant. Keep responses concise."
)

session_service = InMemorySessionService()
runner = Runner(agent=agent, app_name="slack_bot", session_service=session_service)


@app.event("app_mention")
def handle_mention(event, say):
    user_id = event["user"]
    channel = event["channel"]
    text = event["text"]

    # Use channel as session ID for conversational context
    session_id = f"slack_{channel}"

    new_message = types.Content(role="user", parts=[types.Part(text=text)])
    response_text = ""
    for ev in runner.run(user_id=user_id, session_id=session_id, new_message=new_message):
        if ev.content and ev.content.parts:
            for part in ev.content.parts:
                if hasattr(part, "text") and part.text:
                    response_text += part.text

    say(response_text)


@app.event("message")
def handle_dm(event, say):
    if event.get("channel_type") == "im":
        handle_mention(event, say)


if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()
```

**Dependencies:** `pip install slack-bolt google-adk`

## Google PubSub Events

Event-driven agent execution via Google Cloud PubSub.

```python
import json
from google.cloud import pubsub_v1
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

session_service = InMemorySessionService()
runner = Runner(agent=my_agent, app_name="pubsub_agent", session_service=session_service)
subscriber = pubsub_v1.SubscriberClient()
publisher = pubsub_v1.PublisherClient()

PROJECT_ID = "my-project"
subscription_path = subscriber.subscription_path(PROJECT_ID, "agent-requests-sub")
response_topic = publisher.topic_path(PROJECT_ID, "agent-responses")


def callback(message):
    data = json.loads(message.data.decode())
    user_id = data["user_id"]
    session_id = data["session_id"]
    query = data["query"]

    new_message = types.Content(role="user", parts=[types.Part(text=query)])
    response_text = ""
    for event in runner.run(user_id=user_id, session_id=session_id, new_message=new_message):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    response_text += part.text

    # Publish response back
    publisher.publish(
        response_topic,
        json.dumps({
            "user_id": user_id,
            "session_id": session_id,
            "response": response_text
        }).encode()
    )

    message.ack()


streaming_pull = subscriber.subscribe(subscription_path, callback=callback)
streaming_pull.result()  # Block and listen
```

**Dependencies:** `pip install google-cloud-pubsub google-adk`

## Serving React/Next.js Frontends

ADK Python agents serve as the backend API for JavaScript frontends. The ADK backend exposes REST/SSE endpoints that any frontend framework can consume.

### Architecture

```
React/Next.js Frontend  <-->  FastAPI/Flask Python Backend  <-->  ADK Agent
      (JS/TSX)                      (Python)                    (Python)
```

### Python backend (FastAPI with SSE)

Use the FastAPI backend from above. The `/chat/stream` endpoint returns Server-Sent Events that React/Next.js clients can consume with `EventSource`.

### AG-UI / CopilotKit integration

For richer frontend experiences, ADK supports the AG-UI protocol. The Python backend exposes an AG-UI compatible endpoint, and the React frontend uses CopilotKit components:

```bash
# Scaffold a project with ADK + CopilotKit
npx copilotkit@latest create -f adk
```

This generates a Python backend agent paired with a React frontend. Key capabilities:
- **Generative UI** - Agent renders components in chat
- **Shared State** - Frontend and backend share synchronized state
- **Human-in-the-Loop** - Users approve actions before execution

### adk api_server

For development, ADK provides a built-in API server:

```bash
adk api_server my_agent --port 8000
```

This exposes your Python agent as an HTTP API without writing Flask/FastAPI code. Not suitable for production.
