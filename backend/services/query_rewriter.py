"""
Query Rewriter for Follow-up Resolution
=========================================
Detects follow-up questions (pronouns, short vague queries) and rewrites
them to be self-contained using recent conversation history.

Fixes the core issue: VertexAiSearchTool grounds on the raw user query,
so "tell me more about him" returns random results. Rewriting to
"tell me more about Aayush Shrestha" lets the KB search work correctly.

Uses Gemini 2.0 Flash with a cached client and minimal prompt for
fast (~300-400ms) rewrites. Falls back to original query on failure.
"""

import os
import re

# Follow-up detection patterns
_PRONOUN_RE = re.compile(
    r'\b(he|him|his|she|her|hers|they|them|their|theirs|it|its)\b',
    re.IGNORECASE,
)
_REFERENCE_RE = re.compile(
    r'\b(that|this|those|these|the same|above|previous|last one|same one)\b',
    re.IGNORECASE,
)
_CONTINUATION_RE = re.compile(
    r'^(what about|how about|and |but |so |also|tell me more|more info|more detail|elaborate|explain more|go on|continue)',
    re.IGNORECASE,
)
_SHORT_FOLLOWUP_RE = re.compile(
    r'^(yes|yeah|yep|no|nah|which one|what else|anything else)[!?.\s]*$',
    re.IGNORECASE,
)

# Cached Gemini client (initialized once, reused across requests)
_gemini_client = None
_gemini_init_attempted = False


def _get_client():
    """Get or create the cached Gemini client. Returns None if unavailable."""
    global _gemini_client, _gemini_init_attempted
    if _gemini_client is not None:
        return _gemini_client
    if _gemini_init_attempted:
        return None
    _gemini_init_attempted = True

    try:
        from google import genai
        project = os.getenv("GOOGLE_CLOUD_PROJECT", "csnavigator-vertex-ai")
        try:
            _gemini_client = genai.Client(vertexai=True, project=project, location="us-central1")
            print("   [REWRITE] Gemini client initialized (Vertex AI)")
        except Exception:
            api_key = os.getenv("GEMINI_API_KEY", "")
            if api_key:
                _gemini_client = genai.Client(api_key=api_key)
                print("   [REWRITE] Gemini client initialized (API key)")
            else:
                print("   [REWRITE] No Gemini client available")
    except Exception as e:
        print(f"   [REWRITE] Client init failed: {e}")

    return _gemini_client


def is_likely_followup(query: str) -> bool:
    """Detect if a query likely needs conversation context to be understood."""
    q = query.strip()
    if not q:
        return False

    # Very short queries (2 words or fewer) with no specific entity are likely follow-ups
    # Skip if query contains a course code (e.g., COSC 350) or looks self-contained
    words = q.split()
    if len(words) <= 2 and not re.search(r'\b[A-Z]{2,4}\s*\d{3}\b', q):
        return True

    if _PRONOUN_RE.search(q):
        return True
    if _REFERENCE_RE.search(q):
        return True
    if _CONTINUATION_RE.match(q):
        return True
    if _SHORT_FOLLOWUP_RE.match(q):
        return True

    return False


def rewrite_query(query: str, history: list[dict]) -> str:
    """Rewrite a follow-up query to be self-contained.

    Args:
        query: The user's current message
        history: Recent conversation turns [{user_query, bot_response}, ...]

    Returns:
        Rewritten query (or original if not a follow-up / rewrite fails)
    """
    if not history or not is_likely_followup(query):
        return query

    client = _get_client()
    if not client:
        return query

    # Use last 1-2 turns, heavily truncated (just enough for entity names)
    recent = history[-2:]
    ctx = ""
    for h in recent:
        ctx += f"Q: {h['user_query']}\nA: {h['bot_response'][:150]}\n"

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=f"Rewrite replacing pronouns with names from context. Return ONLY the question.\nContext:\n{ctx}\nRewrite: {query}",
            config={"temperature": 0.0, "max_output_tokens": 80},
        )
        rewritten = response.text.strip().strip('"').strip("'")

        if rewritten and 5 < len(rewritten) < 300:
            print(f"   [REWRITE] '{query}' -> '{rewritten}'")
            return rewritten

    except Exception as e:
        print(f"   [REWRITE] Failed ({type(e).__name__}: {e})")

    return query
