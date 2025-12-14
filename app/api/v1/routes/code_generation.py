"""Code generation and invocation routes for AI assistants."""
import importlib.util
import inspect
from pathlib import Path
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgresql import get_db
from app.services.chat_service import ChatService
from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import get_current_user

logger = get_logger(__name__)

router = APIRouter()


class Configurations(BaseModel):
    id: int
    endpoints: Dict[str, Any]
    fields_mapping: Optional[Dict[str, Any]] = {}
    assistant_desc: str


class CodeRequest(BaseModel):
    id: str
    tenant_id: str
    name: str
    category: str
    description: Optional[str] = None
    configurations: Configurations


class UpdateCodeRequest(BaseModel):
    code: str
    path: str


class GetCodeRequest(BaseModel):
    path: str


class InvokeRequest(BaseModel):
    path: str
    action: str
    payload: Optional[Dict[str, Any]] = {}
    auth_config: Optional[Dict[str, Any]] = {}
    endpoint_headers: Optional[List[Dict[str, str]]] = []


@router.post("/generate")
async def generate_code(
    request: CodeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Generate code for an assistant/connector."""
    try:
        endpoints = request.configurations.endpoints or {}
        actions = endpoints.get("actions", []) if isinstance(endpoints, dict) else []
        
        action_names = [
            action.get("name") for action in actions if action.get("name")
        ]
        
        logger.info(f"Generating code for connector: {request.name}, actions: {action_names}")
        
        chat_service = ChatService()
        
        result = await chat_service.generate_code(
            query=request.configurations.assistant_desc,
            payload={},
            endpoints=request.configurations.endpoints,
            configurations=request.configurations.model_dump(),
            base_url=request.configurations.endpoints.get("baseUrl"),
            action_name=action_names,
            fields_mapping=request.configurations.fields_mapping,
            tenant_id=request.tenant_id,
            connector_name=request.name,
            connector_id=request.id
        )
        
        logger.info(f"Code generation successful for connector: {request.name}")
        return result
        
    except Exception as e:
        logger.error(f"Error during code generation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Code generation failed: {str(e)}"
        )


@router.post("/update")
async def update_code(
    request: UpdateCodeRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update or create agent code at the specified path."""
    try:
        path = Path(request.path)
        
        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write the code
        with open(path, "w") as f:
            f.write(request.code)
        
        logger.info(f"Code updated at path: {path}")
        return {"status": "success", "file": str(path)}
        
    except Exception as e:
        logger.error(f"Failed to update code: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update code: {str(e)}"
        )


@router.post("/get")
async def get_code(
    request: GetCodeRequest,
    current_user: dict = Depends(get_current_user)
):
    """Retrieve assistant code from the specified path."""
    try:
        path = Path(request.path)
        
        if not path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent code not found"
            )
        
        with open(path, "r") as f:
            code = f.read()
        
        return {"status": "success", "code": code}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve code: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve code: {str(e)}"
        )


@router.post("/invoke")
async def invoke_agent(
    request: InvokeRequest,
    current_user: dict = Depends(get_current_user)
):
    """Invoke agent code with the specified action and payload."""
    file_path = Path(request.path)
    
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    action = request.action.strip("/")
    
    try:
        # Load the module dynamically
        module = _load_agent_module(file_path)
        
        if not hasattr(module, action):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No action '{action}' found in agent"
            )
        
        func = getattr(module, action)
        
        # Prepare the payload
        prepared_payload = _prepare_invocation_payload(request.model_dump())
        
        logger.info(f"Invoking action '{action}' with prepared payload")
        
        # Check if function accepts parameters
        sig = inspect.signature(func)
        if len(sig.parameters) > 0:
            result = func(prepared_payload)
        else:
            result = func()
        
        return {
            "status": "success",
            "action": action,
            "result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Execution error in {file_path} for action {action}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Execution error: {str(e)}"
        )


def _load_agent_module(file_path: Path):
    """Dynamically load a Python module from file path."""
    spec = importlib.util.spec_from_file_location("agent_module", file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _prepare_invocation_payload(req_data: dict) -> dict:
    """Prepare the invocation payload with auth and parameters."""
    payload = {}
    
    user_payload = req_data.get("payload", {})
    
    # Process URL params
    url_params_list = user_payload.get("urlParams", [])
    if url_params_list and isinstance(url_params_list, list):
        url_params_dict = {
            item.get("key"): item.get("value") 
            for item in url_params_list if item.get("key")
        }
        payload.update(url_params_dict)
    
    # Process query params
    query_params_list = user_payload.get("queryParams", [])
    if query_params_list and isinstance(query_params_list, list):
        payload['queryParams'] = query_params_list
    
    # Process body content
    body_list = user_payload.get("body", [])
    if body_list and isinstance(body_list, list):
        body_dict = {
            item.get("key"): item.get("value") 
            for item in body_list if item.get("key")
        }
        payload['bodyContent'] = body_dict
    
    # Process auth config
    auth_config = req_data.get("auth_config", {})
    auth_type = auth_config.get("auth_type")
    
    if auth_type:
        payload['auth_type'] = auth_type
        
        if auth_type == "api_key":
            payload['key_name'] = auth_config.get("key_name")
            payload['api_key'] = auth_config.get("key_value")
        elif auth_type == "bearer_token":
            payload['access_token'] = auth_config.get("token")
        elif auth_type == "basic_auth":
            payload['username'] = auth_config.get("username")
            payload['password'] = auth_config.get("password")
        elif auth_type == "oauth2":
            payload['token'] = auth_config.get("token")
            payload['token_type'] = auth_config.get("token_type")
        elif auth_type == "custom_header":
            config_data = auth_config.get("config", auth_config)
            auth_headers_list = config_data.get("auth_headers", [])
            
            translated_headers = [
                {"key_name": header.get("key"), "key_value": header.get("value")}
                for header in auth_headers_list
            ]
            payload['auth_headers'] = translated_headers
    
    # Process endpoint headers
    endpoint_headers = req_data.get("endpoint_headers", [])
    if endpoint_headers:
        payload['custom_headers'] = payload.get('custom_headers', [])
        payload['custom_headers'].extend(endpoint_headers)
    
    return payload
