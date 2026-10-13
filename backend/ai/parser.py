import re
from datetime import datetime, timedelta
from typing import Optional
from .intents import identify_intent, identify_query_type
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

CATEGORIES = ['food', 'entertainment', 'utilities', 'transportation', 'health', 'shopping']

def parse_intent(query: str) -> ParsedIntent:
    """
    Parse the user's query and return a structured ParsedIntent object.
    """
    normalized_query = _normalize_query(query)
    intent = _detect_intent(normalized_query)
    time_range = _extract_time(normalized_query)
    category = _extract_category(normalized_query)
    filters = _extract_filters(normalized_query)

    return ParsedIntent(
        intent=intent,
        time=time_range,
        category=category,
        filters=filters,
        raw_query=query,
        query_type=identify_query_type(normalized_query)  # Uses intents.py mapping
    )

# Internal helper
def _normalize_query(query: str) -> str:
    "Normalize the query by lowercasing and removing punctuation."
    query = query.lower().strip()
    query = re.sub(r'[^\w\s]', '', query)  # Remove punctuation
    return query

def _detect_intent(query: str) -> IntentType:
    "Determine the user's intent based on keywords in the query. Order matters: most specific first."

    def has(*words):
        return any(re.search(rf'\b{w}\b', query) for w in words)

    if re.search(r'\b(i spent|i paid|i bought|add (an )?expense|log (an )?expense|log a)\b', query):
        return IntentType.create_expense
    if has('forecast', 'predict', 'projection', 'next month', 'will i spend'):
        return IntentType.forecast
    if has('trend', 'trends', 'pattern', 'patterns', 'over time', 'month by month', 'monthly spending', 'history', 'each month', 'per month', 'by month', r'\d+ months', 'past months'):
        return IntentType.spending_trend
    if has('compare', 'comparison', 'vs', 'versus'):
        return IntentType.compare_months
    if has('anomaly', 'anomalies', 'unusual', 'weird', 'strange', 'outlier', 'outliers', 'suspicious'):
        return IntentType.detect_anomalies
    if has('over budget', 'budget status', 'budget check', 'check my budget', 'budget progress', 'on track'):
        return IntentType.budget_check
    if has('suggest budget', 'recommend budget', 'budget recommendation', 'what should my budget', 'how much should i budget', 'set a budget'):
        return IntentType.suggest_budget
    if has('budget', 'budgets', 'save', 'saving', 'savings', 'cut back', 'reduce'):
        return IntentType.budget_suggestions
    if has('advice', 'insight', 'insights', 'tip', 'tips', 'recommend', 'recommendations', 'help me'):
        return IntentType.advice
    if has('biggest', 'largest', 'highest', 'most expensive', 'top expense') and not has('category', 'categories'):
        return IntentType.highest_expense
    if has('category', 'categories') and has('most', 'highest', 'top', 'biggest'):
        return IntentType.highest_spend_category
    if has('breakdown', 'category', 'categories', 'where', 'divided', 'split'):
        return IntentType.category_breakdown
    return IntentType.monthly_total

def _extract_time(query: str) -> Optional[TimeRange]:
    "Extract time-related information from the query."
    now = datetime.now()
    time_range = TimeRange()

    if re.search(r'\bthis month\b', query):
        time_range.month, time_range.year = now.month, now.year
    elif re.search(r'\blast month\b', query):
        prev = (now.replace(day=1) - timedelta(days=1))
        time_range.month, time_range.year = prev.month, prev.year
    elif re.search(r'\bthis year\b', query):
        time_range.year = now.year
    elif re.search(r'\blast year\b', query):
        time_range.year = now.year - 1

    month_match = re.search(r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\b', query)
    year_match = re.search(r'\b(20\d{2})\b', query)

    if month_match:
        time_range.month = datetime.strptime(month_match.group(1), '%B').month
        # Default to the most recent occurrence of that month
        time_range.year = time_range.year or (now.year if time_range.month <= now.month else now.year - 1)
    if year_match:
        time_range.year = int(year_match.group(1))

    return time_range if any([time_range.month, time_range.year]) else None

def _extract_filters(query: str) -> Optional[dict]:
    "Extract extra parameters: number of months for trends, and two months to compare."
    filters = {}

    n_match = re.search(r'\b(\d{1,2})\s*months?\b', query)
    if n_match:
        filters["n_months"] = max(1, min(24, int(n_match.group(1))))

    months = re.findall(r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\b', query)
    now = datetime.now()
    if len(months) >= 2:
        m1, m2 = (datetime.strptime(m, '%B').month for m in months[:2])
        filters.update(month1=m1, year1=now.year if m1 <= now.month else now.year - 1,
                       month2=m2, year2=now.year if m2 <= now.month else now.year - 1)
    elif re.search(r'\b(this|last) month\b', query) and re.search(r'\bcompare|vs|versus\b', query):
        prev = now.replace(day=1) - timedelta(days=1)
        filters.update(month1=prev.month, year1=prev.year, month2=now.month, year2=now.year)

    return filters or None

def _extract_category(query: str) -> Optional[str]:
    "Extract category information from the query."

    categories = ['food', 'entertainment', 'utilities', 'transportation', 'health', 'shopping']
    for category in categories:
        if category in query:
            return category
    return None

def _infer_query_type(query: str) -> QueryType:
    "Infer the query type based on keywords."
    specific_keywords = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december', '20']
    if any(keyword in query for keyword in specific_keywords):
        return QueryType.specific
    return QueryType.general