# Lyftr AI — 2-3 Minute Video Demo Narration Script

This script provides the exact walkthrough for recording the 2–3 minute submission demo video.

---

### Timing & Sequence Overview

| Timestamp | Screen / Visual | Narration / Action | Key Requirement Demonstrated |
| :--- | :--- | :--- | :--- |
| **0:00 - 0:25** | Open live Frontend in browser. Show branding, clean UI, and System Health in sidebar. | "Hello everyone! This is the Lyftr AI full-stack chatbot, engineered for zero-downtime resilience with multi-key failover and LiteLLM response caching. The frontend is built in React and Tailwind CSS, communicating with a FastAPI backend and SQLite database." | UI Contract, Clean SaaS Design, System Health |
| **0:25 - 0:55** | Type: `"What is the capital of France?"` and send. Show assistant reply and inspect metadata. | "Let's send our first query. Notice the response metadata: `resolution_source` is `LIVE_INFERENCE`, `key_id` is `key_1`, latency is 780ms, and we see exact per-request input and output tokens." | LIVE_INFERENCE, Token Tracking, Metadata display |
| **0:55 - 1:25** | Click **"New Chat"**. Send exact same message: `"What is the capital of France?"`. | "Now, let's start a new chat session with a fresh session ID. We send the exact same question. Look at the result: `resolution_source` is now `LLM_CACHE`. The latency dropped to 12ms, `key_id` is null, and token counts are preserved from the cache. The bot answered instantly without calling the external API." | LLM_CACHE, Cache Hit Contract, Fast Latency |
| **1:25 - 1:55** | In sidebar, select `key_1=429` under the simulation dropdown. Send `"Explain quantum computing"`. | "Next, let's demonstrate automatic key failover. I will simulate a 429 rate limit on `key_1` using the `X-Simulate-Failure` hook. When we send the message, the backend catches the 429 on `key_1`, logs it, and automatically fails over to `key_2`. Notice `key_id` is `key_2` and `fallback_attempts` is `1`. The user experienced zero disruption." | Multi-Key Failover, X-Simulate-Failure, Zero Downtime |
| **1:55 - 2:25** | In sidebar, select `*=429`. Send another query. Show HTTP 503 error message in UI. | "Now, what happens if every configured key fails? Let's simulate `*=429`. When we send the request, the backend returns a clean HTTP 503 with `detail: all providers unavailable`. In the chat, a graceful error badge appears with no blank screen or stack trace, and nothing is added to SQLite history." | 503 Provider Exhaustion, Error Handling, Safe DB State |
| **2:25 - 2:55** | Open browser DevTools / new tab. Visit `GET /health` and `GET /sessions/{session_id}/messages`. Show public GitHub repo. | "Finally, let's look at the endpoints. `GET /health` shows status ok, keys configured: 2, and cache enabled: true. `GET /sessions/.../messages` retrieves chronological history from SQLite. The entire project is open-source on GitHub with multi-stage Dockerfiles and one-command `make up` deployment. Thank you!" | Backend API Contract, SQLite Persistence, Public Repo |

---

### Step-by-Step Recording Checklist

1. **Window Setup**:
   - Left half: Browser with Lyftr AI frontend (`http://localhost:3000` or live URL).
   - Right half: Browser tab ready with `http://localhost:8000/health` and GitHub repo.
2. **Audio Check**:
   - Clear microphone input, 1080p 60fps screen capture.
3. **Pacing**:
   - Speak clearly and highlight the metadata badges (`LIVE_INFERENCE` vs `LLM_CACHE`, `key_id`, `latency_ms`).
