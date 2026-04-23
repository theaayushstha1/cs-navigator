"""Fetch tutor progress data from Firestore for context injection."""

import logging
import re
from collections import defaultdict

from google.cloud import firestore

logger = logging.getLogger(__name__)

_db = None

_EMPTY_RESULT = {
    "weak_topics": [],
    "strong_topics": [],
    "recent_quiz_scores": [],
    "session_count": 0,
}

# Firestore document IDs cannot contain "/" and must not be "." or "..".
# Restrict to a safe character set to prevent path traversal or injection.
_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_\-]{1,1500}$")


def _get_db():
    global _db
    if _db is None:
        _db = firestore.Client()
    return _db


def fetch_tutor_progress(user_id: str) -> dict:
    """Read student's tutor progress from Firestore.

    Returns dict with weak_topics, strong_topics, recent_quiz_scores,
    and session_count. Returns empty defaults if no data exists.
    """
    safe_id = str(user_id) if user_id is not None else ""
    if not _SAFE_ID_RE.match(safe_id):
        logger.warning("fetch_tutor_progress: rejected unsafe user_id")
        return dict(_EMPTY_RESULT)

    try:
        db = _get_db()
        doc_ref = db.collection("students").document(safe_id)
        doc = doc_ref.get()
    except Exception:
        logger.exception("fetch_tutor_progress: Firestore read failed")
        return dict(_EMPTY_RESULT)

    if not doc.exists:
        return dict(_EMPTY_RESULT)

    data = doc.to_dict() or {}
    quiz_history = data.get("quiz_history", [])

    topic_scores = defaultdict(list)
    for q in quiz_history:
        topic = q.get("topic", "unknown")
        total = q.get("total", 1)
        score = q.get("score", 0)
        pct = round((score / total) * 100) if total > 0 else 0
        topic_scores[topic].append(pct)

    weak = []
    strong = []
    for topic, scores in topic_scores.items():
        avg = sum(scores) / len(scores)
        if avg < 70:
            weak.append(topic)
        elif avg >= 85:
            strong.append(topic)

    recent = quiz_history[-5:] if quiz_history else []
    recent_formatted = [
        {"topic": q.get("topic"), "score": q.get("score"), "total": q.get("total")}
        for q in recent
    ]

    return {
        "weak_topics": weak,
        "strong_topics": strong,
        "recent_quiz_scores": recent_formatted,
        "session_count": len(data.get("sessions", [])),
    }
