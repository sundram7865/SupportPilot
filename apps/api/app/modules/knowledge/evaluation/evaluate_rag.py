"""
RAG Evaluation - Groq (LLM) + Gemini (embeddings)
RAGAS 0.1.14 - Proven working version

Fixes applied vs. previous version:
1. The 'n' parameter Groq rejects (max 1) is now stripped at the httpx
   transport layer via an event hook, so it is removed on EVERY outgoing
   request -- sync AND async -- regardless of which internal langchain/
   ragas code path issues the call. The previous monkey-patch only
   touched the sync client, so async calls (used heavily by
   answer_relevancy, which requests multiple generations) kept failing
   with 400 Bad Request.
2. NaN / Inf metric scores are sanitized to None before being returned,
   so FastAPI's default JSONResponse (which uses strict JSON, no NaN)
   does not raise `ValueError: Out of range float values are not JSON
   compliant` and blow up the request/DB session.
3. The DB session is only touched during context retrieval. Nothing in
   this module holds or queries `db` during the (potentially many
   minutes long) RAGAS evaluate() call, so a long-running evaluation
   does not keep an idle transaction open against Postgres. (If you are
   still seeing "SSL SYSCALL error: EOF detected" after this fix, check
   the request-scoped `get_db()` dependency in your router -- it likely
   holds the connection open for the whole request; consider closing/
   returning it before kicking off evaluation, or run evaluation in a
   background task and query with a fresh short-lived session only to
   persist results.)
4. "models/embedding-001" was retired by Google and replaced with
   "models/gemini-embedding-001" (see comment near its usage below).
5. Trimmed GOLDEN_QUESTIONS down to 2 (was 5) and added a proactive
   sliding-window rate limiter shared by every outgoing Groq request --
   both the ones RAGAS/langchain issue internally and the direct
   httpx.post calls in _generate_answer. Groq's free tier for
   llama-3.1-8b-instant caps out around 30 requests/minute; RAGAS's
   evaluate() alone can fire 15-25+ calls in a short burst across just
   4 metrics, so without throttling you get a wall of 429s and multi-
   minute waits from the client's reactive backoff. The rate limiter
   here waits *before* sending so you rarely hit 429 in the first
   place. Also increased the delay between per-question answer-
   generation calls (SLEEP_BETWEEN_QUESTIONS_SECS).
"""

import os
import time
import json
import math
import logging
import threading
import asyncio
import collections
from typing import Dict, List, Optional
from uuid import UUID

import httpx
import pandas as pd
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_recall,
    context_precision,
)
from ragas.run_config import RunConfig
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_openai import ChatOpenAI
from sqlalchemy.orm import Session

from app.modules.knowledge.service import search_knowledge_chunks

logger = logging.getLogger(__name__)

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
JUDGE_MODEL = "llama-3.1-8b-instant"

# How long to wait between generating answers for successive golden
# questions. Increased from 12s -> 20s to spread load further and
# leave more headroom under Groq's per-minute cap.
SLEEP_BETWEEN_QUESTIONS_SECS = 20

# Proactive rate limit for ALL outgoing Groq requests (RAGAS-internal
# and direct httpx.post calls alike). Groq's free tier for
# llama-3.1-8b-instant is ~30 requests/minute; capping ourselves to 20
# leaves headroom for retries without tripping 429s in normal operation.
RATE_LIMIT_MAX_REQUESTS = 20
RATE_LIMIT_WINDOW_SECS = 60.0

# Trimmed from 5 to 2 golden questions to reduce total Groq call volume
# during metric computation (each question fans out into several LLM
# calls per metric -- see prior discussion). Swap in different
# questions from the original 5 if these two aren't representative
# enough for your use case.
GOLDEN_QUESTIONS = [
    {
        "question": "What is the return window, which products are non-returnable, and how long do refunds take for different payment methods?",
        "ground_truth": "Return window: 7 days from delivery. Non-returnable: Personal Care Products, Grocery Items, Gift Cards, Customized Products. Refund timeline: UPI 2-3 days, Bank Account 5-7 days, Credit Card 7-10 days.",
    },
    {
        "question": "What are the shipping options, delivery times, and charges at Urban Kart?",
        "ground_truth": "Standard: 3-7 business days. Express: 1-2 business days. Free shipping on orders above ₹499. Below ₹499 costs ₹49. International shipping unavailable.",
    },
]


