from typing import Any, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import models, crud
from datetime import datetime, timedelta
from .schemas import (
    AIResponse,
    IntentType,
    ParsedIntent,
)

def process_ai_query(parsed_intent: ParsedIntent, db: Session, user_id: int) -> AIResponse: 
    """Process the AI query based on the parsed intent and return an appropriate response."""
    if parsed_intent.intent == IntentType.monthly_total:
        return monthly_total(parsed_intent, db, user_id)
    
    if parsed_intent.intent == IntentType.category_breakdown:
        return get_category_breakdown(parsed_intent, db, user_id)
    
    if parsed_intent.intent == IntentType.spending_trend:
        return get_spending_trend(parsed_intent, db, user_id)

    if parsed_intent.intent == IntentType.highest_spend_category:
        return get_highest_spend_category(parsed_intent, db, user_id)
    
    if parsed_intent.intent == IntentType.compare_months:
        return compare_months(parsed_intent, db, user_id)
    
    if parsed_intent.intent == IntentType.forecast:
        return forecast_spending(parsed_intent, db, user_id)

    if parsed_intent.intent == IntentType.detect_anomalies:
        return detect_anomalies(parsed_intent, db, user_id)

    if parsed_intent.intent == IntentType.budget_suggestions:
        return budget_suggestions(parsed_intent, db, user_id)

    if parsed_intent.intent == IntentType.highest_expense:
        return highest_expense(parsed_intent, db, user_id)

    # faillback response for unhandled intents
    return AIResponse(
        response="I couldn’t fully understand that request yet.",
        execution_status="failed"
    )

def get_monthly_expense_summary(db: Session, user_id: int, month: int, year: int) -> float:
    """Helper to fetch total spending for a given month/year."""
    return (
        db.query(func.sum(models.Expense.amount))
        .filter(
            models.Expense.user_id == user_id,
            models.Expense.deleted_at.is_(None),
            func.extract('month', models.Expense.date) == month,
            func.extract('year', models.Expense.date) == year
        )
        .scalar() or 0.0
    )


def monthly_total(parsed_intent: ParsedIntent, db: Session, user_id: int) -> AIResponse:
    """Calculate the total spending for a given month and year."""
    query = db.query(func.sum(models.Expense.amount)).filter(
        models.Expense.user_id == user_id,
        models.Expense.deleted_at.is_(None)  # fixed deleted_expense -> deleted_at
    )
    
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

def category_breakdown(parsed_intent: ParsedIntent, db: Session, user_id: int) -> AIResponse:
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

def highest_spend_category(parsed_intent: ParsedIntent, db: Session, user_id: int) -> AIResponse:
    month = parsed_intent.time.month if parsed_intent.time else None
    year = parsed_intent.time.year if parsed_intent.time else None
    """Identify the category with the highest spending for a given month and year."""
    query = query = db.query(models.Category.name, func.sum(models.Expense.amount).label("total_amount"))\
        .join(models.Expense, models.Expense.category_id == models.Category.id)\
        .filter(models.Expense.user_id == user_id, models.Expense.deleted_at.is_(None))

    if month:
        query = query.filter(func.extract('month', models.Expense.created_at) == month)
    if year:
        query = query.filter(func.extract('year', models.Expense.created_at) == year)

    # Group by category and order descending by total
    result = query.group_by(models.Category.name).order_by(func.sum(models.Expense.amount).desc()).first()

    # No expenses found
    if not result:
        return AIResponse(
            response="No expenses found for the specified time range.",
            execution_status="failed"
        )

    category, total_amount = result
    return AIResponse(
        response=f"Your highest spending category is '{category}' with ${total_amount:.2f}.",
        data={"category": category, "amount": float(total_amount)},
        execution_status="success"
    )

