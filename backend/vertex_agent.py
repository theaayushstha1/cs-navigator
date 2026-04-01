"""
Vertex AI Agent Engine Client
==============================

Communicates with the CS Navigator agent running on Google ADK web server.
Handles session management and SSE response parsing.

v4.2: Smart session reuse. Sessions are cached per user with a TTL and
context hash. If the same user sends multiple queries with the same
DegreeWorks data, we reuse the existing session instead of creating a
new one each time. Saves ~100-200ms per request.

Usage:
    Local dev:  ADK web server at http://127.0.0.1:8080
    Production: Vertex AI Agent Engine (deployed reasoning engine)
"""

import os
import json
import re
import hashlib
import time as time_module
import requests
from typing import Optional

# Configuration
ADK_BASE_URL = os.getenv("ADK_BASE_URL", "http://127.0.0.1:8080")
ADK_APP_NAME = os.getenv("ADK_APP_NAME", "cs_navigator_unified")

# Session reuse settings
SESSION_TTL = 1800  # 30 minutes: reuse sessions within this window

# Session cache: user_id -> {"session_id", "created_at", "context_hash"}
_session_cache: dict[str, dict] = {}


def _compute_context_hash(context: str) -> str:
    """Hash the DegreeWorks context string to detect changes between queries."""
    if not context:
        return ""
    return hashlib.md5(context.encode()).hexdigest()[:12]


def _create_session(user_id: str, state: Optional[dict] = None) -> str:
    """Create a new ADK session for the user, optionally with initial state.
    Retries once on timeout to handle Cloud Run cold starts on the ADK service."""
    import time as _time
    body = {"state": state} if state else {}
    for attempt in range(2):
        try:
            resp = requests.post(
                f"{ADK_BASE_URL}/apps/{ADK_APP_NAME}/users/{user_id}/sessions",
                headers={"Content-Type": "application/json"},
                json=body,
                timeout=30,
            )
            resp.raise_for_status()
            session_id = resp.json().get("id")
            if session_id:
                print(f"   ADK session created: {session_id} for user {user_id} (attempt {attempt+1})")
                return session_id
        except Exception as e:
            print(f"   ADK session attempt {attempt+1} failed: {e}")
            if attempt == 0:
                _time.sleep(2)
    return ""


def _get_valid_session(user_id: str, context: str = "", model: str = "") -> Optional[str]:
    """Return a cached session ID if it exists, hasn't expired, and context/model matches."""
    cached = _session_cache.get(user_id)
    if not cached:
        return None

    age = time_module.time() - cached["created_at"]
    ctx_hash = _compute_context_hash(context)

    if age >= SESSION_TTL:
        print(f"   ADK session expired (age={age:.0f}s), creating new")
        _session_cache.pop(user_id, None)
        return None

    if cached["context_hash"] != ctx_hash:
        print(f"   ADK session context changed, creating new")
        _session_cache.pop(user_id, None)
        return None

    if cached.get("model", "") != model:
        print(f"   ADK session model changed ({cached.get('model', '')} -> {model}), creating new")
        _session_cache.pop(user_id, None)
        return None

    print(f"   ADK session reused: {cached['session_id']} (age={age:.0f}s)")
    return cached["session_id"]


def _cache_session(user_id: str, session_id: str, context: str = "", model: str = ""):
    """Store a session in the reuse cache."""
    _session_cache[user_id] = {
        "session_id": session_id,
        "created_at": time_module.time(),
        "context_hash": _compute_context_hash(context),
        "model": model,
    }


def query_agent(query: str, user_id: str = "default", context: str = "", model: str = "", canvas_context: str = "") -> str:
    """
    Send a query to the CS Navigator agent and return the final text response.

    Reuses ADK sessions when the user's DegreeWorks context hasn't changed.
    Canvas data is sent via state_delta (volatile, changes often).

    Args:
        query: The user's question
        user_id: Unique user identifier
        context: DegreeWorks student data (injected into session state, stable)
        model: Model preference ("inav-1.0" or "inav-1.1")
        canvas_context: Canvas LMS data (sent via state_delta, volatile)
    """
    # Session reuse: hash only DegreeWorks (stable), NOT Canvas (volatile)
    session_id = _get_valid_session(user_id, context, model)

    if not session_id:
        state = {}
        if context:
            state["degreeworks"] = context
        if canvas_context:
            state["canvas"] = canvas_context
        if model:
            state["model_preference"] = model
        session_id = _create_session(user_id, state=state if state else None)
        if not session_id:
            return "The AI agent is currently unavailable. Please try again in a moment."
        _cache_session(user_id, session_id, context, model)

    return _run_query(query, user_id, session_id, context=context, model=model, canvas_context=canvas_context)


