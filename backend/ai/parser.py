import re
from datetime import datetime
from typing import Optional

from .schemas import ParsedIntent, IntentType, TimeRange, QueryType

"""
This file handles turning a user's natural language query into something
the backend can actually work with.

It does NOT:
- Talk to the database
- Build responses
- Handle auth or permissions

All it does is figure out what the user is asking for and pull out
useful pieces like intent, time, and category.
"""

def parse_intent(query: str) -> ParsedIntent:
    normalized_query = _normalize_query(query)

    intent = _detect_intent(normalized_query)
    time_range = _extract_time(normalized_query)
    category = _extract_category(normalized_query)

    return ParsedIntent(
        intent=intent,
        time=time_range,
        category=category,
        raw_query=query,
        query_type=_determine_query_type(normalized_query)
    )

def _normalize_query(query: str) -> str:
    query = query.lower().strip()
    query = re.sub(r'[^\w\s]', '', query)  # Remove punctuation
    return query

def _detect_intent(query: str) -> IntentType:
    "Determine the user's intent based on keywords in the query."

    if "total" in query or "spend" in query:
        return IntentType.monthly_total
    elif "breakdown" in query or "category" in query:
        return IntentType.category_breakdown
    elif "trend" in query or "pattern" in query:
        return IntentType.spending_trend
    elif "highest" in query and "category" in query:
        return IntentType.highest_spend_category
    elif "compare" in query and "months" in query:
        return IntentType.compare_months
    elif "top merchants" in query or "frequent merchants" in query:
        return IntentType.top_merchants
    elif "forecast" in query or "predict" in query:
        return IntentType.forecast
    else:
        return IntentType.monthly_total  # Default intent

def _extract_time(query: str) -> Optional[TimeRange]:
    "Extract time-related information from the query."

    month_match = re.search(r'january|february|march|april|may|june|july|august|september|october|november|december', query)
    year_match = re.search(r'\b(20\d{2})\b', query)

    time_range = TimeRange()

    if month_match:
        month_str = month_match.group(0)
        month_num = datetime.strptime(month_str, '%B').month
        time_range.month = month_num

    if year_match:
        time_range.year = int(year_match.group(1))

    return time_range if (time_range.month or time_range.year) else None
def _extract_category(query: str) -> Optional[str]:
    "Extract category information from the query."

    categories = ['food', 'entertainment', 'utilities', 'transportation', 'health', 'shopping']
    for category in categories:
        if category in query:
            return category
    return None

def _infer_query_type(query: str) -> QueryType:
    "Determine if the query is specific or general."

    specific_keywords = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december', '20']
    if any(keyword in query for keyword in specific_keywords):
        return QueryType.specific
    return QueryType.general