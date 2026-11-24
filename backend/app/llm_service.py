import os
import sys
import types
import time
import logging
from typing import List, Dict, Any, Optional, Tuple
from fastapi import HTTPException

# Offline flag for local model cost map
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"

# Compatibility shim for environments where compiled Rust extension DLLs are restricted
try:
    from litellm.rust_bridge import _native
except (ImportError, Exception):
    class DummyObj(Exception):
        def __init__(self, *args, **kwargs): pass
        def __call__(self, *args, **kwargs): return self
        def __getattr__(self, k): return DummyObj()
        def __iter__(self): return iter([])

    class DummyModule(types.ModuleType):
        def __getattr__(self, name): return DummyObj

    sys.modules['litellm.rust_bridge._native'] = DummyModule('litellm.rust_bridge._native')

import litellm
from app.config import settings
from app.cache_service import cache_service

logger = logging.getLogger("lyftr.llm")

# Prevent litellm from printing verbose logs or telemetries
litellm.telemetry = False
litellm.suppress_debug_info = True


class SimulatedProviderError(Exception):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code


def parse_simulate_failure_header(header_value: Optional[str]) -> Dict[str, int]:
    """
    Parses X-Simulate-Failure header value into a dictionary.
    Examples:
      'key_1=429' -> {'key_1': 429}
      'key_1=429,key_2=500' -> {'key_1': 429, 'key_2': 500}
      '*=429' -> {'*': 429}
    Allowed codes: 429, 500, 502, 503.
    """
    if not header_value:
        return {}
    
    simulation_map = {}
    tokens = [t.strip() for t in header_value.split(",") if t.strip()]
    for token in tokens:
        if "=" in token:
            target, code_str = token.split("=", 1)
            target = target.strip()
            try:
                code = int(code_str.strip())
                if code in (429, 500, 502, 503):
                    simulation_map[target] = code
                else:
                    logger.warning(f"Unsupported simulated status code: {code}")
            except ValueError:
                logger.warning(f"Invalid simulated status code string: {code_str}")
    return simulation_map


def estimate_tokens(text: str) -> int:
    """Estimates tokens for fallback tracking if provider does not return usage."""
    if not text:
        return 0
    return max(1, len(text.split()) * 4 // 3)


def execute_llm_completion(
    model: str,
    messages: List[Dict[str, str]],
    simulate_header: Optional[str] = None
) -> Tuple[str, Dict[str, Any]]:
    """
    Executes completion with LiteLLM caching and multi-key failover.

    Returns:
      reply: str
      metadata: dict with resolution_source, model, latency_ms, input_tokens, output_tokens, key_id, fallback_attempts
    """
    start_time = time.perf_counter()

    # 1. Check LiteLLM Response Cache FIRST
    cached = cache_service.get(model=model, messages=messages)
    if cached is not None:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        metadata = {
            "resolution_source": "LLM_CACHE",
            "model": model,
            "latency_ms": latency_ms,
            "input_tokens": cached["input_tokens"],
            "output_tokens": cached["output_tokens"],
            "key_id": None,
            "fallback_attempts": 0
        }
        return cached["reply"], metadata

    # 2. Parse Failure Simulation Header
    simulations: Dict[str, int] = {}
    if settings.ENABLE_FAILURE_SIMULATION and simulate_header:
        simulations = parse_simulate_failure_header(simulate_header)

    configured_keys = settings.parsed_keys
    if not configured_keys:
        logger.error("No LLM API keys configured!")
        raise HTTPException(status_code=503, detail="all providers unavailable")

    fallback_attempts = 0
    last_error: Optional[Exception] = None

    for key_id, api_key in configured_keys:
        # Check simulation rule
        simulated_code = simulations.get("*") or simulations.get(key_id)
        if simulated_code:
            logger.info(f"Simulating failure {simulated_code} on key '{key_id}'")
            fallback_attempts += 1
            last_error = SimulatedProviderError(simulated_code, f"Simulated provider error {simulated_code}")
            continue

        try:
            # Live LiteLLM inference attempt
            logger.info(f"Attempting inference with key '{key_id}' on model '{model}'")
            response = litellm.completion(
                model=model,
                messages=messages,
                api_key=api_key,
                timeout=30.0
            )

            # Extract response text
            reply = response.choices[0].message.content or ""

            # Extract token usage
            input_tokens = 0
            output_tokens = 0
            if hasattr(response, "usage") and response.usage:
                input_tokens = getattr(response.usage, "prompt_tokens", 0) or 0
                output_tokens = getattr(response.usage, "completion_tokens", 0) or 0
            
            if input_tokens == 0:
                input_tokens = sum(estimate_tokens(m["content"]) for m in messages)
            if output_tokens == 0:
                output_tokens = estimate_tokens(reply)

            # Store in cache
            cache_service.set(
                model=model,
                messages=messages,
                reply=reply,
                input_tokens=input_tokens,
                output_tokens=output_tokens
            )

            latency_ms = int((time.perf_counter() - start_time) * 1000)
            metadata = {
                "resolution_source": "LIVE_INFERENCE",
                "model": model,
                "latency_ms": latency_ms,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "key_id": key_id,
                "fallback_attempts": fallback_attempts
            }
            return reply, metadata

        except Exception as e:
            # Handle failover on 429, 500, 502, 503, etc.
            status_code = getattr(e, "status_code", None) or getattr(e, "http_status", None)
            logger.warning(f"Key '{key_id}' failed with exception: {type(e).__name__} (status: {status_code})")
            fallback_attempts += 1
            last_error = e
            continue

    # All keys exhausted
    logger.error(f"All {len(configured_keys)} keys failed! Last error: {last_error}")
    raise HTTPException(status_code=503, detail="all providers unavailable")