def _run_query(message: str, user_id: str, session_id: str, retried: bool = False, context: str = "", model: str = "", canvas_context: str = "") -> str:
    """Send a query to the ADK and parse the SSE response."""
    try:
        payload = {
            "app_name": ADK_APP_NAME,
            "user_id": user_id,
            "session_id": session_id,
            "new_message": {
                "role": "user",
                "parts": [{"text": message}],
            },
        }
        # Send volatile data via state_delta (Canvas changes often, model per-request)
        state_delta = {}
        if model:
            state_delta["model_preference"] = model
        if canvas_context:
            state_delta["canvas"] = canvas_context
        if state_delta:
            payload["state_delta"] = state_delta

        resp = requests.post(
            f"{ADK_BASE_URL}/run_sse",
            headers={"Content-Type": "application/json"},
            json=payload,
            stream=True,
            timeout=120,
        )

        # Handle "Session not found": recreate with DegreeWorks + Canvas state and retry once
        if resp.status_code == 404 and not retried:
            print(f"   ADK session {session_id} not found, creating a new one...")
            _session_cache.pop(user_id, None)
            state = {}
            if context:
                state["degreeworks"] = context
            if canvas_context:
                state["canvas"] = canvas_context
            if model:
                state["model_preference"] = model
            new_session_id = _create_session(user_id, state=state if state else None)
            if new_session_id:
                _cache_session(user_id, new_session_id, context, model)
                return _run_query(message, user_id, new_session_id, retried=True, context=context, model=model, canvas_context=canvas_context)
            return "The AI agent is currently unavailable. Please try again in a moment."

        resp.raise_for_status()

        # Parse SSE events and extract the final text response
        final_text = ""
        for line in resp.iter_lines():
            if not line:
                continue
            decoded = line.decode("utf-8")
            if not decoded.startswith("data: "):
                continue

            json_str = decoded[6:]  # Strip "data: " prefix
            try:
                event = json.loads(json_str)
            except json.JSONDecodeError:
                continue

            # Extract text from model responses (skip function_call / function_response)
            content = event.get("content", {})
            if not isinstance(content, dict):
                continue

            role = content.get("role", "")
            if role != "model":
                continue

            parts = content.get("parts", [])
            for part in parts:
                if isinstance(part, dict) and "text" in part:
                    final_text = part["text"]  # Keep last model text (the final answer)

        if final_text:
            # Clean up citation artifacts from Gemini grounding
            final_text = re.sub(r'\s*\[cite:\s*[^\]]*\]', '', final_text)
            return final_text.strip()
        else:
            return "I'm sorry, I couldn't generate a response. Please try rephrasing your question."

    except requests.exceptions.ConnectionError:
        print("   ADK server not reachable. Is it running on port 8080?")
        return "The AI agent is currently unavailable. Please try again in a moment."
    except requests.exceptions.Timeout:
        print("   ADK query timed out after 120s")
        return "The request took too long. Please try a simpler question."
    except Exception as e:
        print(f"   ADK query error: {e}")
        return f"An error occurred while processing your question. Please try again."


def check_agent_health() -> dict:
    """Check if the ADK agent server is healthy."""
    try:
        resp = requests.get(f"{ADK_BASE_URL}/list-apps", timeout=15)
        if resp.status_code == 200:
            apps = resp.json()
            has_navigator = any(
                ADK_APP_NAME in str(app) for app in (apps if isinstance(apps, list) else [apps])
            )
            return {
                "status": "connected",
                "message": f"ADK server running, app '{ADK_APP_NAME}' {'found' if has_navigator else 'not found'}",
            }
        return {"status": "error", "message": f"ADK server returned {resp.status_code}"}
    except requests.exceptions.ConnectionError:
        return {"status": "disconnected", "message": "ADK server not reachable"}
    except Exception as e:
        return {"status": "error", "message": str(e)[:100]}


def reset_session(user_id: str) -> None:
    """Reset the ADK session for a user (forces new session on next query)."""
    _session_cache.pop(user_id, None)


def query_agent_stream(query: str, user_id: str = "default", context: str = "", model: str = "", canvas_context: str = ""):
    """
    Send a query to the CS Navigator agent and stream text chunks as they arrive.

    Session reuse based on DegreeWorks (stable). Canvas sent via state_delta (volatile).
    """
    # Session reuse: hash only DegreeWorks (stable), NOT Canvas
    session_id = _get_valid_session(user_id, context, model)

    if not session_id:
        state = {}
        if context:
            state["degreeworks"] = context
        if canvas_context:
            state["canvas"] = canvas_context
        if model:
            state["model_preference"] = model
        session_id = _create_session(user_id, state=state if state else None)
        if not session_id:
            yield {"type": "error", "content": "The AI agent is currently unavailable. Please try again in a moment."}
            return
        _cache_session(user_id, session_id, context, model)

    yield from _run_query_stream(query, user_id, session_id, context=context, model=model, canvas_context=canvas_context)


