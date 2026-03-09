# -*- coding: utf-8 -*-
"""
Cache Warmer for CS Navigator
==============================
Pre-loads common questions into L1 + L2 cache on startup.
Runs in background so the server starts immediately.

Phase 1: Uses curated question pool
Phase 2 (future): Pull top questions from user query logs
"""

import asyncio
import logging
import time
from cache import query_cache
from vertex_agent import query_agent

logger = logging.getLogger(__name__)

# ============================================================================
# SEED QUESTIONS (curated common questions)
# These are the same pool used for /api/popular-questions
# ============================================================================

SEED_QUESTIONS = [
    # Course & curriculum
    "What courses should I take next semester if I'm interested in AI/ML?",
    "Can you recommend a study plan for the cybersecurity track?",
    "What are the prerequisites for COSC 450 Operating Systems?",
    "What electives count toward the CS degree?",
    "What math courses are required for the CS major?",
    "What is the recommended course sequence for freshmen CS students?",
    "Which courses cover data structures and algorithms?",
    # Department & faculty
    "Who are the professors in the CS department and what do they teach?",
    "Who is the chair of the Computer Science department?",
    "What research areas do CS faculty specialize in?",
    # Career & opportunities
    "What internship and co-op opportunities are available for CS majors?",
    "What career paths can I pursue with a CS degree from Morgan State?",
    "How can I prepare for technical interviews?",
    "What companies recruit CS students from Morgan State?",
    # Academic advising & graduation
    "How do I apply for graduation and what requirements do I need?",
    "How many credits do I need to graduate with a CS degree?",
    "What is the difference between a B.S. and B.A. in Computer Science?",
    "What is the minimum GPA required to stay in the CS program?",
    # Research & extracurricular
    "What research labs and projects can I join in the CS department?",
    "Are there any CS student organizations or clubs at Morgan State?",
    "How can I get involved in undergraduate research?",
    # Frequently asked
    "How do I contact my academic advisor?",
    "Where is the Computer Science department located?",
    "How do I register for CS courses?",
    "What programming languages are taught in the CS program?",
]


async def warm_cache():
    """
    Pre-fill cache with responses to common questions.
    Checks Redis (L2) first so we skip questions already cached.
    Runs each query sequentially to avoid overwhelming the agent.
    """
    logger.info(f"[CACHE WARMER] Starting cache warm-up with {len(SEED_QUESTIONS)} questions...")
    start_time = time.time()
    cached_count = 0
    skipped_count = 0
    failed_count = 0

    for i, question in enumerate(SEED_QUESTIONS, 1):
        # Check if already in cache (L1 or L2/Redis)
        existing = query_cache.get(question, context_hash="")
        if existing is not None:
            skipped_count += 1
            logger.info(f"[CACHE WARMER] [{i}/{len(SEED_QUESTIONS)}] Already cached: {question[:50]}...")
            continue

        try:
            # Query the agent (runs in thread pool to not block event loop)
            response = await asyncio.to_thread(
                query_agent,
                query=question,
                user_id="cache-warmer",
                context=""
            )

            if response and "error" not in response.lower()[:50]:
                query_cache.set(question, response, context_hash="")
                cached_count += 1
                logger.info(f"[CACHE WARMER] [{i}/{len(SEED_QUESTIONS)}] Cached: {question[:50]}...")
            else:
                failed_count += 1
                logger.warning(f"[CACHE WARMER] [{i}/{len(SEED_QUESTIONS)}] Bad response: {question[:50]}...")

        except Exception as e:
            failed_count += 1
            logger.warning(f"[CACHE WARMER] [{i}/{len(SEED_QUESTIONS)}] Failed: {e}")

        # Small delay between queries to not hammer the agent
        await asyncio.sleep(0.5)

    elapsed = time.time() - start_time
    logger.info(
        f"[CACHE WARMER] Done in {elapsed:.1f}s | "
        f"Cached: {cached_count} | Skipped: {skipped_count} | Failed: {failed_count}"
    )
    return {"cached": cached_count, "skipped": skipped_count, "failed": failed_count}