def highest_expense(parsed_intent: ParsedIntent, db: Session, user_id: int) -> AIResponse:
    """Identify the single highest expense for a given month and year."""
    month = parsed_intent.time.month if parsed_intent.time else None
    year = parsed_intent.time.year if parsed_intent.time else None

    query = db.query(models.Expense).filter(
        models.Expense.user_id == user_id,
        models.Expense.deleted_at.is_(None)
    )

    if month:
        query = query.filter(func.extract('month', models.Expense.created_at) == month)
    if year:
        query = query.filter(func.extract('year', models.Expense.created_at) == year)

    highest_expense = query.order_by(models.Expense.amount.desc()).first()

    if not highest_expense:
        return AIResponse(
            response="No expenses found for the specified time range.",
            execution_status="failed"
        )

    return AIResponse(
        response=f"Your highest expense is ${highest_expense.amount:.2f} for '{highest_expense.description}'.",
        data={
            "expense_id": highest_expense.expense_id,
            "amount": float(highest_expense.amount),
            "description": highest_expense.description,
            "date": highest_expense.created_at.isoformat()
        },
        execution_status="success"
    )

def compare_months(parsed_intent: ParsedIntent, db: Session, user_id: int) -> AIResponse:
    """Compare spending between two specified months."""
    filters = parsed_intent.filters or {}
    month1, year1 = filters.get("month1"), filters.get("year1")
    month2, year2 = filters.get("month2"), filters.get("year2")

    if not all([month1, year1, month2, year2]):
        return AIResponse(
            response="Please provide both months and years to compare.",
            execution_status="failed"
        )
    

    def total_for_month(m, y):
        return (
            db.query(func.sum(models.Expense.amount))
            .filter(
                models.Expense.user_id == user_id,
                models.Expense.deleted_at.is_(None),
                func.extract('month', models.Expense.created_at) == m,
                func.extract('year', models.Expense.created_at) == y
            )
            .scalar() or 0.0
        )
    t1, t2 = total_for_month(month1, year1), total_for_month(month2, year2)
    return AIResponse(
        response=f"Total spending for {month1}/{year1} is ${t1:.2f}, and for {month2}/{year2} is ${t2:.2f}.",
        data={"month_total": t1, "month2_total": t2},
        execution_status="success"
)
def spending_trend(parsed_intent: ParsedIntent, db: Session, user_id: int) -> AIResponse:
    """Analyze spending trend over the past N months."""
    n_months = parsed_intent.filters.get("n_months", 6) if parsed_intent.filters else 6
    end_date = datetime.now()
    start_date = end_date.replace(day=1)
    for _ in range(n_months):
        start_date = (start_date.replace(day=1) - timedelta(days=1)).replace(day=1)

    query = db.query(
        func.extract('year', models.Expense.created_at).label('year'),
        func.extract('month', models.Expense.created_at).label('month'),
        func.sum(models.Expense.amount).label('total_amount')
    ).filter(
        models.Expense.user_id == user_id,
        models.Expense.deleted_at.is_(None),
        models.Expense.created_at >= start_date,
        models.Expense.created_at < end_date
    ).group_by(
        func.extract('year', models.Expense.created_at),
        func.extract('month', models.Expense.created_at)
    ).order_by(
        func.extract('year', models.Expense.created_at),
        func.extract('month', models.Expense.created_at)
    )

    results = query.all()
    trend = [
        {
            "year": int(year),
            "month": int(month),
            "total_amount": float(total_amount)
        }
        for year, month, total_amount in results
    ]

    return AIResponse(
        response=f"Here's your spending trend over the past {n_months} months.",
        data={"trend": trend},
        execution_status="success"
    )