def _run_query_stream(message: str, user_id: str, session_id: str, retried: bool = False, context: str = "", model: str = "", canvas_context: str = ""):
    """Stream query results from ADK, yielding text chunks as they arrive."""
    try:
        payload = {
            "app_name": ADK_APP_NAME,
            "user_id": user_id,
            "session_id": session_id,
            "new_message": {
                "role": "user",
                "parts": [{"text": message}],
            },
        }
        state_delta = {}
        if model:
            state_delta["model_preference"] = model
        if canvas_context:
            state_delta["canvas"] = canvas_context
        if state_delta:
            payload["state_delta"] = state_delta

        resp = requests.post(
            f"{ADK_BASE_URL}/run_sse",
            headers={"Content-Type": "application/json"},
            json=payload,
            stream=True,
            timeout=120,
        )

        # Handle "Session not found": recreate with DegreeWorks + Canvas state and retry once
        if resp.status_code == 404 and not retried:
            print(f"   ADK session {session_id} not found, creating a new one...")
            _session_cache.pop(user_id, None)
            state = {}
            if context:
                state["degreeworks"] = context
            if canvas_context:
                state["canvas"] = canvas_context
            if model:
                state["model_preference"] = model
            new_session_id = _create_session(user_id, state=state if state else None)
            if new_session_id:
                _cache_session(user_id, new_session_id, context, model)
                yield from _run_query_stream(message, user_id, new_session_id, retried=True, context=context, model=model, canvas_context=canvas_context)
                return
            yield {"type": "error", "content": "The AI agent is currently unavailable. Please try again in a moment."}
            return

        resp.raise_for_status()

        # Map tool/agent names to user-friendly status messages
        TOOL_STATUS_MAP = {
            "vertex_ai_search": "Searching knowledge base",
            "discovery_engine_search": "Searching knowledge base",
        }

        # Stream SSE events and yield text chunks + status updates
        full_text = ""
        for line in resp.iter_lines():
            if not line:
                continue
            decoded = line.decode("utf-8")
            if not decoded.startswith("data: "):
                continue

            json_str = decoded[6:]  # Strip "data: " prefix
            try:
                event = json.loads(json_str)
            except json.JSONDecodeError:
                continue

            content = event.get("content", {})
            if not isinstance(content, dict):
                continue

            role = content.get("role", "")
            parts = content.get("parts", [])

            # Check for tool calls and yield status updates
            for part in parts:
                if isinstance(part, dict):
                    # Handle function calls (tools being invoked)
                    if "functionCall" in part:
                        func_name = part["functionCall"].get("name", "")
                        args = part["functionCall"].get("args", {})
                        # Check for agent transfer
                        if func_name == "transfer_to_agent":
                            agent_name = args.get("agent_name", "specialist")
                            status = TOOL_STATUS_MAP.get(agent_name, f"Consulting {agent_name.replace('_', ' ')}")
                        else:
                            status = TOOL_STATUS_MAP.get(func_name, f"Processing {func_name.replace('_', ' ')}")
                        yield {"type": "status", "content": status}

            # Extract text from model responses
            if role != "model":
                continue

            for part in parts:
                if isinstance(part, dict) and "text" in part:
                    text = part["text"]
                    # Clean citation artifacts
                    text = re.sub(r'\s*\[cite:\s*[^\]]*\]', '', text)
                    if text.strip():
                        # Yield the new text chunk (delta from previous)
                        if len(text) > len(full_text):
                            chunk = text[len(full_text):]
                            full_text = text
                            yield {"type": "chunk", "content": chunk}
                        elif text != full_text:
                            # Complete replacement - yield the whole thing
                            full_text = text
                            yield {"type": "chunk", "content": text}

        yield {"type": "done", "content": full_text.strip()}

    except requests.exceptions.ConnectionError:
        print("   ADK server not reachable. Is it running on port 8080?")
        yield {"type": "error", "content": "The AI agent is currently unavailable. Please try again in a moment."}
    except requests.exceptions.Timeout:
        print("   ADK query timed out after 120s")
        yield {"type": "error", "content": "The request took too long. Please try a simpler question."}
    except Exception as e:
        print(f"   ADK stream error: {e}")
        yield {"type": "error", "content": "An error occurred while processing your question. Please try again."}
