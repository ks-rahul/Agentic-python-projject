"""Chat routes for AI conversations."""
import json
import uuid
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import StreamingResponse

from app.schemas.session import ChatRequest
from app.services.chat_service import ChatService
from app.services.agent_service import AgentService
from app.db.postgresql import get_db
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/tenants/{tenant_id}/agents/{agent_id}/stream")
async def stream_chat(
    tenant_id: str,
    agent_id: str,
    request: ChatRequest,
    db = Depends(get_db)
):
    """Stream chat responses via Server-Sent Events."""
    agent_service = AgentService(db)
    agent_config = await agent_service.get_full_configuration(agent_id)
    
    if not agent_config:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    chat_service = ChatService()
    
    async def stream_response():
        message_id = str(uuid.uuid4())
        full_response = ""
        
        try:
            async for chunk in chat_service.stream_chat(
                agent_config=agent_config,
                session_id=request.session_id,
                user_query=request.user_query
            ):
                yield f"data: {json.dumps(chunk)}\n\n"
                if chunk.get("type") == "chunk":
                    full_response += chunk.get("content", "")
            
            logger.info(f"Chat response completed for session {request.session_id}")
            
        except Exception as e:
            logger.error(f"Error during chat stream: {e}")
            error_chunk = {"type": "error", "error": str(e), "message_id": message_id}
            yield f"data: {json.dumps(error_chunk)}\n\n"
    
    return StreamingResponse(
        stream_response(),
        media_type="text/event-stream"
    )


@router.websocket("/tenants/{tenant_id}/agents/{agent_id}/ws/{session_id}")
async def websocket_chat(
    websocket: WebSocket,
    tenant_id: str,
    agent_id: str,
    session_id: str,
    db = Depends(get_db)
):
    """WebSocket endpoint for real-time chat."""
    await websocket.accept()
    
    agent_service = AgentService(db)
    agent_config = await agent_service.get_full_configuration(agent_id)
    
    if not agent_config:
        await websocket.send_json({
            "type": "error",
            "data": {"message": "Agent configuration not found"}
        })
        await websocket.close(code=1011)
        return
    
    chat_service = ChatService()
    
    try:
        while True:
            user_query = await websocket.receive_text()
            logger.info(f"WS query for agent '{agent_id}', session '{session_id}': {user_query}")
            
            await websocket.send_json({
                "type": "status",
                "data": {"message": "Processing..."}
            })
            
            full_response = ""
            async for chunk in chat_service.stream_chat(
                agent_config=agent_config,
                session_id=session_id,
                user_query=user_query
            ):
                if chunk.get("type") == "chunk":
                    await websocket.send_json({
                        "type": "token",
                        "data": {"delta": chunk.get("content", "")}
                    })
                    full_response += chunk.get("content", "")
                elif chunk.get("type") == "sources":
                    await websocket.send_json({
                        "type": "sources",
                        "data": {"sources": chunk.get("sources", [])}
                    })
            
            await websocket.send_json({
                "type": "end",
                "data": {"full_response": full_response}
            })
            
            # Update chat history
            await chat_service.update_chat_history(
                session_id=session_id,
                user_message=user_query,
                assistant_message=full_response
            )
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session '{session_id}'")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "data": {"message": str(e)}
            })
        except:
            pass
        await websocket.close(code=1011)
