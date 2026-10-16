import os
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import anthropic
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import models

"""
LLM layer for SpendSense's AI chat.

The rule-based processor still computes the numbers (and chart data); this module
hands Claude a snapshot of the user's finances plus the recent conversation and lets
it write the actual reply. If no API key is configured or the call fails, the caller
falls back to the rule-based response.
"""

logger = logging.getLogger(__name__)

# Haiku is the budget pick: ~$0.10 / $0.50 per million input/output tokens (<1/40th of Opus).
# The numbers are precomputed, so the model only has to phrase them well.
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-5-5")

SYSTEM_PROMPT = """You are SpendSense, a personal finance assistant inside an expense-tracking app.

You'll receive a snapshot of the user's spending data and, sometimes, the result of a calculation the app already ran for their question. Answer using only those numbers - never invent expenses, totals, or budgets. If the data can't answer the question, say what's missing and suggest what they could log or ask instead.

Style: conversational, direct, and specific. Lead with the answer, cite real figures (dollar amounts, months, categories), and add one practical observation or suggestion when it's useful. Keep replies short - a few sentences or a brief list - since they're shown in a small chat window. Plain text only; no markdown headings or tables.

If the user wants to log an expense, tell them to phrase it like "I spent $45 on groceries" so the app can add it."""

_client: Optional[anthropic.Anthropic] = None


def llm_enabled() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY"))


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(timeout=60.0)
    return _client


def build_financial_context(db: Session, user_id: int) -> str:
    """Summarize the user's spending into a compact text snapshot for the model."""
    now = datetime.now()
    base = db.query(models.Expense).filter(
        models.Expense.user_id == user_id,
        models.Expense.deleted_at.is_(None),
    )

    # Monthly totals, last 12 months (including the current, partial month)
    month_starts = []
    cursor = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    for _ in range(12):
        month_starts.append(cursor)
        cursor = (cursor - timedelta(days=1)).replace(day=1)
    month_starts.reverse()

    rows = db.query(
        func.extract('year', models.Expense.expense_date),
        func.extract('month', models.Expense.expense_date),
        func.sum(models.Expense.amount),
    ).filter(
        models.Expense.user_id == user_id,
        models.Expense.deleted_at.is_(None),
        models.Expense.expense_date >= month_starts[0],
    ).group_by(
        func.extract('year', models.Expense.expense_date),
        func.extract('month', models.Expense.expense_date),
    ).all()
    totals = {(int(y), int(m)): float(t) for y, m, t in rows}
    monthly = [
        f"{m.strftime('%b %Y')}: ${totals.get((m.year, m.month), 0.0):.2f}"
        for m in month_starts
    ]

    def by_category(start: datetime, end: datetime) -> List[str]:
        results = db.query(models.Category.name, func.sum(models.Expense.amount))\
            .join(models.Expense, models.Expense.category_id == models.Category.category_id)\
            .filter(
                models.Expense.user_id == user_id,
                models.Expense.deleted_at.is_(None),
                models.Expense.expense_date >= start,
                models.Expense.expense_date < end,
            ).group_by(models.Category.name)\
            .order_by(func.sum(models.Expense.amount).desc()).all()
        return [f"{name}: ${float(amt):.2f}" for name, amt in results]

    this_month_start = month_starts[-1]
    last_month_start = month_starts[-2]
    next_month_start = (this_month_start + timedelta(days=32)).replace(day=1)

    def fmt_expense(e: models.Expense) -> str:
        cat = e.category.name if e.category else "uncategorized"
        date = e.expense_date.strftime('%Y-%m-%d') if e.expense_date else "?"
        return f"{date} | ${e.amount:.2f} | {cat} | {e.description or ''}"

    recent = base.order_by(models.Expense.expense_date.desc()).limit(10).all()
    largest = base.filter(models.Expense.expense_date >= now - timedelta(days=90))\
        .order_by(models.Expense.amount.desc()).limit(10).all()

    budget_lines = []
    budgets = db.query(models.Budget).filter(
        models.Budget.user_id == user_id,
        models.Budget.is_active == 1,
    ).all()
    for b in budgets:
        q = db.query(func.sum(models.Expense.amount)).filter(
            models.Expense.user_id == user_id,
            models.Expense.deleted_at.is_(None),
            models.Expense.expense_date >= this_month_start,
        )
        if b.category_id:
            q = q.filter(models.Expense.category_id == b.category_id)
        spent = float(q.scalar() or 0.0)
        scope = b.category.name if b.category else "overall"
        budget_lines.append(f"{scope} ({b.period}): ${spent:.2f} spent this month of ${b.amount:.2f} limit")

    sections = [
        f"Today: {now.strftime('%A, %B %d, %Y')}",
        "Monthly totals (last 12 months, current month is partial):\n" + "\n".join(monthly),
        f"Spending by category - {this_month_start.strftime('%B %Y')}:\n" + ("\n".join(by_category(this_month_start, next_month_start)) or "none"),
        f"Spending by category - {last_month_start.strftime('%B %Y')}:\n" + ("\n".join(by_category(last_month_start, this_month_start)) or "none"),
        "Largest expenses, last 90 days (date | amount | category | description):\n" + ("\n".join(fmt_expense(e) for e in largest) or "none"),
        "Most recent expenses:\n" + ("\n".join(fmt_expense(e) for e in recent) or "none"),
        "Budgets:\n" + ("\n".join(budget_lines) or "none set"),
    ]
    return "\n\n".join(sections)


def _history_to_messages(context: Optional[List[str]]) -> List[Dict[str, str]]:
    """Convert the frontend's ["User: ...", "AI: ..."] history into API messages."""
    messages: List[Dict[str, str]] = []
    for line in context or []:
        if line.startswith("User: "):
            role, content = "user", line[len("User: "):]
        elif line.startswith("AI: "):
            role, content = "assistant", line[len("AI: "):]
        else:
            continue
        # Roles must alternate; merge back-to-back turns from the same side
        if messages and messages[-1]["role"] == role:
            messages[-1]["content"] += "\n\n" + content
        else:
            messages.append({"role": role, "content": content})
    while messages and messages[0]["role"] != "user":
        messages.pop(0)
    return messages


def generate_llm_reply(
    query: str,
    financial_context: str,
    history: Optional[List[str]] = None,
    computed: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Ask Claude to answer the user's question. Returns None if the call fails."""
    prompt = f"<spending_data>\n{financial_context}\n</spending_data>\n\n"
    if computed:
        prompt += f"<app_calculation>\n{json.dumps(computed, default=str)}\n</app_calculation>\n\n"
    prompt += f"<question>\n{query}\n</question>"

    messages = _history_to_messages(history)
    if messages and messages[-1]["role"] == "user":
        messages.pop()  # unanswered turn (e.g. this same query echoed in the history)
    messages.append({"role": "user", "content": prompt})

    try:
        response = _get_client().messages.create(
            model=MODEL,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=messages,
            output_config={"effort": "low"},
        )
    except anthropic.APIStatusError as e:
        logger.error("Claude API error %s: %s", e.status_code, e.message)
        return None
    except anthropic.APIConnectionError as e:
        logger.error("Claude API connection error: %s", e)
        return None
    except Exception:
        # Never let the LLM layer take down the endpoint; the rule-based reply still works
        logger.exception("Unexpected error calling Claude")
        return None

    if response.stop_reason == "refusal":
        logger.warning("Claude declined request %s", response._request_id)
        return None

    text = "".join(block.text for block in response.content if block.type == "text").strip()
    return text or None
