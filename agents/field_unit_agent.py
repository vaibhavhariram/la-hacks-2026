"""Fetch.ai uAgent with Chat Protocol for field unit reports.

Receives natural language messages via Agentverse Chat Protocol and
forwards raw text to the backend /field-report endpoint (Option A contract).

Run locally:
    python agents/field_unit_agent.py

Register on Agentverse:
    - Deploy via Agentverse UI or CLI with mailbox=True
    - Agent address printed on startup — register this address in Agentverse

IMPORTANT: verify exact uagents + uagents-ai-engine Chat Protocol imports
against the Agentverse docs before the hackathon. The API surface changed
between minor versions. Pin to whatever version the prize docs specify.

References:
    https://docs.agentverse.ai/guides/agents/chat-protocol
    https://github.com/fetchai/uAgents
"""
import os

from dotenv import load_dotenv
from uagents import Agent, Context

# Chat Protocol imports — verify these against current Agentverse docs
# uagents-ai-engine >= 0.4 expected path:
try:
    from uagents_ai_engine import (
        ChatProtocol,
        ChatMessage,
        ChatAcknowledgement,
    )
    _CHAT_PROTO_AVAILABLE = True
except ImportError:
    _CHAT_PROTO_AVAILABLE = False
    print("[agent] WARNING: uagents-ai-engine not installed. Install to enable Chat Protocol.")

import httpx

load_dotenv()

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8001")
AGENT_SEED = os.environ.get("AGENT_SEED", "aegis-field-unit-default-seed")

agent = Agent(
    name="aegis-field-unit",
    seed=AGENT_SEED,
    mailbox=True,  # enables Agentverse mailbox mode — local agent, registered remotely
)

@agent.on_event("startup")
async def on_startup(ctx: Context):
    ctx.logger.info(f"Field unit agent started. Address: {agent.address}")
    ctx.logger.info(f"Backend URL: {BACKEND_URL}")


async def _handle_report_text(ctx: Context, text: str) -> str:
    """Forward raw text to /field-report. Backend parses internally (Option A contract)."""
    payload = {"text": text, "unit_id": "aegis-field-unit"}
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.post(f"{BACKEND_URL}/field-report", json=payload)
            r.raise_for_status()
        ctx.logger.info(f"Posted field report: {len(text)} chars")
        return "Report received and forwarded to dispatch."
    except httpx.HTTPError as e:
        ctx.logger.error(f"Backend POST failed: {e}")
        return f"error: backend unreachable — {e}"


# ── Chat Protocol handler ─────────────────────────────────────────────────────
# Wrapped in guard so agent still starts if uagents-ai-engine isn't installed

if _CHAT_PROTO_AVAILABLE:
    chat_proto = ChatProtocol()

    @chat_proto.on_message(ChatMessage)
    async def handle_chat_message(ctx: Context, sender: str, msg: ChatMessage):
        ctx.logger.info(f"Chat message from {sender}: {msg.text!r}")

        # Acknowledge receipt immediately
        await ctx.send(sender, ChatAcknowledgement(acknowledged=True))

        response_text = await _handle_report_text(ctx, msg.text)

        # Send structured response back to sender
        await ctx.send(sender, ChatMessage(text=response_text))

    agent.include(chat_proto, publish_manifest=True)
    print("[agent] Chat Protocol registered")
else:
    print("[agent] Chat Protocol NOT registered — install uagents-ai-engine")


if __name__ == "__main__":
    agent.run()
