from typing import List, Dict
from .schemas import IntentType, ParsedIntent, QueryType, TimeRange

# Mapping of IntentType to trigger keywords/phrases
INTENT_KEYWORDS: Dict[IntentType, List[str]] = {
    IntentType.monthly_total: ["total spend", "monthly total", "how much did i spend", "total spending"],
    IntentType.category_breakdown: ["category breakdown", "spending by category", "how is my spending divided"],
    IntentType.spending_trend: ["spending trend", "spending over time", "how has my spending changed", "pattern"],
    IntentType.highest_spend_category: ["highest spend category", "top spending category", "where do i spend the most"],
    IntentType.compare_months: ["compare months", "month comparison", "spending comparison"],
    IntentType.forecast: ["forecast", "predict", "spending forecast"],  # matches processor function
    IntentType.detect_anomalies: ["detect anomalies", "unusual spending", "anomaly detection"],
    IntentType.budget_suggestions: ["budget suggestions", "spending advice", "budget tips"],
    IntentType.highest_expense: ["highest expense", "biggest expense", "largest spending"],
}


# Mapping of QueryType to trigger keywords/phrases
QUERY_KEYWORDS: Dict[QueryType, List[str]] = {
    QueryType.summary: ["summary", "overview", "report"],
    QueryType.advice: ["advice", "tips", "suggestions"],
    QueryType.forecast: ["forecast", "predict", "projection"],
}


# Intent identification
def identify_intent(query: str) -> IntentType:
    """Identify the intent type from the user's query based on keywords."""
    normalized_query = query.lower()
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(keyword in normalized_query for keyword in keywords):
            return intent
    return IntentType.monthly_total  # Default intent if no match


def identify_query_type(query: str) -> QueryType:
    """Identify the query type from the user's query based on keywords."""
    normalized_query = query.lower()
    for qtype, keywords in QUERY_KEYWORDS.items():
        if any(keyword in normalized_query for keyword in keywords):
            return qtype
    return QueryType.summary  # Default query type if no match


# Parse query into structured intent
def parse_intent_from_query(
    query: str,
    time_range: TimeRange = None,
    category: str = None,
    filters: Dict[str, Any] = None
) -> ParsedIntent:
    """
    Parse the user's query into a structured ParsedIntent object
    that can be passed directly to the processor.
    """
    intent = identify_intent(query)
    query_type = identify_query_type(query)

    return ParsedIntent(
        intent=intent,
        time=time_range,
        category=category,
        filters=filters,
        raw_query=query,
        query_type=query_type
    )
