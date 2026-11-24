import os
from pathlib import Path
from typing import List, Tuple
from dotenv import load_dotenv

# Ensure LiteLLM uses local cached model cost map and skips remote network polls
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "true"

load_dotenv()


class Settings:
    def __init__(self):
        # Database URL
        self.DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:////data/app.db")
        
        # LLM Model
        self.LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini/gemini-3.5-flash-lite")
        
        # Raw API Keys string
        self.RAW_LLM_API_KEYS: str = os.getenv("LLM_API_KEYS", "key_1:test_key_1,key_2:test_key_2")
        
        # Allowed origins for CORS (strip trailing slashes so pasted URLs match browser Origin headers)
        raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
        self.ALLOWED_ORIGINS: List[str] = [
            origin.strip().rstrip("/") for origin in raw_origins.split(",") if origin.strip()
        ]
        if "*" in self.ALLOWED_ORIGINS:
            self.ALLOWED_ORIGINS = ["*"]

        # PORT – Render injects this; used by Dockerfile CMD
        self.PORT: int = int(os.getenv("PORT", "8000"))
            
        # Failure simulation flag
        self.ENABLE_FAILURE_SIMULATION: bool = os.getenv("ENABLE_FAILURE_SIMULATION", "true").lower() in ("true", "1", "yes")

    @property
    def parsed_keys(self) -> List[Tuple[str, str]]:
        """
        Parses LLM_API_KEYS into a list of (key_id, api_key) tuples.
        Supports:
        1. 'key_1:sk-xxx,key_2:sk-yyy'
        2. 'sk-xxx,sk-yyy' -> mapped automatically to ('key_1', 'sk-xxx'), ('key_2', 'sk-yyy')
        """
        if not self.RAW_LLM_API_KEYS or not self.RAW_LLM_API_KEYS.strip():
            return []
            
        entries = [e.strip() for e in self.RAW_LLM_API_KEYS.split(",") if e.strip()]
        result = []
        for i, entry in enumerate(entries, start=1):
            if ":" in entry:
                key_id, key_val = entry.split(":", 1)
                result.append((key_id.strip(), key_val.strip()))
            else:
                result.append((f"key_{i}", entry.strip()))
        return result

    @property
    def sqlite_db_path(self) -> str:
        """
        Extracts and resolves a valid filesystem path from DATABASE_URL.
        Gracefully falls back to local ./data/app.db if /data is not accessible.
        """
        url = self.DATABASE_URL
        if url.startswith("sqlite:///"):
            path_str = url[len("sqlite:///"):]
            if path_str.startswith("/") and len(path_str) > 2 and path_str[2] == ":":
                # Windows path like /C:/data/app.db
                path_str = path_str[1:]
        elif url.startswith("sqlite://"):
            path_str = url[len("sqlite://"):]
        else:
            path_str = url

        db_path = Path(path_str)
        for candidate in (db_path, Path("./data/app.db"), Path("/tmp/data/app.db")):
            try:
                candidate.parent.mkdir(parents=True, exist_ok=True)
                test_file = candidate.parent / ".perm_check"
                test_file.touch()
                test_file.unlink()
                return str(candidate.resolve())
            except (OSError, PermissionError):
                continue
        return str(Path("/tmp/data/app.db"))


settings = Settings()
