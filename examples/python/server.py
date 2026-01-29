"""FastAPI server for the Research Assistant agent.

Demonstrates ADK + FastAPI integration with both standard and streaming endpoints.
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from research_agent import root_agent

app = FastAPI(title="Research Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

session_service = InMemorySessionService()
runner = Runner(
    agent=root_agent,
    app_name="research_assistant",
    session_service=session_service,
)


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    user_id: str = "default"


async def get_or_create_session(user_id: str, session_id: str | None):
    """Get existing session or create a new one."""
    if session_id:
        existing = await session_service.get_session(
            app_name="research_assistant",
            user_id=user_id,
            session_id=session_id,
        )
        if existing:
            return existing
    return await session_service.create_session(
        app_name="research_assistant",
        user_id=user_id,
    )


@app.post("/chat")
async def chat(request: ChatRequest):
    """Non-streaming chat endpoint."""
    session = await get_or_create_session(request.user_id, request.session_id)
    events = []

    new_message = types.Content(
        role="user", parts=[types.Part(text=request.message)]
    )

    async for event in runner.run_async(
        user_id=request.user_id,
        session_id=session.id,
        new_message=new_message,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    events.append({
                        "type": "content",
                        "text": part.text,
                        "author": event.author,
                        "is_final": event.is_final_response(),
                    })
                elif hasattr(part, "function_call") and part.function_call:
                    events.append({
                        "type": "tool_call",
                        "name": part.function_call.name,
                    })

    return {"session_id": session.id, "events": events}


@app.get("/chat/stream")
async def chat_stream(message: str, session_id: str = "", user_id: str = "default"):
    """SSE streaming endpoint."""
    session = await get_or_create_session(user_id, session_id or None)

    new_message = types.Content(
        role="user", parts=[types.Part(text=message)]
    )

    async def generate():
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session.id,
            new_message=new_message,
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
