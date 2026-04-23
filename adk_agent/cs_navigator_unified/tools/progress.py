"""Student progress tracking tools via Firestore.

Used by Quiz Master to record scores and by the Tutor orchestrator
to check student weaknesses. Reads/writes directly to Firestore.
"""

import logging
from collections import defaultdict
from datetime import datetime, timezone

from google.cloud import firestore

logger = logging.getLogger(__name__)

_MAX_ID_LEN = 128

_db = None


def _get_db():
    global _db
    if _db is None:
        _db = firestore.Client()
    return _db


def _validate_user_id(user_id) -> str:
    """Ensure user_id is a non-empty, reasonably sized string."""
    if not isinstance(user_id, str):
        raise ValueError("user_id must be a string")
    uid = user_id.strip()
    if not uid:
        raise ValueError("user_id must not be empty")
    if len(uid) > _MAX_ID_LEN:
        raise ValueError("user_id is too long")
    return uid


def _get_profile(user_id: str) -> dict:
    """Load student profile from Firestore. Returns defaults if not found."""
    db = _get_db()
    doc = db.collection("students").document(user_id).get()
    if not doc.exists:
        return {
            "canvas_user_id": user_id,
            "enrolled_courses": [],
            "quiz_history": [],
            "weak_topics": [],
            "strong_topics": [],
            "sessions": [],
            "last_active": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    return doc.to_dict()


def _analyze_mastery(user_id: str) -> dict:
    """Analyze quiz history and compute topic mastery levels."""
    profile = _get_profile(user_id)
    quiz_history = profile.get("quiz_history", [])

    if not quiz_history:
        return {"weak_topics": [], "strong_topics": [], "topic_stats": {}, "total_quizzes": 0}

    topic_scores = defaultdict(list)
    topic_missed = defaultdict(list)
    for q in quiz_history:
        topic = q.get("topic", "unknown")
        total = q.get("total", 1)
        score = q.get("score", 0)
        pct = round((score / total) * 100) if total > 0 else 0
        topic_scores[topic].append(pct)
        topic_missed[topic].extend(q.get("missed_concepts", []))

    weak, strong = [], []
    topic_stats = {}
    for topic, scores in topic_scores.items():
        avg = sum(scores) / len(scores)
        recent = scores[-1]
        prev = scores[-2] if len(scores) >= 2 else recent
        if recent > prev:
            trend = "improving"
        elif recent < prev:
            trend = "declining"
        else:
            trend = "stable"

        missed_counts = defaultdict(int)
        for c in topic_missed[topic]:
            missed_counts[c] += 1
        top_missed = sorted(missed_counts, key=missed_counts.get, reverse=True)[:5]

        topic_stats[topic] = {
            "average_score": round(avg, 1),
            "recent_score": recent,
            "attempts": len(scores),
            "trend": trend,
            "commonly_missed": top_missed,
        }

        if avg < 70:
            weak.append(topic)
        elif avg >= 85:
            strong.append(topic)

    db = _get_db()
    db.collection("students").document(user_id).set(
        {"weak_topics": weak, "strong_topics": strong, "last_active": datetime.now(timezone.utc).isoformat()},
        merge=True,
    )

    return {
        "weak_topics": weak,
        "strong_topics": strong,
        "topic_stats": topic_stats,
        "total_quizzes": len(quiz_history),
    }


def get_student_profile(canvas_user_id: str) -> dict:
    """Load the student's profile including courses, quiz history, and weak topics.

    Args:
        canvas_user_id: The student's user ID.
    """
    try:
        canvas_user_id = _validate_user_id(canvas_user_id)
    except ValueError as e:
        return {"status": "error", "message": str(e)}
    try:
        profile = _get_profile(canvas_user_id)
        mastery = _analyze_mastery(canvas_user_id)
        profile["mastery"] = mastery
        return profile
    except Exception as e:
        logger.exception("Failed to load student profile for user=%s", canvas_user_id)
        return {"status": "error", "message": f"Failed to load profile: {type(e).__name__}"}


def update_quiz_score(
    canvas_user_id: str,
    topic: str,
    score: int,
    total: int,
    missed_concepts: list[str],
) -> dict:
    """Record a quiz result and update mastery analysis.

    Args:
        canvas_user_id: The student's user ID.
        topic: The quiz topic (e.g., 'sorting algorithms').
        score: Number of correct answers.
        total: Total number of questions.
        missed_concepts: List of concepts the student got wrong.
    """
    try:
        canvas_user_id = _validate_user_id(canvas_user_id)
    except ValueError as e:
        return {"status": "error", "message": str(e)}
    try:
        db = _get_db()
        result = {
            "topic": topic,
            "score": score,
            "total": total,
            "missed_concepts": missed_concepts,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        db.collection("students").document(canvas_user_id).set(
            {"quiz_history": firestore.ArrayUnion([result])},
            merge=True,
        )

        mastery = _analyze_mastery(canvas_user_id)
        pct = round((score / total) * 100) if total > 0 else 0
        return {
            "status": "recorded",
            "score_pct": pct,
            "updated_weak_topics": mastery["weak_topics"],
            "updated_strong_topics": mastery["strong_topics"],
            "message": f"Scored {score}/{total} ({pct}%) on {topic}.",
        }
    except Exception as e:
        logger.exception("Failed to update quiz score for user=%s", canvas_user_id)
        return {"status": "error", "message": f"Failed to record quiz: {type(e).__name__}"}


def get_weaknesses(canvas_user_id: str) -> dict:
    """Get the student's weak topics from quiz history.

    Args:
        canvas_user_id: The student's user ID.
    """
    try:
        canvas_user_id = _validate_user_id(canvas_user_id)
    except ValueError as e:
        return {"status": "error", "message": str(e)}
    try:
        mastery = _analyze_mastery(canvas_user_id)
    except Exception as e:
        logger.exception("Failed to analyze mastery for user=%s", canvas_user_id)
        return {"status": "error", "message": f"Failed to load weaknesses: {type(e).__name__}"}
    weak_details = []
    for topic in mastery["weak_topics"]:
        stats = mastery["topic_stats"].get(topic, {})
        weak_details.append({
            "topic": topic,
            "average_score": stats.get("average_score", 0),
            "commonly_missed": stats.get("commonly_missed", []),
            "trend": stats.get("trend", "unknown"),
        })
    return {
        "status": "ok",
        "weak_topics": weak_details,
        "count": len(weak_details),
    }


def log_session(canvas_user_id: str, topics_covered: list[str]) -> dict:
    """Log a tutoring session with topics discussed.

    Args:
        canvas_user_id: The student's user ID.
        topics_covered: List of topics covered in this session.
    """
    try:
        canvas_user_id = _validate_user_id(canvas_user_id)
    except ValueError as e:
        return {"status": "error", "message": str(e)}
    try:
        db = _get_db()
        session = {
            "topics_covered": topics_covered,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        db.collection("students").document(canvas_user_id).set(
            {"sessions": firestore.ArrayUnion([session])},
            merge=True,
        )
        return {"status": "logged", "topics": topics_covered}
    except Exception as e:
        logger.exception("Failed to log session for user=%s", canvas_user_id)
        return {"status": "error", "message": f"Failed to log session: {type(e).__name__}"}
