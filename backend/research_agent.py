"""
Auto-Research Agent for CS Navigator
======================================
Tracks failed queries, clusters similar ones, researches answers
using Gemini + Google Search grounding, and creates KB suggestions
for admin review.

Flow: Failed Query Detection -> Clustering -> Research -> KB Suggestion
"""

import re
import json
import logging
import numpy as np
from datetime import datetime, timezone
from db import SessionLocal
from models import FailedQuery, KBSuggestion
from sqlalchemy import func

log = logging.getLogger(__name__)

# Patterns that indicate the bot couldn't answer (KB miss)
FAILED_RESPONSE_PATTERNS = re.compile(
    r"based on the information I have access to|"
    r"contact the CS department at|"
    r"I (?:don't|do not) have (?:specific |enough )?information|"
    r"I (?:couldn't|could not) find|"
    r"not (?:available|found) in (?:my|the) knowledge base|"
    r"I (?:don't|do not) have access to|"
    r"I am unable to (?:determine|find|provide)|"
    r"For more details, contact",
    re.IGNORECASE
)

# Skip these short/greeting queries
SKIP_PATTERNS = re.compile(
    r"^(hi|hello|hey|thanks|thank you|ok|okay|bye|good|sup|yo|what's up)[\s!?.]*$",
    re.IGNORECASE
)


# =============================================================================
# PHASE 1: Failed Query Detection
# =============================================================================

def detect_and_log_failed_query(user_query: str, bot_response: str, user_id: int = None) -> bool:
    """Check if the bot's response indicates a KB miss and log it.
    Returns True if logged as a failed query."""
    # Skip short or greeting queries
    if len(user_query.strip()) < 15 or SKIP_PATTERNS.match(user_query.strip()):
        return False

    # Check if response indicates a KB miss
    if not FAILED_RESPONSE_PATTERNS.search(bot_response):
        return False

    try:
        with SessionLocal() as db:
            entry = FailedQuery(
                user_query=user_query.strip(),
                bot_response=bot_response[:1000],  # Truncate long responses
                user_id=user_id,
                status="new",
            )
            db.add(entry)
            db.commit()
            log.info(f"[RESEARCH] Logged failed query: {user_query[:60]}...")
        return True
    except Exception as e:
        log.warning(f"[RESEARCH] Failed to log query: {e}")
        return False


# =============================================================================
# PHASE 2: Query Clustering
# =============================================================================

CLUSTER_SIMILARITY_THRESHOLD = 0.82

_genai_client = None

def _embed_text(text: str) -> np.ndarray | None:
    """Generate embedding using text-embedding-004 (same approach as semantic cache)."""
    global _genai_client
    try:
        if _genai_client is None:
            from google import genai
            _genai_client = genai.Client(vertexai=True)

        result = _genai_client.models.embed_content(
            model="text-embedding-004",
            contents=text,
            config={"output_dimensionality": 256},
        )
        return np.array(result.embeddings[0].values, dtype=np.float32)
    except Exception as e:
        log.warning(f"[RESEARCH] Embedding failed: {e}")
        return None


def cluster_failed_queries() -> int:
    """Group unclustered failed queries by semantic similarity.
    Returns number of queries assigned to clusters."""
    with SessionLocal() as db:
        unclustered = db.query(FailedQuery).filter(
            FailedQuery.status == "new",
            FailedQuery.cluster_id == None
        ).order_by(FailedQuery.created_at.desc()).limit(200).all()

        if not unclustered:
            return 0

        # Embed all unclustered queries
        embeddings = []
        for q in unclustered:
            emb = _embed_text(q.user_query)
            embeddings.append((q, emb))

        # Get next cluster ID
        max_id = db.query(func.coalesce(func.max(FailedQuery.cluster_id), 0)).scalar()
        next_cluster_id = max_id + 1
        assigned = set()

        # Greedy cosine similarity clustering
        for i, (qi, emb_i) in enumerate(embeddings):
            if i in assigned or emb_i is None:
                continue

            cluster_members = [i]
            for j, (qj, emb_j) in enumerate(embeddings):
                if j <= i or j in assigned or emb_j is None:
                    continue
                sim = float(np.dot(emb_i, emb_j) / (np.linalg.norm(emb_i) * np.linalg.norm(emb_j)))
                if sim >= CLUSTER_SIMILARITY_THRESHOLD:
                    cluster_members.append(j)

            for idx in cluster_members:
                embeddings[idx][0].cluster_id = next_cluster_id
                embeddings[idx][0].status = "clustered"
                assigned.add(idx)
            next_cluster_id += 1

        db.commit()
        log.info(f"[RESEARCH] Clustered {len(assigned)} queries into {next_cluster_id - max_id - 1} groups")
        return len(assigned)


# =============================================================================
# PHASE 3: Research Engine (Gemini + Google Search Grounding)
# =============================================================================

def research_topic(representative_query: str, all_queries: list[str]) -> dict:
    """Use Gemini with Google Search to research a failed query topic.
    Focuses on Morgan State CS department official pages."""
    from google import genai
    from google.genai import types

    queries_text = "\n".join(f"- {q}" for q in all_queries[:5])

    prompt = f"""You are a research assistant for Morgan State University's Computer Science department.

Students asked these questions that our chatbot couldn't answer:
{queries_text}

The core question is: {representative_query}

RESEARCH TASK:
1. Search for the answer on Morgan State University's official website (morgan.edu), especially the Computer Science department pages.
2. Focus on: morgan.edu/computer-science, morgan.edu/scmns, and related university pages.
3. Find specific, factual information: names, dates, locations, phone numbers, URLs, policies, hours.
4. Cross-reference multiple pages if possible to ensure accuracy.
5. If you find conflicting information, note it.

OUTPUT FORMAT (return ONLY valid JSON, no markdown fences):
{{
  "topic": "short topic label (e.g., CS Tutoring Lab Hours)",
  "answer": "the factual answer you found (2-4 paragraphs with specific details)",
  "sources": ["url1", "url2"],
  "confidence": "high or medium or low",
  "suggested_doc_id": "existing KB doc to append to, or new doc name like academic_tutoring_hours",
  "suggested_content": "content formatted for the knowledge base in plain natural language text"
}}"""

    try:
        client = genai.Client(vertexai=True, project="csnavigator-vertex-ai", location="us-central1")

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        )

        text = response.text.strip()

        # Parse JSON from response
        try:
            # Try direct parse
            result = json.loads(text)
        except json.JSONDecodeError:
            # Extract JSON from markdown or mixed text
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = {
                    "topic": representative_query[:100],
                    "answer": text,
                    "sources": [],
                    "confidence": "low",
                    "suggested_doc_id": "",
                    "suggested_content": text,
                }

        return result

    except Exception as e:
        log.error(f"[RESEARCH] Research failed for '{representative_query[:50]}': {e}")
        return {
            "topic": representative_query[:100],
            "answer": f"Research failed: {str(e)[:200]}",
            "sources": [],
            "confidence": "low",
            "suggested_doc_id": "",
            "suggested_content": "",
        }


# =============================================================================
# PHASE 4: Batch Orchestrator
# =============================================================================

def run_research_batch(max_clusters: int = 20) -> dict:
    """Run a full research cycle: cluster -> research -> create suggestions.
    Called by Cloud Scheduler (daily) or manual admin trigger."""

    # Step 1: Cluster new failed queries
    clustered_count = cluster_failed_queries()

    # Step 2: Research unresearched clusters
    researched = []
    with SessionLocal() as db:
        clusters = db.query(
            FailedQuery.cluster_id,
            func.count(FailedQuery.id).label("count"),
        ).filter(
            FailedQuery.status == "clustered"
        ).group_by(FailedQuery.cluster_id).order_by(
            func.count(FailedQuery.id).desc()
        ).limit(max_clusters).all()

        for cluster_id, count in clusters:
            # Get all queries in this cluster
            queries = db.query(FailedQuery).filter(
                FailedQuery.cluster_id == cluster_id
            ).all()
            query_texts = [q.user_query for q in queries]
            representative = query_texts[0]

            # Check if we already have a suggestion for this cluster
            existing = db.query(KBSuggestion).filter(
                KBSuggestion.cluster_id == cluster_id
            ).first()
            if existing:
                continue

            # Research
            log.info(f"[RESEARCH] Researching cluster {cluster_id}: '{representative[:50]}...' ({count} queries)")
            research = research_topic(representative, query_texts)

            # Create suggestion
            suggestion = KBSuggestion(
                cluster_id=cluster_id,
                topic=research.get("topic", representative[:100]),
                representative_query=representative,
                query_count=count,
                researched_answer=research.get("answer", ""),
                sources=json.dumps(research.get("sources", [])),
                confidence=research.get("confidence", "low"),
                suggested_doc_id=research.get("suggested_doc_id", ""),
                suggested_content=research.get("suggested_content", ""),
                status="pending",
            )
            db.add(suggestion)

            # Mark queries as researched
            for q in queries:
                q.status = "researched"

            researched.append({
                "cluster_id": cluster_id,
                "topic": suggestion.topic,
                "count": count,
                "confidence": suggestion.confidence,
            })

        db.commit()

    log.info(f"[RESEARCH] Batch complete: {clustered_count} clustered, {len(researched)} researched")
    return {
        "clustered": clustered_count,
        "researched": len(researched),
        "topics": researched,
    }


# =============================================================================
# STATS
# =============================================================================

def get_research_stats() -> dict:
    """Get stats for the admin research dashboard."""
    with SessionLocal() as db:
        return {
            "total_failed": db.query(FailedQuery).count(),
            "new_queries": db.query(FailedQuery).filter(FailedQuery.status == "new").count(),
            "clustered": db.query(FailedQuery).filter(FailedQuery.status == "clustered").count(),
            "researched": db.query(FailedQuery).filter(FailedQuery.status == "researched").count(),
            "pending_suggestions": db.query(KBSuggestion).filter(KBSuggestion.status == "pending").count(),
            "approved": db.query(KBSuggestion).filter(KBSuggestion.status == "approved").count(),
            "pushed": db.query(KBSuggestion).filter(KBSuggestion.status == "pushed").count(),
            "rejected": db.query(KBSuggestion).filter(KBSuggestion.status == "rejected").count(),
        }
