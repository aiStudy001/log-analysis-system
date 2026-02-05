"""
WebSocket controller for streaming Text-to-SQL queries
"""
import asyncio
import logging
import re
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.stream_service import stream_query_execution
from app.dependencies import get_schema_repository, get_query_repository
from app.services.cache_service import get_query_cache
from typing import List

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])

# Feature #5: Active WebSocket connections for broadcasting
active_connections: List[WebSocket] = []


def sanitize_error_message(error: str) -> str:
    """
    Remove sensitive information from error messages

    Args:
        error: Raw error message

    Returns:
        Sanitized error message safe for client display
    """
    # Remove file paths
    error = re.sub(r'File ".*?"', 'File "[REDACTED]"', error)
    # Remove connection strings
    error = re.sub(r'postgresql://.*?@', 'postgresql://[REDACTED]@', error)
    # Remove full stack traces (keep only first line)
    lines = error.split('\n')
    return lines[0] if lines else error


@router.websocket("/ws/query")
async def websocket_query(websocket: WebSocket):
    """
    WebSocket endpoint for streaming Text-to-SQL queries

    Message Types (Client → Server):
        - {"action": "query", "question": "...", "max_results": 100, "conversation_id": "..."}
        - {"action": "cancel"}

    Message Types (Server → Client):
        - {"type": "cache_hit", "message": "...", "data": {...}} (Feature #1)
        - {"type": "context_resolved", "node": "...", "data": {...}} (Feature #2)
        - {"type": "node_complete", "node": "...", "status": "...", "data": {...}}
        - {"type": "validation_failed", "node": "...", "message": "..."}
        - {"type": "execution_failed", "node": "...", "message": "..."}
        - {"type": "complete", "sql": "...", "results": [...], ...}
        - {"type": "error", "message": "..."}
        - {"type": "cancelled", "message": "..."}
    """
    await websocket.accept()

    # Feature #5: Register connection for alerts
    active_connections.append(websocket)

    task = None

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            action = data.get("action")
            print(f"🔍 WebSocket received: action={action}, data={data}")  # DEBUG

            if action == "query":
                question = data.get("question")
                max_results = data.get("max_results", 100)
                conversation_id = data.get("conversation_id", "default")  # Feature #2
                time_range_structured = data.get("time_range_structured")  # NEW: Flexible time range
                print(f"📝 Starting query: question='{question}', max_results={max_results}, time_range_structured={time_range_structured}")  # DEBUG

                # Cancel previous task if running
                if task and not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

                # Start new streaming query with conversation_id
                print(f"🚀 Creating stream_query task...")  # DEBUG
                task = asyncio.create_task(
                    stream_query(websocket, question, max_results, conversation_id, time_range_structured)
                )
                print(f"✅ Task created: {task}")  # DEBUG

            elif action == "cancel":
                if task and not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        await websocket.send_json({
                            "type": "cancelled",
                            "message": "Query cancelled by user"
                        })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected gracefully for client {websocket.client}")
        if task and not task.done():
            task.cancel()
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)

        # Try to send error to client
        try:
            if websocket.client_state.value == 1:  # CONNECTED
                await websocket.send_json({
                    "type": "error",
                    "message": sanitize_error_message(str(e)),
                    "retry_possible": True
                })
        except Exception as send_error:
            logger.error(f"Failed to send error to client: {send_error}")
        finally:
            # Try to close WebSocket gracefully
            try:
                await websocket.close(code=1011, reason="Server error")
            except Exception as close_error:
                logger.error(f"Failed to close WebSocket: {close_error}")
    finally:
        # Feature #5: Unregister connection
        if websocket in active_connections:
            active_connections.remove(websocket)


async def stream_query(
    websocket: WebSocket,
    question: str,
    max_results: int,
    conversation_id: str = "default",
    time_range_structured: dict = None
):
    """
    Stream agent execution to WebSocket (meal-planner pattern)

    Args:
        websocket: WebSocket connection
        question: User's natural language question
        max_results: Maximum number of results
        conversation_id: Conversation session ID (Feature #2)
        time_range_structured: Optional structured time range from frontend
    """
    print(f"🎬 stream_query STARTED: question='{question}'")  # DEBUG
    try:
        # Get repositories
        print(f"📦 Getting repositories...")  # DEBUG
        schema_repo = get_schema_repository()
        query_repo = get_query_repository()
        print(f"✅ Repositories obtained")  # DEBUG

        # Stream events with conversation context
        print(f"🔄 Starting stream_query_execution...")  # DEBUG
        async for event in stream_query_execution(
            question, max_results, schema_repo, query_repo, conversation_id, time_range_structured
        ):
            print(f"📤 Sending event: {event.get('type', 'unknown')}")  # DEBUG
            await websocket.send_json(event)
        print(f"✅ stream_query COMPLETED")  # DEBUG

    except asyncio.CancelledError:
        logger.info("Query cancelled by user")
        # Check WebSocket state before sending
        try:
            if websocket.client_state.value == 1:  # CONNECTED
                await websocket.send_json({
                    "type": "cancelled",
                    "message": "Query cancelled"
                })
        except Exception as e:
            logger.warning(f"Failed to send cancellation message: {e}")
    except Exception as e:
        logger.error(f"Error in stream_query: {e}", exc_info=True)
        # Check WebSocket state before sending
        try:
            if websocket.client_state.value == 1:  # CONNECTED
                await websocket.send_json({
                    "type": "error",
                    "message": sanitize_error_message(str(e)),
                    "retry_possible": True
                })
        except Exception as send_error:
            logger.error(f"Failed to send error message: {send_error}")


@router.post("/invalidate_cache")
async def invalidate_cache():
    """
    Invalidate all cached query results

    Called when new logs are inserted to ensure fresh data.

    Returns:
        Status message
    """
    cache = get_query_cache()
    await cache.invalidate_all()
    return {
        "status": "cache_invalidated",
        "message": "모든 캐시가 무효화되었습니다"
    }


# Feature #5: Broadcast alerts to all connected clients
async def broadcast_alert(alert: dict):
    """
    Send alert to all connected WebSocket clients

    Args:
        alert: Alert data to broadcast
    """
    dead_connections = []
    success_count = 0
    failed_count = 0

    for ws in active_connections:
        try:
            await ws.send_json({
                "type": "alert",
                **alert
            })
            success_count += 1
        except Exception as e:
            logger.warning(f"Failed to send alert to client: {e}")
            dead_connections.append(ws)
            failed_count += 1

    # Remove dead connections
    for ws in dead_connections:
        if ws in active_connections:
            active_connections.remove(ws)

    # Log broadcast summary
    logger.info(
        f"Alert broadcast complete: {success_count} success, {failed_count} failed, "
        f"{len(active_connections)} active connections"
    )
