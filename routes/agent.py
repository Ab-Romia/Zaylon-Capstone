"""
Agentic system endpoints (Zaylon v2 API).
Exposes the LangGraph multi-agent system for production use.
"""

import logging
import time
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from auth import verify_api_key, limiter, get_rate_limit_string
from models import (
    AgentInvokeRequest, AgentInvokeResponse,
    AgentThought, AgentToolCall, AgentStreamChunk
)
from app.agents.graph import invoke_agent, stream_agent
from services import analytics
from core.enums import EventType
from core.background import background_tasks

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/agent", tags=["Agent v2"])


@router.post(
    "/invoke",
    response_model=AgentInvokeResponse,
    summary="Invoke Zaylon agent"
)
@limiter.limit(get_rate_limit_string())
async def invoke_zaylon_agent(
    request: Request,
    body: AgentInvokeRequest,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Invoke the Zaylon multi-agent system.

    **Flow**:
    1. Load customer memory from Memory Bank
    2. Supervisor routes to Sales or Support agent
    3. Agent executes with access to specialized tools
    4. Save extracted facts back to Memory Bank

    **Returns**:
    - Final response from the agent
    - Full chain of thought (reasoning steps)
    - Tool calls made during execution
    - Customer profile from Memory Bank
    """
    start_time = time.time()
    logger.info(f"Agent invocation request from {body.customer_id} on {body.channel}")

    # Use thread_id from request or generate one
    thread_id = body.thread_id or str(uuid.uuid4())

    try:
        # Invoke the agent
        result = await invoke_agent(
            customer_id=body.customer_id,
            message=body.message,
            channel=body.channel
        )

        # Calculate execution time
        execution_time_ms = int((time.time() - start_time) * 1000)

        if not result.get("success", False):
            # Agent execution failed
            error_msg = result.get("error", "Unknown error")
            logger.error(f"Agent execution failed: {error_msg}")

            # Log failure to analytics
            background_tasks.add_task(
                analytics.log_event_background(
                    customer_id=body.customer_id,
                    event_type=EventType.AGENT_INVOKED,
                    event_data={
                        "success": False,
                        "error": error_msg,
                        "channel": body.channel,
                        "message_preview": body.message[:100]
                    },
                    response_time_ms=execution_time_ms
                )
            )

            return AgentInvokeResponse(
                success=False,
                response=result.get("final_response", "I apologize, but I encountered an error."),
                agent_used="unknown",
                chain_of_thought=[],
                tool_calls=[],
                user_profile={},
                execution_time_ms=execution_time_ms,
                thread_id=thread_id,
                error=error_msg
            )

        # Extract data from result
        final_response = result.get("final_response", "")
        chain_of_thought_raw = result.get("chain_of_thought", [])
        tool_calls_raw = result.get("tool_calls", [])
        user_profile = result.get("user_profile", {})
        current_agent = result.get("current_agent", "unknown")

        # Convert chain of thought to response model
        chain_of_thought = [
            AgentThought(node="internal", reasoning=cot)
            if isinstance(cot, str)
            else AgentThought(**cot)
            for cot in chain_of_thought_raw
        ]

        # Convert tool calls to response model
        tool_calls = [
            AgentToolCall(**tc) if isinstance(tc, dict) else tc
            for tc in tool_calls_raw
        ]

        # Log successful invocation to analytics with Chain of Thought
        background_tasks.add_task(
            analytics.log_event_background(
                customer_id=body.customer_id,
                event_type=EventType.AGENT_INVOKED,
                event_data={
                    "success": True,
                    "agent_used": current_agent,
                    "channel": body.channel,
                    "message_preview": body.message[:100],
                    "response_preview": final_response[:100],
                    "chain_of_thought": [
                        {"node": cot.node, "reasoning": cot.reasoning}
                        for cot in chain_of_thought
                    ],
                    "tool_calls_count": len(tool_calls),
                    "tools_used": [tc.tool_name for tc in tool_calls]
                },
                response_time_ms=execution_time_ms
            )
        )

        # Log agent routing
        background_tasks.add_task(
            analytics.log_event_background(
                customer_id=body.customer_id,
                event_type=EventType.AGENT_ROUTED,
                event_data={
                    "agent": current_agent,
                    "channel": body.channel
                }
            )
        )

        logger.info(
            f"Agent invocation successful - Agent: {current_agent}, "
            f"Time: {execution_time_ms}ms, Tools: {len(tool_calls)}"
        )

        return AgentInvokeResponse(
            success=True,
            response=final_response,
            agent_used=current_agent,
            chain_of_thought=chain_of_thought,
            tool_calls=tool_calls,
            user_profile=user_profile,
            execution_time_ms=execution_time_ms,
            thread_id=thread_id
        )

    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Unexpected error during agent invocation: {e}", exc_info=True)

        # Log error to analytics
        background_tasks.add_task(
            analytics.log_event_background(
                customer_id=body.customer_id,
                event_type=EventType.AGENT_INVOKED,
                event_data={
                    "success": False,
                    "error": str(e),
                    "channel": body.channel
                },
                response_time_ms=execution_time_ms
            )
        )

        return AgentInvokeResponse(
            success=False,
            response="I apologize, but I encountered an unexpected error. Please try again.",
            agent_used="unknown",
            chain_of_thought=[],
            tool_calls=[],
            user_profile={},
            execution_time_ms=execution_time_ms,
            thread_id=thread_id,
            error=str(e)
        )


@router.post(
    "/stream",
    summary="Stream agent execution"
)
@limiter.limit(get_rate_limit_string())
async def stream_zaylon_agent(
    request: Request,
    body: AgentInvokeRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Stream agent execution for real-time updates.

    Returns Server-Sent Events (SSE) with:
    - Agent thoughts as they occur
    - Tool calls in real-time
    - Final response

    This endpoint is useful for building interactive UIs that show
    the agent's reasoning process as it happens.
    """
    logger.info(f"Agent streaming request from {body.customer_id}")

    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events from agent stream."""
        try:
            async for event in stream_agent(
                customer_id=body.customer_id,
                message=body.message,
                channel=body.channel
            ):
                # Check for error
                if "error" in event:
                    chunk = AgentStreamChunk(
                        type="error",
                        content=event["error"],
                        done=True
                    )
                    yield f"data: {chunk.model_dump_json()}\n\n"
                    return

                # Process event based on what changed
                # LangGraph streams state updates
                for node_name, node_output in event.items():
                    if node_name == "__end__":
                        # Final event
                        chunk = AgentStreamChunk(
                            type="final",
                            content="Agent execution complete",
                            done=True
                        )
                        yield f"data: {chunk.model_dump_json()}\n\n"

                    elif "chain_of_thought" in node_output:
                        # New thought
                        thoughts = node_output.get("chain_of_thought", [])
                        if thoughts:
                            latest_thought = thoughts[-1]
                            chunk = AgentStreamChunk(
                                type="thought",
                                content=latest_thought,
                                node=node_name,
                                done=False
                            )
                            yield f"data: {chunk.model_dump_json()}\n\n"

                    elif "tool_calls" in node_output:
                        # Tool call
                        tool_calls = node_output.get("tool_calls", [])
                        if tool_calls:
                            latest_tool = tool_calls[-1]
                            tool_name = latest_tool.get("tool_name", "unknown")
                            chunk = AgentStreamChunk(
                                type="tool_call",
                                tool_name=tool_name,
                                content=f"Calling tool: {tool_name}",
                                done=False
                            )
                            yield f"data: {chunk.model_dump_json()}\n\n"

                    elif "final_response" in node_output:
                        # Final response ready
                        response = node_output.get("final_response")
                        if response:
                            chunk = AgentStreamChunk(
                                type="response",
                                content=response,
                                done=False
                            )
                            yield f"data: {chunk.model_dump_json()}\n\n"

        except Exception as e:
            logger.error(f"Error during streaming: {e}", exc_info=True)
            chunk = AgentStreamChunk(
                type="error",
                content=str(e),
                done=True
            )
            yield f"data: {chunk.model_dump_json()}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )
