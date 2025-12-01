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
    summary="Stream agent execution with detailed process logs"
)
@limiter.limit(get_rate_limit_string())
async def stream_zaylon_agent(
    request: Request,
    body: AgentInvokeRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Stream agent execution for real-time updates with complete transparency.

    Returns Server-Sent Events (SSE) with:
    - Real-time system logs
    - Agent routing decisions
    - Tool calls with arguments and results
    - Agent processing updates
    - Final response matching /invoke format

    **Perfect for building interactive UIs with:**
    - Live process visualization
    - System logs panel
    - Analytics dashboard
    - Transparent AI reasoning display

    **Response Format:**
    - Stream chunks: {"type": "log|thinking|tool_call|tool_result|agent_processing", ...}
    - Final chunk: {"type": "final_response", ...all fields from /invoke...}
    """
    start_time = time.time()
    thread_id = body.thread_id or str(uuid.uuid4())

    logger.info(f"[STREAM] Agent streaming request from {body.customer_id} on {body.channel}")

    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate enhanced SSE events with full transparency."""
        collected_data = {
            "chain_of_thought": [],
            "tool_calls": [],
            "user_profile": {},
            "current_agent": "unknown",
            "final_response": None,
            "success": False
        }

        try:
            # Emit initial log
            yield f"data: {AgentStreamChunk(type='log', content=f'Message received from {body.customer_id}').model_dump_json()}\n\n"

            async for event in stream_agent(
                customer_id=body.customer_id,
                message=body.message,
                channel=body.channel
            ):
                # Handle error events
                if "error" in event:
                    error_msg = event["error"]
                    execution_time_ms = int((time.time() - start_time) * 1000)

                    # Emit error log
                    yield f"data: {AgentStreamChunk(type='log', content=f'ERROR: {error_msg}').model_dump_json()}\n\n"

                    # Emit final error response
                    yield f"data: {AgentStreamChunk(type='final_response', success=False, response='I apologize, but I encountered an error.', agent_used='unknown', chain_of_thought=[], tool_calls=[], user_profile={}, execution_time_ms=execution_time_ms, thread_id=thread_id, error=error_msg, done=True).model_dump_json()}\n\n"
                    return

                # Process LangGraph state updates
                for node_name, node_output in event.items():
                    node_time = int((time.time() - start_time) * 1000)

                    if node_name == "__end__":
                        # End of execution - emit final response
                        execution_time_ms = int((time.time() - start_time) * 1000)

                        # Convert chain of thought
                        chain_of_thought = [
                            AgentThought(node="internal", reasoning=cot)
                            if isinstance(cot, str)
                            else AgentThought(**cot)
                            for cot in collected_data["chain_of_thought"]
                        ]

                        # Convert tool calls
                        tool_calls = [
                            AgentToolCall(**tc) if isinstance(tc, dict) else tc
                            for tc in collected_data["tool_calls"]
                        ]

                        # Emit final response matching /invoke format
                        final_chunk = AgentStreamChunk(
                            type="final_response",
                            success=True,
                            response=collected_data["final_response"] or "Response generated",
                            agent_used=collected_data["current_agent"],
                            chain_of_thought=chain_of_thought,
                            tool_calls=tool_calls,
                            user_profile=collected_data["user_profile"],
                            execution_time_ms=execution_time_ms,
                            thread_id=thread_id,
                            done=True
                        )
                        yield f"data: {final_chunk.model_dump_json()}\n\n"

                    elif node_name == "load_memory":
                        # Memory loading
                        yield f"data: {AgentStreamChunk(type='log', content='Loaded customer memory from Memory Bank', node=node_name, execution_time_ms=node_time).model_dump_json()}\n\n"

                        if "user_profile" in node_output:
                            collected_data["user_profile"] = node_output["user_profile"]
                            fact_count = len(node_output["user_profile"])
                            yield f"data: {AgentStreamChunk(type='log', content=f'Found {fact_count} customer facts', node=node_name).model_dump_json()}\n\n"

                    elif node_name == "supervisor":
                        # Routing decision
                        yield f"data: {AgentStreamChunk(type='log', content='Supervisor analyzing message...', node=node_name, execution_time_ms=node_time).model_dump_json()}\n\n"

                        if "next" in node_output:
                            next_agent = node_output["next"]
                            yield f"data: {AgentStreamChunk(type='thinking', content=f'Routing decision: {next_agent.upper()}', node=node_name, execution_time_ms=node_time).model_dump_json()}\n\n"
                            yield f"data: {AgentStreamChunk(type='log', content=f'Routed to {next_agent} agent', node=node_name).model_dump_json()}\n\n"

                    elif node_name in ["sales_agent", "support_agent"]:
                        # Agent processing
                        collected_data["current_agent"] = node_name.replace("_agent", "")

                        # Check for chain of thought updates
                        if "chain_of_thought" in node_output:
                            thoughts = node_output["chain_of_thought"]
                            if thoughts and len(thoughts) > len(collected_data["chain_of_thought"]):
                                new_thoughts = thoughts[len(collected_data["chain_of_thought"]):]
                                for thought in new_thoughts:
                                    thought_text = thought if isinstance(thought, str) else thought.get("reasoning", "")
                                    yield f"data: {AgentStreamChunk(type='thinking', content=thought_text, node=node_name, execution_time_ms=node_time).model_dump_json()}\n\n"
                                collected_data["chain_of_thought"] = thoughts

                        # Check for tool calls
                        if "tool_calls" in node_output:
                            tool_calls = node_output["tool_calls"]
                            if tool_calls and len(tool_calls) > len(collected_data["tool_calls"]):
                                new_tools = tool_calls[len(collected_data["tool_calls"]):]
                                for tool_call in new_tools:
                                    tool_name = tool_call.get("tool_name", "unknown")
                                    tool_args = tool_call.get("arguments", {})
                                    tool_result = tool_call.get("result")

                                    # Emit tool call
                                    yield f"data: {AgentStreamChunk(type='tool_call', tool_name=tool_name, tool_args=tool_args, content=f'Calling {tool_name}', node=node_name, execution_time_ms=node_time).model_dump_json()}\n\n"
                                    yield f"data: {AgentStreamChunk(type='log', content=f'Tool: {tool_name}', node=node_name).model_dump_json()}\n\n"

                                    # Emit tool result if available
                                    if tool_result:
                                        result_preview = str(tool_result)[:200]
                                        yield f"data: {AgentStreamChunk(type='tool_result', tool_name=tool_name, tool_result=result_preview, content=f'{tool_name} completed', node=node_name, execution_time_ms=node_time).model_dump_json()}\n\n"
                                        yield f"data: {AgentStreamChunk(type='log', content=f'{tool_name} completed successfully', node=node_name).model_dump_json()}\n\n"

                                collected_data["tool_calls"] = tool_calls

                        # Check for final response
                        if "final_response" in node_output:
                            response = node_output["final_response"]
                            if response:
                                collected_data["final_response"] = response
                                # Fix: Extract variable to avoid nested f-string quote issues
                                agent_name = collected_data.get("current_agent", "unknown").capitalize()
                                yield f"data: {AgentStreamChunk(type='agent_processing', content=f'{agent_name} agent response generated', node=node_name, execution_time_ms=node_time).model_dump_json()}\n\n"
                                yield f"data: {AgentStreamChunk(type='log', content='Response generated', node=node_name).model_dump_json()}\n\n"

                    elif node_name == "save_memory":
                        # Memory saving
                        yield f"data: {AgentStreamChunk(type='log', content='Saving customer facts to Memory Bank', node=node_name, execution_time_ms=node_time).model_dump_json()}\n\n"

                        if "user_profile" in node_output:
                            collected_data["user_profile"] = node_output["user_profile"]
                            new_facts = len(node_output["user_profile"]) - len(collected_data.get("initial_profile", {}))
                            if new_facts > 0:
                                yield f"data: {AgentStreamChunk(type='log', content=f'Saved {new_facts} new facts', node=node_name).model_dump_json()}\n\n"

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"[STREAM] Error during streaming: {e}", exc_info=True)

            # Emit error log
            yield f"data: {AgentStreamChunk(type='log', content=f'FATAL ERROR: {str(e)}').model_dump_json()}\n\n"

            # Emit final error response
            yield f"data: {AgentStreamChunk(type='final_response', success=False, response='I apologize, but I encountered an unexpected error.', agent_used='unknown', chain_of_thought=[], tool_calls=[], user_profile={}, execution_time_ms=execution_time_ms, thread_id=thread_id, error=str(e), done=True).model_dump_json()}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "Access-Control-Allow-Origin": "*"  # Allow web interface
        }
    )
