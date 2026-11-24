import os
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "true"
import time
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Configure environment before importing app
os.environ["DATABASE_URL"] = "sqlite:///./test_data/test_app.db"
os.environ["LLM_API_KEYS"] = "key_1:test_secret_1,key_2:test_secret_2"
os.environ["LLM_MODEL"] = "gemini/gemini-2.0-flash"
os.environ["ENABLE_FAILURE_SIMULATION"] = "true"

from app.main import app
from app.database import init_db, get_db_connection
from app.cache_service import cache_service


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def setup_teardown():
    """Reset database and cache before each test."""
    cache_service.clear()
    init_db()
    conn = get_db_connection()
    with conn:
        conn.execute("DELETE FROM messages;")
    conn.close()
    yield


def make_mock_llm_response(text="The capital of France is Paris.", prompt_tokens=42, completion_tokens=9):
    mock_resp = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = text
    mock_resp.choices = [mock_choice]
    mock_resp.usage = MagicMock()
    mock_resp.usage.prompt_tokens = prompt_tokens
    mock_resp.usage.completion_tokens = completion_tokens
    return mock_resp


# 1. Health endpoint test
def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["keys_configured"] == 2
    assert data["cache_enabled"] is True


# 2. First message produces LIVE_INFERENCE
def test_first_message_live_inference(client):
    with patch("litellm.completion", return_value=make_mock_llm_response("Paris is the capital.", 40, 10)):
        res = client.post("/chat", json={
            "session_id": "s-test-1",
            "message": "What is the capital of France?"
        })
        assert res.status_code == 200
        data = res.json()
        assert data["session_id"] == "s-test-1"
        assert data["reply"] == "Paris is the capital."
        meta = data["metadata"]
        assert meta["resolution_source"] == "LIVE_INFERENCE"
        assert meta["key_id"] == "key_1"
        assert meta["fallback_attempts"] == 0
        assert meta["input_tokens"] == 40
        assert meta["output_tokens"] == 10


# 3. Same first message in a new session produces LLM_CACHE
def test_same_message_new_session_cache_hit(client):
    # Session 1: Live call
    with patch("litellm.completion", return_value=make_mock_llm_response("Paris.", 30, 5)):
        res1 = client.post("/chat", json={
            "session_id": "session-A",
            "message": "Capital of France?"
        })
        assert res1.status_code == 200
        assert res1.json()["metadata"]["resolution_source"] == "LIVE_INFERENCE"

    # Session 2: Same prompt in new session -> must hit cache
    res2 = client.post("/chat", json={
        "session_id": "session-B",
        "message": "Capital of France?"
    })
    assert res2.status_code == 200
    data2 = res2.json()
    meta2 = data2["metadata"]
    assert meta2["resolution_source"] == "LLM_CACHE"
    assert meta2["key_id"] is None
    assert meta2["fallback_attempts"] == 0
    assert data2["reply"] == "Paris."
    assert meta2["input_tokens"] == 30
    assert meta2["output_tokens"] == 5


# 4. Different message does not return unrelated cached content
def test_different_message_does_not_hit_cache(client):
    with patch("litellm.completion", side_effect=[
        make_mock_llm_response("Answer 1", 20, 5),
        make_mock_llm_response("Answer 2", 25, 8)
    ]):
        res1 = client.post("/chat", json={"session_id": "s-diff-1", "message": "First query"})
        assert res1.json()["reply"] == "Answer 1"
        assert res1.json()["metadata"]["resolution_source"] == "LIVE_INFERENCE"

        res2 = client.post("/chat", json={"session_id": "s-diff-2", "message": "Completely different query"})
        assert res2.json()["reply"] == "Answer 2"
        assert res2.json()["metadata"]["resolution_source"] == "LIVE_INFERENCE"


