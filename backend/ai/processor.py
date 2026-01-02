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

def get_monthly_total(parsed_intent: ParsedIntent, db: Session, user_id: int) -> AIResponse:
    """Calculate the total spending for a given month and year."""
    query = db.query(func.sum(models.Expense.amount)).filter(
        models.Expense.user_id == user_id,
        models.Expense.deleted_expense == False
    )
    
    # Apply time filters if provided
    if parsed_intent.time:
        if parsed_intent.time.month:
            query = query.filter(func.extract('month', models.Expense.date) == parsed_intent.time.month)
        if parsed_intent.time.year:
            query = query.filter(func.extract('year', models.Expense.date) == parsed_intent.time.year)
    
    total_spending = query.scalar() or 0.0

    if parsed_intent.time and parsed_intent.time.month and parsed_intent.time.year:
        response_text = (
            f"Your total spending for "
            f"{parsed_intent.time.month}/{parsed_intent.time.year} "
            f"is ${total_spending:.2f}."
        )
    else:
        response_text = f"Your total recorded spending is ${total_spending:.2f}."

    return AIResponse(
        response=response_text,
        data={"total_spending": round(total_spending, 2)},
        execution_status="success"
    )

    def get_category_breakdown(parsed_intent: ParsedIntent, db: Session, user_id: int) -> AIResponse:
    #Provide a breakdown of spending by category for a given month and year
        month = parsed_intent.time.month if parsed_intent.time else None
        year = parsed_intent.time.year if parsed_intent.time else None
        query = db.query(models.Category.name, func.sum(models.Expense.amount))\
            .join(models.Expense, models.Expense.category_id == models.Category.id)\
            .filter(models.Expense.user_id == user_id)\
            .filter(models.Expense.deleted_at.is_(None))

        if month:
            query = query.filter(func.extract('month', models.Expense.created_at) == month)
        if year:
            query = query.filter(func.extract('year', models.Expense.created_at) == year)

        query = query.group_by(models.Category.name)
        results = query.all()

        breakdown = {name: float(amount) for name, amount in results}

        return AIResponse(
            response=f"Here's your category breakdown.",
            data={"by_category": breakdown},
            execution_status="success"
        )
