import logging
from contextlib import asynccontextmanager
from typing import List, Optional
from fastapi import FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.config import settings
from app.database import init_db, check_db_health, save_message, get_messages_by_session, session_exists
from app.models import ChatRequest, ChatResponse, ChatMetadata, HealthResponse, SessionHistoryResponse
from app.llm_service import execute_llm_completion
from app.cache_service import cache_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("lyftr.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure SQLite database and tables exist
    init_db()
    yield


app = FastAPI(
    title="Lyftr AI API",
    description="High-reliability conversational AI platform with failover and caching",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=settings.ALLOWED_ORIGINS != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    error_msg = "; ".join([f"{err.get('loc', ['field'])[-1]}: {err.get('msg')}" for err in errors])
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": error_msg}
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled server error: {exc}", exc_info=False)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred."}
    )


@app.get("/health", response_model=HealthResponse)
def get_health():
    """
    Health check endpoint: Returns 200 once app running, DB reachable, key pool loaded.
    { "status": "ok", "keys_configured": 2, "cache_enabled": true }
    """
    db_healthy = check_db_health()
    if not db_healthy:
        raise HTTPException(status_code=503, detail="database unavailable")

    keys_count = len(settings.parsed_keys)
    return HealthResponse(
        status="ok",
        keys_configured=keys_count,
        cache_enabled=cache_service.enabled
    )


@app.post("/chat", response_model=ChatResponse)
def post_chat(
    req: ChatRequest,
    x_simulate_failure: Optional[str] = Header(None, alias="X-Simulate-Failure")
):
    """
    Chat completion endpoint with multi-turn context, caching, and failover.
    Only successful requests are saved to SQLite.
    """
    session_id = req.session_id
    user_message = req.message
    system_prompt = req.system_prompt

    # 1. Retrieve past conversation history from database
    history = get_messages_by_session(session_id)

    # 2. Build full message list for LiteLLM (system prompt + history + new message)
    llm_messages: List[dict] = []
    if system_prompt:
        llm_messages.append({"role": "system", "content": system_prompt})
    
    for past_msg in history:
        llm_messages.append({"role": past_msg["role"], "content": past_msg["content"]})
        
    llm_messages.append({"role": "user", "content": user_message})

    # 3. Execute LLM completion with caching & failover
    # Any failure here (e.g. 503 if all providers fail) raises HTTPException and will NOT reach step 4
    reply, meta_dict = execute_llm_completion(
        model=settings.LLM_MODEL,
        messages=llm_messages,
        simulate_header=x_simulate_failure
    )

    metadata = ChatMetadata(**meta_dict)

    # 4. Save user message and assistant reply to database ONLY on success
    # Metadata stored for assistant message: resolution_source, input_tokens, output_tokens
    stored_meta = {
        "resolution_source": metadata.resolution_source,
        "input_tokens": metadata.input_tokens,
        "output_tokens": metadata.output_tokens
    }
    try:
        save_message(session_id=session_id, role="user", content=user_message, metadata=None)
        save_message(session_id=session_id, role="assistant", content=reply, metadata=stored_meta)
    except Exception as e:
        logger.error(f"Failed to persist chat messages to database: {e}")

    return ChatResponse(
        session_id=session_id,
        reply=reply,
        metadata=metadata
    )


@app.get("/sessions/{session_id}/messages", response_model=SessionHistoryResponse)
def get_session_history(session_id: str):
    """
    Returns the stored history of one session from SQLite, oldest first, without the system prompt.
    Returns 404 {"detail": "session not found"} if session does not exist.
    """
    if not session_id or not session_id.strip():
        raise HTTPException(status_code=422, detail="session_id is required")

    session_id_clean = session_id.strip()
    if not session_exists(session_id_clean):
        raise HTTPException(status_code=404, detail="session not found")
        
    messages = get_messages_by_session(session_id_clean)
    return SessionHistoryResponse(
        session_id=session_id_clean,
        messages=messages
    )
