"""
Vertex AI Agent Engine Client
==============================

Communicates with the CS Navigator agent running on Google ADK web server.
Handles session management and SSE response parsing.

Usage:
    Local dev:  ADK web server at http://127.0.0.1:8080
    Production: Vertex AI Agent Engine (deployed reasoning engine)
"""

import os
import json
import requests
import uuid
from typing import Optional

# Configuration
ADK_BASE_URL = os.getenv("ADK_BASE_URL", "http://127.0.0.1:8080")
ADK_APP_NAME = os.getenv("ADK_APP_NAME", "cs_navigator_unified")

# In-memory session cache: maps chatbot user_id -> ADK session_id
_session_cache: dict[str, str] = {}


def _create_session(user_id: str) -> str:
    """Create a new ADK session for the user."""
    try:
        resp = requests.post(
            f"{ADK_BASE_URL}/apps/{ADK_APP_NAME}/users/{user_id}/sessions",
            headers={"Content-Type": "application/json"},
            json={},
            timeout=10,
        )
        resp.raise_for_status()
        session_id = resp.json().get("id")
        if session_id:
            _session_cache[user_id] = session_id
            print(f"   ADK session created: {session_id} for user {user_id}")
            return session_id
    except Exception as e:
        print(f"   Failed to create ADK session: {e}")
    return ""


def _get_or_create_session(user_id: str) -> str:
    """Get an existing ADK session or create a new one for the user."""
    if user_id in _session_cache:
        return _session_cache[user_id]
    return _create_session(user_id)


def query_agent(query: str, user_id: str = "default", context: str = "") -> str:
    """
    Send a query to the CS Navigator agent and return the final text response.

    Args:
        query: The user's question
        user_id: Unique user identifier (for session management)
        context: Optional context to prepend (e.g., DegreeWorks data, conversation history)

    Returns:
        The agent's text response, or an error message
    """
    session_id = _get_or_create_session(user_id)
    if not session_id:
        return "The AI agent is currently unavailable. Please try again in a moment."

    # Build the message: prepend context if provided
    message = query
    if context:
        message = f"{context}\n\nQuestion: {query}"

    return _run_query(message, user_id, session_id)


def _run_query(message: str, user_id: str, session_id: str, retried: bool = False) -> str:
    """Send a query to the ADK and parse the SSE response."""
    try:
        resp = requests.post(
            f"{ADK_BASE_URL}/run_sse",
            headers={"Content-Type": "application/json"},
            json={
                "app_name": ADK_APP_NAME,
                "user_id": user_id,
                "session_id": session_id,
                "new_message": {
                    "role": "user",
                    "parts": [{"text": message}],
                },
            },
            stream=True,
            timeout=120,
        )

        # Handle "Session not found" - create a fresh session and retry once
        if resp.status_code == 404 and not retried:
            print(f"   ADK session {session_id} not found, creating a new one...")
            _session_cache.pop(user_id, None)
            new_session_id = _create_session(user_id)
            if new_session_id:
                return _run_query(message, user_id, new_session_id, retried=True)
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
        resp = requests.get(f"{ADK_BASE_URL}/list-apps", timeout=5)
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
