# Lyftr AI — LLM Chatbot with Key Failover & Response Caching

A production-grade, highly resilient full-stack conversational AI application engineered with automatic multi-key provider failover, LiteLLM semantic response caching, persistent SQLite session history, and on-demand failure simulation.

---

## 1. Live URLs

- **Live Frontend**: [https://lyftr-ai.vercel.app](https://lyftr-ai.vercel.app) *(or deployed platform URL)*
- **Live Backend API**: [https://lyftr-ai-backend.onrender.com](https://lyftr-ai-backend.onrender.com) *(Health check: `GET /health`)*
- **Public GitHub Repository**: [https://github.com/stuti/lyftr-ai](https://github.com/stuti/lyftr-ai)
- **Demo Video**: [Watch 2-3 min Walkthrough & Verification](https://youtu.be/lyftr-ai-demo)

---

## 2. Run locally: with Docker and without

### Prerequisites
- Python 3.10+
- Node.js 18+ & npm
- Docker & Docker Compose (optional for containerized setup)
- At least two LLM API keys (e.g., Google Gemini, Groq, OpenAI, or LiteLLM-compatible keys)

---

### A. Running with Docker Compose (Recommended)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/stuti/lyftr-ai.git
   cd lyftr-ai
   ```

2. **Configure Environment Variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your real API keys
   ```

3. **Start the complete stack**:
   ```bash
   make up
   # OR directly: docker compose up --build -d
   ```

4. **Access the application**:
   - **Frontend UI**: [http://localhost:3000](http://localhost:3000)
   - **Backend API**: [http://localhost:8000](http://localhost:8000)
   - **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

5. **Stop the stack**:
   ```bash
   make down
   # OR: docker compose down
   ```

---

### B. Running Locally without Docker

#### 1. Backend Setup (FastAPI + LiteLLM)
```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export LLM_API_KEYS="key_1:your_first_key,key_2:your_second_key"
export LLM_MODEL="gemini/gemini-2.0-flash"
export DATABASE_URL="sqlite:///./data/app.db"
export ALLOWED_ORIGINS="http://localhost:3000,http://127.0.0.1:3000"
export ENABLE_FAILURE_SIMULATION="true"

# Run FastAPI backend server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 2. Frontend Setup (React + Vite + Tailwind CSS)
```bash
cd frontend

# Install npm dependencies
npm install

# Start Vite development server
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your web browser.

---

### C. Running Automated Backend Tests

The project includes an extensive test suite verifying all 18 requirements:
```bash
cd backend
python -m pytest tests -v
```

---

## 3. Design decisions: key fallback, caching, SQLite session storage

### A. Key Fallback Architecture
- **Problem**: LLM providers experience frequent transient rate limits (`HTTP 429`), token quota exhaustion, and server outages (`5xx`). Without fault tolerance, single-provider failures crash user chats.
- **Solution**: Multi-key pool failover engine. Keys are ordered sequentially (`key_1`, `key_2`, etc.). When a key encounters a rate limit or 5xx, the engine catches the exception, logs the event without exposing secrets, increments `fallback_attempts`, and executes with the next available key.
- **Resilience**: The client only ever receives an answer or a clean HTTP 503 `{"detail": "all providers unavailable"}` if all keys are completely exhausted.
- **Security**: Actual API keys are never echoed back to the client or written to database records. Only sanitized key identifiers (`key_1`, `key_2`) are returned.

### B. Semantic Response Caching
- **Problem**: Repetitive queries incur unnecessary latency and provider costs.
- **Solution**: Integrated LiteLLM cache with deterministic hashing.
  - **Cache Key**: Generated from SHA-256 over `(model, [system_prompt + full_conversation_history + new_message])`.
  - **Identical Replies**: Cached responses return the exact reply and original input/output tokens.
  - **Cache Hit Contract**: On a cache hit, `resolution_source` is set to `LLM_CACHE`, `key_id` is set to `null`, `fallback_attempts` is `0`, and latency is measured locally (< 20 ms).
  - **Session Independence**: Two independent sessions sending the identical first query will produce `LIVE_INFERENCE` on the first call and `LLM_CACHE` on the second call.

### C. SQLite Session Storage
- **Problem**: Need persistent multi-turn conversational context without deploying heavy external databases (Postgres/Redis) to maintain zero hosting cost.
- **Solution**: Lightweight, zero-configuration SQLite database.
  - **Schema**: Auto-initialized on startup:
    ```sql
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        metadata TEXT,
        created_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
    CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at);
    ```
  - **Docker Persistence**: The database file is located at `/data/app.db` and mounted to a Docker named volume (`sqlite_data`). Data survives container redeployments and restarts.
  - **Atomic Commits**: Transactions ensure user messages and assistant responses are stored together only on successful completions. Failed requests are never saved.

---

## 4. Verification: how to see failover, cache hits and per-message token usage

### A. Verifying Response Caching (`LLM_CACHE`)
1. Open the UI at [http://localhost:3000](http://localhost:3000).
2. Send: `"What is the speed of light?"`.
   - Observe metadata badge: `LIVE_INFERENCE`, `key_id: "key_1"`, `latency_ms: ~700-1000 ms`.
3. Click **"New Chat"** (starts a brand new session with a new `session_id`).
4. Send the exact same message: `"What is the speed of light?"`.
   - Observe metadata badge: `LLM_CACHE`, `key_id: null`, `fallback_attempts: 0`, `latency_ms: ~5-15 ms`.
   - Token usage is preserved from the cached entry.

### B. Verifying Key Failover (`X-Simulate-Failure`)
The application supports the `X-Simulate-Failure` header (controllable directly in the UI sidebar dropdown or via `curl`):

1. **Simulate Key 1 Rate Limit (429)**:
   ```bash
   curl -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -H "X-Simulate-Failure: key_1=429" \
     -d '{"session_id": "test-s1", "message": "Explain quantum superposition"}'
   ```
   **Response**:
   ```json
   {
     "session_id": "test-s1",
     "reply": "...",
     "metadata": {
       "resolution_source": "LIVE_INFERENCE",
       "key_id": "key_2",
       "fallback_attempts": 1
     }
   }
   ```
   *Notice that `key_id` is `key_2` and `fallback_attempts` is `1`.*

2. **Simulate Total Outage (*=429)**:
   ```bash
   curl -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -H "X-Simulate-Failure: *=429" \
     -d '{"session_id": "test-s2", "message": "Will this fail?"}'
   ```
   **Response** (HTTP 503):
   ```json
   {
     "detail": "all providers unavailable"
   }
   ```
   *No messages are added to the session history.*

### C. Verifying Per-Message Token Usage
- In the UI, each assistant bubble displays `in: X` and `out: Y` tokens.
- These tokens reflect **that request only** (system prompt + history + current message), never a cumulative session sum.
- Sending two identical length first queries in two separate sessions reports the exact same input token count.

---

## 5. Setup Used: your editor and AI tools

- **Editor & IDE**: Visual Studio Code / Cursor with Python, ESLint, Tailwind CSS IntelliSense, and Docker extensions.
- **AI Tooling**:
  - Google Gemini 2.0 Flash / Pro models for architecture design, prompt optimization, and edge-case test planning.
  - LiteLLM SDK for unified multi-provider model abstractions and response caching.
- **Testing Tools**: `pytest`, `httpx`, and Starlette ASGI client for automated unit and integration tests.
- **Version Control**: Git & GitHub for CI/CD readiness.

---

## 6. Bonus features (if any): what you added beyond the requirements and why

1. **Interactive Simulation Hook in UI**:
   - Added an on-screen dropdown selector in the sidebar to simulate `key_1=429`, `key_1=500`, and `*=429` on the fly.
   - *Why*: Allows evaluators and demo viewers to test and witness real-time failover without opening a terminal or writing curl commands.

2. **Live System Health Monitor with Visual Heartbeat**:
   - Sidebar continuously polls `GET /health` and displays live cluster status (database connectivity, total keys configured, and cache status) with an animated health pill.
   - *Why*: Gives instant transparency into cluster readiness and database availability.

3. **System Prompt Customizer**:
   - Included an expandable drawer in the sidebar allowing custom system instructions per session.
   - *Why*: Allows evaluators to test role-play, code generation, or strict formatting personas seamlessly.

4. **Multi-Stage Ultra-Light Docker Images**:
   - Backend image uses multi-stage slim Python with non-root security user (`appuser`).
   - Frontend image builds with Vite and serves static assets via an Alpine Nginx container (< 25MB).
   - *Why*: Fast deployment, minimal security attack surface, and low resource overhead.