def _strip_n_from_body(request: httpx.Request) -> None:
    """
    Shared implementation: remove the `n` field from a JSON POST body.

    Groq's OpenAI-compatible endpoint rejects `n` values other than 1.
    RAGAS/langchain sometimes set n>1 internally (e.g. answer_relevancy
    requests multiple generations to measure semantic consistency).
    Stripping it here -- at the transport layer -- guarantees it is
    removed no matter which internal client object (sync or async)
    issues the request.
    """
    if request.method != "POST" or not request.content:
        return
    try:
        body = json.loads(request.content)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return

    if not isinstance(body, dict) or "n" not in body:
        return

    body.pop("n", None)
    new_content = json.dumps(body).encode("utf-8")
    request.headers["content-length"] = str(len(new_content))
    request.stream = httpx._content.ByteStream(new_content)  # type: ignore[attr-defined]
    request._content = new_content


class _RateLimiter:
    """
    Sliding-window rate limiter shared across sync + async call sites.

    Instead of letting Groq return 429 and relying on the client's
    reactive exponential backoff (slow, and each retry itself counts
    against the window), this waits *before* sending once the request
    count in the trailing window hits the cap. `acquire()` blocks the
    calling thread; `acquire_async()` awaits instead, for use inside
    async httpx event hooks.
    """

    def __init__(self, max_requests: int, per_seconds: float):
        self.max_requests = max_requests
        self.per_seconds = per_seconds
        self._lock = threading.Lock()
        self._timestamps: "collections.deque[float]" = collections.deque()

    def _compute_wait(self) -> float:
        with self._lock:
            now = time.monotonic()
            while self._timestamps and now - self._timestamps[0] >= self.per_seconds:
                self._timestamps.popleft()
            if len(self._timestamps) < self.max_requests:
                self._timestamps.append(now)
                return 0.0
            wait = self.per_seconds - (now - self._timestamps[0])
            wait = max(wait, 0.0)
            # Reserve our slot for when we'll actually send, so
            # concurrent callers computing wait times don't all pile
            # into the same freed-up slot.
            self._timestamps.append(now + wait)
            return wait

    def acquire(self) -> None:
        wait = self._compute_wait()
        if wait > 0:
            time.sleep(wait)

    async def acquire_async(self) -> None:
        wait = self._compute_wait()
        if wait > 0:
            await asyncio.sleep(wait)


def _sanitize_score(value: float) -> Optional[float]:
    """Convert NaN/Inf to None so the result is JSON-serializable."""
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return f


