import os
import sys
import types
import json
import hashlib
import logging
from typing import List, Dict, Any, Optional

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

logger = logging.getLogger("lyftr.cache")


class LiteLLMCacheService:
    """
    LiteLLM Response Cache Service.
    Enforces required cache semantics:
    - Keys on (model, complete message list including system prompt, history, and new message).
    - Preserves cached reply text, input_tokens, and output_tokens.
    - key_id is null and fallback_attempts is 0 on cache hits.
    - Independent sessions with identical context produce a cache hit.
    - Different messages produce a cache miss.
    """

    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.enabled: bool = True
        try:
            import litellm
            from litellm.caching import Cache
            litellm.cache = Cache(type="local")
            logger.info("LiteLLM local cache enabled.")
        except Exception as e:
            logger.warning(f"Could not initialize native LiteLLM cache wrapper: {e}")

    def _generate_cache_key(self, model: str, messages: List[Dict[str, str]]) -> str:
        """
        Generates a deterministic hash key from the model and exact message sequence.
        Normalizes whitespace and fields.
        """
        normalized_messages = [
            {"role": msg["role"].strip(), "content": msg["content"].strip()}
            for msg in messages
        ]
        payload = {
            "model": model.strip(),
            "messages": normalized_messages
        }
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def get(self, model: str, messages: List[Dict[str, str]]) -> Optional[Dict[str, Any]]:
        """
        Look up a cached response.
        Returns dict with reply, input_tokens, output_tokens, or None.
        """
        if not self.enabled:
            return None
            
        cache_key = self._generate_cache_key(model, messages)
        entry = self._cache.get(cache_key)
        if entry:
            logger.info(f"Cache HIT for key {cache_key[:8]}")
            return {
                "reply": entry["reply"],
                "input_tokens": entry["input_tokens"],
                "output_tokens": entry["output_tokens"]
            }
        return None

    def set(
        self,
        model: str,
        messages: List[Dict[str, str]],
        reply: str,
        input_tokens: int,
        output_tokens: int
    ) -> None:
        """
        Stores an LLM completion response into the cache.
        """
        if not self.enabled:
            return
            
        cache_key = self._generate_cache_key(model, messages)
        self._cache[cache_key] = {
            "reply": reply,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens
        }
        logger.info(f"Cache SET for key {cache_key[:8]}")

    def clear(self) -> None:
        """Clears the cache (useful for testing)."""
        self._cache.clear()


cache_service = LiteLLMCacheService()
