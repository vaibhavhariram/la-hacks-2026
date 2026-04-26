"""Fetch.ai uAgent with Chat Protocol for field unit reports.

Receives natural language messages via Agentverse Chat Protocol and
forwards raw text to the backend /field-report endpoint (Option A contract).

Run locally:
    python agents/field_unit_agent.py

Register on Agentverse:
    - Deploy via Agentverse UI or CLI with mailbox=True
    - Agent address printed on startup — register this address in Agentverse

References:
    https://uagents.fetch.ai/docs/examples/asi-1
    https://innovationlab.fetch.ai/events/hackathons/hack-brown-2026/hackpack
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    TextContent,
    chat_protocol_spec,
)

import httpx

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.gemma_parser import blocked_hazard_payload, parse_report_safe

load_dotenv()

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
AGENT_SEED = os.environ.get("AGENT_SEED", "aegis-field-unit-default-seed")
AGENT_PORT = int(os.environ.get("AGENT_PORT", "8002"))


async def _handle_report_text(ctx: Context, text: str) -> str:
    """Forward raw text, then post blocked hazard if parser finds one."""
    report_payload = {"text": text, "unit_id": "aegis-field-unit"}
    parsed = parse_report_safe(text)
    hazard_payload = blocked_hazard_payload(parsed)

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            report_response = await client.post(f"{BACKEND_URL}/field-report", json=report_payload)
            report_response.raise_for_status()

            if hazard_payload:
                hazard_response = await client.post(f"{BACKEND_URL}/hazard", json=hazard_payload)
                hazard_response.raise_for_status()

        ctx.logger.info(f"Posted field report: {len(text)} chars")
        if hazard_payload:
            ctx.logger.info(f"Posted blocked hazard: {hazard_payload}")
            return "Report received. Blocked route hazard posted to dispatch."
        return "Report received and forwarded to dispatch."
    except httpx.HTTPError as e:
        ctx.logger.error(f"Backend POST failed: {e}")
        return f"error: backend unreachable — {e}"


# ── Chat Protocol handler ─────────────────────────────────────────────────────

chat_proto = Protocol(spec=chat_protocol_spec)


@chat_proto.on_message(ChatMessage)
async def handle_chat_message(ctx: Context, sender: str, msg: ChatMessage):
    text = msg.text().strip()
    ctx.logger.info(f"Chat message from {sender}: {text!r}")

    # Acknowledge receipt immediately.
    await ctx.send(sender, ChatAcknowledgement(acknowledged_msg_id=msg.msg_id))

    response_text = await _handle_report_text(ctx, text)

    await ctx.send(sender, ChatMessage(content=[
        TextContent(text=response_text),
        EndSessionContent(),
    ]))


@chat_proto.on_message(ChatAcknowledgement)
async def handle_chat_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    ctx.logger.info(f"Chat acknowledgement from {sender}: {msg.acknowledged_msg_id}")


def build_agent() -> Agent:
    field_agent = Agent(
        name="aegis-field-unit",
        seed=AGENT_SEED,
        port=AGENT_PORT,
        mailbox=True,
        publish_agent_details=True,
    )

    @field_agent.on_event("startup")
    async def on_startup(ctx: Context):
        ctx.logger.info(f"Field unit agent started. Address: {field_agent.address}")
        ctx.logger.info(f"Backend URL: {BACKEND_URL}")
        ctx.logger.info(f"Agent port: {AGENT_PORT}")

    field_agent.include(chat_proto, publish_manifest=True)
    return field_agent


print("[agent] Chat Protocol registered")


if __name__ == "__main__":
    agent = build_agent()
    agent.run()