class AIRAGEvaluator:
    def __init__(self, db: Session, organization_id: UUID):
        self.db = db
        self.organization_id = organization_id

        grok_key = os.getenv("GROK_API_KEY")
        gemini_key = os.getenv("GEMINI_API_KEY")
        if not grok_key:
            raise ValueError("GROK_API_KEY not set")
        if not gemini_key:
            raise ValueError("GEMINI_API_KEY not set")

        os.environ["OPENAI_API_KEY"] = grok_key

        # Shared rate limiter: used by the httpx event hooks below AND
        # by the direct httpx.post call in _generate_answer, so every
        # Groq request -- regardless of code path -- counts against
        # the same budget.
        self._rate_limiter = _RateLimiter(
            max_requests=RATE_LIMIT_MAX_REQUESTS, per_seconds=RATE_LIMIT_WINDOW_SECS
        )

        def _sync_hook(request: httpx.Request) -> None:
            _strip_n_from_body(request)
            self._rate_limiter.acquire()

        async def _async_hook(request: httpx.Request) -> None:
            _strip_n_from_body(request)
            await self._rate_limiter.acquire_async()

        # Custom httpx clients with the n-stripping + rate-limiting
        # hooks attached, so every request the ChatOpenAI wrapper
        # issues -- sync or async -- goes through both before hitting
        # Groq.
        sync_http_client = httpx.Client(event_hooks={"request": [_sync_hook]})
        async_http_client = httpx.AsyncClient(event_hooks={"request": [_async_hook]})

        self.llm = ChatOpenAI(
            model=JUDGE_MODEL,
            api_key=grok_key,
            base_url=GROQ_BASE_URL,
            temperature=0.1,
            max_retries=2,
            request_timeout=60,
            http_client=sync_http_client,
            http_async_client=async_http_client,
        )
        # NOTE: "models/embedding-001" (and "text-embedding-004") were
        # retired by Google and now 404 with:
        #   "models/embedding-001 is not found for API version v1beta,
        #    or is not supported for embedContent"
        # "gemini-embedding-001" is the current GA replacement. It
        # returns 3072-dim vectors by default; since these embeddings
        # are only used internally by RAGAS for cosine-similarity
        # metrics (never stored in your pgvector schema), the larger
        # dimensionality is harmless here -- no need to pass
        # output_dimensionality unless you want to cut latency/cost.
        self.embeddings = LangchainEmbeddingsWrapper(
            GoogleGenerativeAIEmbeddings(
                model="models/gemini-embedding-001", google_api_key=gemini_key
            )
        )

    def _generate_answer(self, question: str, contexts: List[str]) -> str:
        if not contexts:
            return "No relevant information found."

        ctx_text = "\n\n".join(contexts[:3])[:3000]
        try:
            # This call bypasses the ChatOpenAI client's http_client,
            # so it doesn't automatically go through the httpx event
            # hooks above. Acquire the same rate-limit budget manually
            # to keep it counted against the shared window.
            self._rate_limiter.acquire()
            r = httpx.post(
                f"{GROQ_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {os.getenv('GROK_API_KEY')}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": JUDGE_MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": "Answer using ONLY the provided context. Be concise.",
                        },
                        {
                            "role": "user",
                            "content": f"Context:\n{ctx_text}\n\nQuestion: {question}",
                        },
                    ],
                    "temperature": 0.1,
                    "max_tokens": 300,
                },
                timeout=60,
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Answer generation failed for question %r: %s", question, exc)
            return "Error generating answer."

    def _retrieve_contexts(self, query: str, limit: int = 5):
        results = search_knowledge_chunks(
            db=self.db,
            organization_id=self.organization_id,
            query=query,
            limit=limit,
        )
        return [c.content for c, _, _ in results], [s for _, _, s in results]

    def _build_eval_records(self, questions: List[Dict]) -> List[Dict]:
        """
        Retrieval + answer generation phase. This is the ONLY phase that
        touches self.db. Once this returns, evaluate() (which can take
        several minutes under Groq rate limits) never touches the DB.
        """
        records = []
        for i, item in enumerate(questions):
            q = item["question"]
            print(f"   Q{i + 1}/{len(questions)}: {q[:60]}...")
            ctx, _ = self._retrieve_contexts(q)
            ans = self._generate_answer(q, ctx)
            records.append(
                {
                    "question": q,
                    "answer": ans,
                    "contexts": [c[:400] for c in ctx[:3]],
                    "ground_truth": item["ground_truth"],
                }
            )
            if i < len(questions) - 1:
                time.sleep(SLEEP_BETWEEN_QUESTIONS_SECS)
        return records

    def evaluate_with_golden_questions(self, questions: Optional[List[Dict]] = None) -> Dict:
        if questions is None:
            questions = GOLDEN_QUESTIONS

        print(
            "\n"
            + "=" * 60
            + f"\n🤖 RAG EVALUATION - {len(questions)} Golden Questions\n"
            + "=" * 60
        )

        records = self._build_eval_records(questions)

        print("\n📊 Computing RAGAS metrics...")
        try:
            ds = Dataset.from_pandas(pd.DataFrame(records))
            results = evaluate(
                dataset=ds,
                metrics=[context_precision, context_recall, faithfulness, answer_relevancy],
                llm=self.llm,
                embeddings=self.embeddings,
                run_config=RunConfig(max_workers=1, timeout=600),
            )
        except Exception as e:  # noqa: BLE001
            logger.exception("RAGAS evaluation failed")
            return {"error": str(e)}

        print("\n" + "=" * 60 + "\n📊 RESULTS\n" + "=" * 60)
        scores: Dict[str, Optional[float]] = {}
        for k in results.keys():
            if k in ("question", "answer", "contexts", "ground_truth"):
                continue
            raw = results[k]
            s = _sanitize_score(raw)
            scores[k] = s
            if s is None:
                print(f"  {k:25s}: N/A ❌ (NaN/Inf -- likely rate-limited or malformed responses)")
            else:
                icon = "✅" if s >= 0.8 else "👍" if s >= 0.6 else "⚠️" if s >= 0.4 else "❌"
                print(f"  {k:25s}: {s:.4f} {icon}")

        return {"scores": scores}


async def run_golden_evaluation(db, org_id):
    return AIRAGEvaluator(db, org_id).evaluate_with_golden_questions()


async def quick_retrieval_test(db, org_id, query):
    e = AIRAGEvaluator(db, org_id)
    ctx, _ = e._retrieve_contexts(query)
    return {"query": query, "ai_answer": e._generate_answer(query, ctx)}