# 5. Key 1 fails with 429 -> successfully falls back to key_2
def test_key_failover_429(client):
    with patch("litellm.completion", return_value=make_mock_llm_response("Fallback success", 35, 12)):
        res = client.post(
            "/chat",
            headers={"X-Simulate-Failure": "key_1=429"},
            json={"session_id": "s-fail-1", "message": "Test failover"}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["reply"] == "Fallback success"
        meta = data["metadata"]
        assert meta["resolution_source"] == "LIVE_INFERENCE"
        assert meta["key_id"] == "key_2"
        assert meta["fallback_attempts"] == 1


# 6. Key 1 fails with 500 -> successfully falls back to key_2
def test_key_failover_500(client):
    with patch("litellm.completion", return_value=make_mock_llm_response("Fallback from 500", 35, 12)):
        res = client.post(
            "/chat",
            headers={"X-Simulate-Failure": "key_1=500"},
            json={"session_id": "s-fail-2", "message": "Test 500 failover"}
        )
        assert res.status_code == 200
        data = res.json()
        meta = data["metadata"]
        assert meta["key_id"] == "key_2"
        assert meta["fallback_attempts"] == 1


# 7. Simulation *=429 returns 503 {"detail": "all providers unavailable"}
def test_all_keys_failed_returns_503(client):
    res = client.post(
        "/chat",
        headers={"X-Simulate-Failure": "*=429"},
        json={"session_id": "s-fail-all", "message": "Test total failure"}
    )
    assert res.status_code == 503
    assert res.json() == {"detail": "all providers unavailable"}

    # Check that failed request was NOT stored in database
    hist_res = client.get("/sessions/s-fail-all/messages")
    assert hist_res.status_code == 404


# 8. Multi-key failover chain key_1=429,key_2=500 returns 503 when all configured keys fail
def test_failover_chain_exhaustion(client):
    res = client.post(
        "/chat",
        headers={"X-Simulate-Failure": "key_1=429,key_2=500"},
        json={"session_id": "s-chain", "message": "Testing failover chain"}
    )
    assert res.status_code == 503
    assert res.json() == {"detail": "all providers unavailable"}


# 9. Empty message returns HTTP 422
def test_empty_message_validation(client):
    res = client.post("/chat", json={"session_id": "s-val", "message": "   "})
    assert res.status_code == 422
    assert "detail" in res.json()


# 10. Message over 4000 characters returns HTTP 422
def test_message_too_long_validation(client):
    long_msg = "A" * 4001
    res = client.post("/chat", json={"session_id": "s-val", "message": long_msg})
    assert res.status_code == 422
    assert "detail" in res.json()


# 11. Multi-turn conversation preserves history
def test_multiturn_conversation(client):
    with patch("litellm.completion", side_effect=[
        make_mock_llm_response("My name is Lyftr Assistant.", 20, 10),
        make_mock_llm_response("Your name is Alice.", 45, 8)
    ]) as mock_comp:
        # Turn 1
        client.post("/chat", json={"session_id": "s-multi", "message": "Hello, my name is Alice."})
        
        # Turn 2
        client.post("/chat", json={"session_id": "s-multi", "message": "What is my name?"})
        
        # Verify litellm was called with full context on Turn 2
        call_args_turn2 = mock_comp.call_args_list[1]
        sent_messages = call_args_turn2[1]["messages"]
        roles = [m["role"] for m in sent_messages]
        assert roles == ["user", "assistant", "user"]
        assert sent_messages[0]["content"] == "Hello, my name is Alice."
        assert sent_messages[2]["content"] == "What is my name?"


# 12. Separate sessions remain isolated
def test_session_isolation(client):
    with patch("litellm.completion", side_effect=[
        make_mock_llm_response("Reply session 1", 20, 5),
        make_mock_llm_response("Reply session 2", 20, 5)
    ]) as mock_comp:
        client.post("/chat", json={"session_id": "s-iso-1", "message": "Secret in 1"})
        client.post("/chat", json={"session_id": "s-iso-2", "message": "Query in 2"})
        
        call_session_2 = mock_comp.call_args_list[1][1]["messages"]
        # Session 2 must NOT contain messages from Session 1
        assert len(call_session_2) == 1
        assert call_session_2[0]["content"] == "Query in 2"


# 13. History endpoint returns chronological messages
def test_history_endpoint(client):
    with patch("litellm.completion", return_value=make_mock_llm_response("Response 1", 20, 5)):
        client.post("/chat", json={"session_id": "s-hist", "message": "Query 1"})

    res = client.get("/sessions/s-hist/messages")
    assert res.status_code == 200
    data = res.json()
    assert data["session_id"] == "s-hist"
    assert len(data["messages"]) == 2
    assert data["messages"][0]["role"] == "user"
    assert data["messages"][0]["content"] == "Query 1"
    assert data["messages"][1]["role"] == "assistant"
    assert data["messages"][1]["content"] == "Response 1"
    assert data["messages"][1]["metadata"]["resolution_source"] == "LIVE_INFERENCE"


# 14. Unknown session returns 404
def test_unknown_session_404(client):
    res = client.get("/sessions/non-existent-session-id/messages")
    assert res.status_code == 404
    assert res.json() == {"detail": "session not found"}


# 15. Token usage is per request, never cumulative
def test_token_usage_per_request_not_cumulative(client):
    # Two identical length first messages in separate sessions must report approximately equal input tokens
    with patch("litellm.completion", side_effect=[
        make_mock_llm_response("Reply A", 25, 10),
        make_mock_llm_response("Reply B", 25, 10)
    ]):
        res1 = client.post("/chat", json={"session_id": "s-tok-1", "message": "Hello world"})
        res2 = client.post("/chat", json={"session_id": "s-tok-2", "message": "Hello world"})
        
        assert res1.json()["metadata"]["input_tokens"] == 25
        # If it's a new session, it's a cache hit or live with 25 tokens, never 50
        meta2 = res2.json()["metadata"]
        assert meta2["input_tokens"] == 25
        assert meta2["output_tokens"] == 10


# 16. Cache hit latency is faster than live inference
def test_cache_hit_latency(client):
    def slow_llm_completion(*args, **kwargs):
        time.sleep(0.05)
        return make_mock_llm_response("Slow reply", 20, 5)

    with patch("litellm.completion", side_effect=slow_llm_completion):
        res1 = client.post("/chat", json={"session_id": "s-lat-1", "message": "Latency check"})
        latency_live = res1.json()["metadata"]["latency_ms"]
        assert latency_live >= 50

    # Cache hit
    res2 = client.post("/chat", json={"session_id": "s-lat-2", "message": "Latency check"})
    latency_cache = res2.json()["metadata"]["latency_ms"]
    assert res2.json()["metadata"]["resolution_source"] == "LLM_CACHE"
    assert latency_cache < latency_live