def forecast_spending(parsed_intent: ParsedIntent, db: Session, user_id: int) -> AIResponse:
    """Forecast future spending based on historical data."""
    # Simple forecasting logic (e.g., average of past 6 months)
    n_months = parsed_intent.filters.get("n_months", 6) if parsed_intent.filters else 6

    end_date = datetime.now()
    start_date = end_date.replace(day=1)
    for _ in range(n_months):
        start_date = (start_date - timedelta(days=1)).replace(day=1)

    total_spent = (
        db.query(func.sum(models.Expense.amount).label('total_amount')
        ).filter(
            models.Expense.user_id == user_id,
            models.Expense.deleted_at.is_(None),
            models.Expense.created_at >= start_date,
            models.Expense.created_at < end_date
    )
    .scalar() or 0.0 
    )
    average_monthly_spending = total_spent / n_months if n_months > 0 else 0.0

    return AIResponse(
        response=f"Based on your past {n_months} months, your forecasted monthly spending is approximately ${average_monthly_spending:.2f}.",
        data={"forecasted_monthly_spending": round(average_monthly_spending, 2), "months_analyzed": n_months}, execution_status="success")
    
    def detect_anomalies(parsed_intent: ParsedIntent, db: Session, user_id: int) -> AIResponse:
        """Detect spending anomalies in the user's expenses."""
        expenses = db.query(models.Expense).filter(
            models.Expense.user_id == user_id,
            models.Expense.deleted_at.is_(None)
        ).all()

    if not expenses:
        return AIResponse(
            response="No expenses found to analyze for anomalies.",
            execution_status="failed"
        )

    # Simple anomaly: >2 std deviations from category average
    from statistics import mean, stdev
    category_totals = {}
    for exp in expenses:
        category_totals.setdefault(exp.category_id, []).append(exp.amount)
        
    # Identify anomalies
    anomalies = []
    for category_id, amounts in category_totals.items():
        if len(amounts) < 2: 
            continue
        avg = mean(amounts)
        sd = stdev(amounts)
        for amt in amounts:
            if abs(amt - avg) > 2 * sd:
                anomalies.append({"category_id": category_id, "amount": amt, "avg": avg})

    return AIResponse(
        response=f"Detected {len(anomalies)} unusual transactions.",
        data={"anomalies": anomalies},
        execution_status="success"
    )

    # could be used for smart categorization of expenses
    def smart_categorize(expense_description: str) -> str:
        categories = ["food", "entertainment", "transportation", "utilities", "health", "shopping"]
        expense_description = expense_description.lower()
        for cat in categories:
            if cat in expense_description:
                return cat
        return "other"

def budget_suggestions(parsed_intent: ParsedIntent, db: Session, user_id: int) -> AIResponse:
    """Generate dynamic budget suggestions based on historical spending trends."""
    from statistics import mean

    # Fetch last 6 months of spending by category
    expenses = db.query(
        models.Category.name,
        func.sum(models.Expense.amount).label('total_amount'),
        func.extract('month', models.Expense.created_at).label('month'),
        func.extract('year', models.Expense.created_at).label('year')
    ).join(models.Expense, models.Expense.category_id == models.Category.id)\
     .filter(
        models.Expense.user_id == user_id,
        models.Expense.deleted_at.is_(None)
     ).group_by('month', 'year', models.Category.name)\
     .order_by('year', 'month').all()

    if not expenses:
        return AIResponse(
            response="No spending data to generate suggestions.",
            execution_status="failed"
        )

    # Aggregate totals by category over months
    category_totals = {}
    for cat_name, total_amount, month, year in expenses:
        category_totals.setdefault(cat_name, []).append(total_amount)

    # Generate suggestions: if last month exceeds 20% of category average
    suggestions = []
    last_month = max((y, m) for _, _, m, y in expenses)
    for cat, totals in category_totals.items():
        avg = mean(totals[:-1]) if len(totals) > 1 else totals[0]
        last = totals[-1]
        if last > 1.2 * avg:  # more than 20% above average
            suggestions.append({
                "category": cat,
                "last_month": last,
                "average": round(avg, 2),
                "advice": f"Spending in {cat} increased by {round((last-avg)/avg*100, 1)}% this month. Consider reviewing your budget."
            })

    return AIResponse(
        response=f"Generated {len(suggestions)} budget suggestions based on your spending trends.",
        data={"suggestions": suggestions},
        execution_status="success"
    )
