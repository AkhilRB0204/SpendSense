from typing import Any, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import models
from datetime import datetime
from .schemas import (
    AIResponse,
    IntentType,
    ParsedIntent,
)

def process_ai_query(parsed_intent: ParsedIntent, db: Session, user_id: int) -> AIResponse: 
    """Process the AI query based on the parsed intent and return an appropriate response."""
    if parsed_intent.intent == IntentType.monthly_total:
        return get_monthly_total(parsed_intent, db, user_id)
    
    if parsed_intent.intent == IntentType.category_breakdown:
        return get_category_breakdown(parsed_intent, db, user_id)
    
    if parsed_intent.intent == IntentType.spending_trend:
        return get_spending_trend(parsed_intent, db, user_id)

    if parsed_intent.intent == IntentType.highest_spend_category:
        return get_highest_spend_category(parsed_intent, db, user_id)
    
    if parsed_intent.intent == IntentType.compare_months:
        return compare_months(parsed_intent, db, user_id)

    # faillback response for unhandled intents
    return AIResponse(
        response="I couldn’t fully understand that request yet.",
        execution_status="failed"
    )