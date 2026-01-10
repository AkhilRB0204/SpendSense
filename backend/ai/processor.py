import re
from typing import Any, Dict, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from statistics import mean, stdev
from collections import defaultdict

from database import models
from .schemas import (
    AIResponse,
    IntentType,
    ParsedIntent,
    TimeRange
)

from database import crud as db_crud


# Main entry point to process AI queries
def process_ai_query(parsed_intent: ParsedIntent, db: Session, user_id: int) -> AIResponse:
    """Process the AI query based on the parsed intent and return an appropriate response."""
    if parsed_intent.intent == IntentType.advice:
        return AIResponse(
            response="You could reduce expenses by setting category limits and reviewing recurring charges.",
            execution_status="success"
        )
    
    try:

        if parsed_intent.intent == IntentType.advice:
            return generate_personalized_advice(db, user_id)

        elif parsed_intent.intent == IntentType.monthly_total:
            return monthly_total(parsed_intent, db, user_id)
    
        elif parsed_intent.intent == IntentType.category_breakdown:
            return category_breakdown(parsed_intent, db, user_id)
    
        elif parsed_intent.intent == IntentType.spending_trend:
            return spending_trend(parsed_intent, db, user_id)

        elif parsed_intent.intent == IntentType.highest_spend_category:
            return highest_spend_category(parsed_intent, db, user_id)
    
        elif parsed_intent.intent == IntentType.compare_months:
            return compare_months(parsed_intent, db, user_id)
    
        elif parsed_intent.intent == IntentType.forecast:
            return forecast_spending(parsed_intent, db, user_id)

        elif parsed_intent.intent == IntentType.detect_anomalies:
            return detect_anomalies(parsed_intent, db, user_id)

        elif parsed_intent.intent == IntentType.budget_suggestions:
            return budget_suggestions(parsed_intent, db, user_id)

        elif parsed_intent.intent == IntentType.highest_expense:
            return highest_expense(parsed_intent, db, user_id)
        
        elif parsed_intent.intent == IntentType.budget_check:
            return check_budget_alerts(db, user_id)
        elif parsed_intent.intent == IntentType.suggest_budget:
            category_id = None
            if parsed_intent.category:
                category = db.query(models.Category).filter(
                    models.Category.name.ilike(f"%{parsed_intent.category}%")
                ).first()
                if category:
                    category_id = category.category_id
            return suggest_budget_from_history(db, user_id, category_id)
        else :
            return AIResponse(
                response="I couldn’t fully understand that request yet.",
                execution_status="failed"
                )
    except Exception as e:
        return AIResponse(
            response=f"An error occurred while processing your request: {str(e)}",
            execution_status="failed"
        )


# Helper: monthly total
def get_monthly_expense_summary(db: Session, user_id: int, month: int, year: int) -> float:
    """Fetch total spending for a given month and year."""
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
        models.Expense.deleted_at.is_(None)
    )
    
    # Build response text based on time range
    if parsed_intent.time:
        if parsed_intent.time.month:
            query = query.filter(func.extract('month', models.Expense.date) == parsed_intent.time.month)
        if parsed_intent.time.year:
            query = query.filter(func.extract('year', models.Expense.date) == parsed_intent.time.year)
        if parsed_intent.time.day:
            query = query.filter(func.extract('day', models.Expense.date) == parsed_intent.time.day)

    
    total_spending = query.scalar() or 0.0

    if parsed_intent.time and parsed_intent.time.month and parsed_intent.time.year:
        response_text = f"Your total spending for {parsed_intent.time.month}/{parsed_intent.time.year} is ${total_spending:.2f}."
    elif parsed_intent.time and parsed_intent.time.year:
        response_text = f"Your total spending for {parsed_intent.time.year} is ${total_spending:.2f}."
    else:
        response_text = f"Your total recorded spending is ${total_spending:.2f}."

    return AIResponse(
        response=response_text,
        data={"total_spending": round(total_spending, 2)},
        execution_status="success"
    )


# Category breakdown
def category_breakdown(parsed_intent: ParsedIntent, db: Session, user_id: int) -> AIResponse:
    """Provide a breakdown of spending by category for a given month and year."""
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

    if not results:
        return AIResponse(
            response="No expenses found for the specified period.",
            data={"by_category": {}},
            execution_status="success"
        )

    breakdown = {name: float(amount) for name, amount in results}

    return AIResponse(
        response="Here's your category breakdown.",
        data={"by_category": breakdown},
        execution_status="success"
    )


# Highest spend category
def highest_spend_category(parsed_intent: ParsedIntent, db: Session, user_id: int) -> AIResponse:
    """Identify the category with the highest spending for a given month and year."""
    month = parsed_intent.time.month if parsed_intent.time else None
    year = parsed_intent.time.year if parsed_intent.time else None

    query = db.query(
        models.Category.name,
        func.sum(models.Expense.amount).label("total_amount")
    ).join(models.Expense, models.Expense.category_id == models.Category.id)\
     .filter(models.Expense.user_id == user_id, models.Expense.deleted_at.is_(None))

    if month:
        query = query.filter(func.extract('month', models.Expense.created_at) == month)
    if year:
        query = query.filter(func.extract('year', models.Expense.created_at) == year)

    result = query.group_by(models.Category.name).order_by(func.sum(models.Expense.amount).desc()).first()

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


# Highest expense
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

    highest_exp = query.order_by(models.Expense.amount.desc()).first()

    if not highest_exp:
        return AIResponse(
            response="No expenses found for the specified time range.",
            execution_status="failed"
        )

    return AIResponse(
        response=f"Your highest expense is ${highest_exp.amount:.2f} for '{highest_exp.description}'.",
        data={
            "expense_id": highest_exp.expense_id,
            "amount": float(highest_exp.amount),
            "description": highest_exp.description,
            "date": highest_exp.created_at.isoformat()
        },
        execution_status="success"
    )


# Compare months
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

    t1 = total_for_month(month1, year1)
    t2 = total_for_month(month2, year2)

    return AIResponse(
        response=f"Total spending for {month1}/{year1} is ${t1:.2f}, and for {month2}/{year2} is ${t2:.2f}.",
        data={"month1_total": t1, "month2_total": t2},
        execution_status="success"
    )


# Spending trend
def spending_trend(parsed_intent: ParsedIntent, db: Session, user_id: int) -> AIResponse:
    """Analyze spending trend over the past N months."""
    filters = parsed_intent.filters or {}
    n_months = filters.get("n_months", 6)
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
        {"year": int(year), "month": int(month), "total_amount": float(total_amount)}
        for year, month, total_amount in results
    ]

    if not trend:
        return AIResponse(
            response="No spending data available for trend analysis.",
            execution_status="failed"
        )

    return AIResponse(
        response=f"Here's your spending trend over the past {n_months} months.",
        data={"trend": trend},
        execution_status="success"
    )


# Forecast spending
def forecast_spending(parsed_intent: ParsedIntent, db: Session, user_id: int) -> AIResponse:
    """Forecast future spending based on historical data (average of past N months)."""
    filters = parsed_intent.filters or {}
    n_months = filters.get("n_months", 6)
    forecast_periods = filters.get("forecast_periods", 3)

    end_date = datetime.now()
    start_date = end_date.replace(day=1)
    for _ in range(n_months):
        start_date = (start_date - timedelta(days=1)).replace(day=1)

    query = db.query (
        func.extract('year', models.Expense.expense_date).label('year'),
        func.extract('month', models.Expense.expense_date).label('month'),
        func.sum(models.Expense.amount).label('total_amount')
    ).filter(
        models.Expense.user_id == user_id,
        models.Expense.deleted_at.is_(None),
        models.Expense.expense_date >= start_date,
        models.Expense.expense_date < end_date
    ).group_by(
        func.extract('year', models.Expense.expense_date),
        func.extract('month', models.Expense.expense_date)
    ).order_by(
        func.extract('year', models.Expense.expense_date),
        func.extract('month', models.Expense.expense_date)
    )

    results = query.all()

    if len(results) < 3:
        return AIResponse(
            response="Not enough historical data for accurate forecasting. Need at least 3 months of expense data.",
            execution_status="failed"
        )

    # Extract spending amounts
    historical_spending = [float(r.total_amount) for r in results]
    
    # Calculate trend
    if len(historical_spending) >= 2:
        recent_avg = mean(historical_spending[-3:]) if len(historical_spending) >= 3 else historical_spending[-1]
        older_avg = mean(historical_spending[:-3]) if len(historical_spending) > 3 else historical_spending[0]
        monthly_trend = (recent_avg - older_avg) / max(len(historical_spending) - 3, 1)
    else:
        monthly_trend = 0
        recent_avg = historical_spending[0]
    
    # Generate forecasts with dampening
    forecasts = []
    base_value = recent_avg
    
    for i in range(1, forecast_periods + 1):
        dampening_factor = 1 / (1 + i * 0.1)
        forecast_value = base_value + (monthly_trend * i * dampening_factor)
        forecasts.append(round(max(0, forecast_value), 2))
    
    # Determine trend direction
    avg_spending = mean(historical_spending)
    
    if abs(monthly_trend) < avg_spending * 0.05:
        trend_direction = "stable"
    elif monthly_trend > 0:
        trend_direction = "increasing"
    else:
        trend_direction = "decreasing"
    
    # Calculate confidence
    recent_volatility = stdev(historical_spending[-3:]) if len(historical_spending) >= 3 else 0
    
    if avg_spending > 0:
        confidence = max(50, min(95, 100 - (recent_volatility / avg_spending * 50)))
    else:
        confidence = 50
    
    response_text = f"Based on {len(historical_spending)} months of data, your spending is {trend_direction}. "
    response_text += f"Forecasted monthly spending: {', '.join([f'${f:.2f}' for f in forecasts])}. "
    response_text += f"Confidence: {confidence:.0f}%."
    
    return AIResponse(
        response=response_text,
        data={
            "historical_spending": historical_spending,
            "forecasts": forecasts,
            "trend_direction": trend_direction,
            "monthly_trend": round(monthly_trend, 2),
            "average_monthly": round(avg_spending, 2),
            "confidence_score": round(confidence, 1),
            "forecast_periods": forecast_periods
        },
        execution_status="success"
    )


# Detect anomalies
def detect_anomalies(parsed_intent: ParsedIntent, db: Session, user_id: int) -> AIResponse:
    """Detect spending anomalies in the user's expenses using IQR(Interquartile Range) Method."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    expenses = db.query(models.Expense).filter(
        models.Expense.user_id == user_id,
        models.Expense.deleted_at.is_(None),
        models.Expense.expense_date >= start_date
    ).all()

    if not expenses:
        return AIResponse(
            response="No expenses found to analyze for anomalies.",
            execution_status="failed"
        )

    # Simple anomaly: >2 standard deviations from category average
    category_data = defaultdict(list)
    for exp in expenses:
        category_data[exp.category_id].append({
            'amount': float(exp.amount),
            'date': exp.expense_date,
            'description': exp.description,
            'expense_id': exp.expense_id
        })

    anomalies = []

    for category_id, transactions in category_data.items():
        if len(transactions) < 5:
            continue
        
        amounts = [t['amount'] for t in transactions]
        sorted_amounts = sorted(amounts)
        
        # Calculate IQR
        n = len(sorted_amounts)
        q1_idx = n // 4
        q3_idx = (3 * n) // 4
        q1 = sorted_amounts[q1_idx]
        q3 = sorted_amounts[q3_idx]
        iqr = q3 - q1
        
        upper_bound = q3 + 1.5 * iqr
        avg_amount = mean(amounts)
        
        # Find anomalies
        for transaction in transactions:
            amount = transaction['amount']
            
            if amount > upper_bound and iqr > 0:
                if avg_amount > 0:
                    deviation_pct = ((amount - avg_amount) / avg_amount * 100)
                else:
                    deviation_pct = 0
                
                severity = "high" if amount > q3 + 3 * iqr else "medium"
                
                anomalies.append({
                    "expense_id": transaction['expense_id'],
                    "category_id": category_id,
                    "amount": amount,
                    "description": transaction['description'],
                    "date": transaction['date'].isoformat(),
                    "category_average": round(avg_amount, 2),
                    "deviation_percent": round(deviation_pct, 1),
                    "severity": severity
                })
        
        anomalies.sort(key=lambda x: (x['severity'] == 'high', x['amount']), reverse=True)
    
        if not anomalies:
            return AIResponse(
            response="No unusual spending patterns detected. Your expenses look consistent!",
            data={"anomalies": []},
            execution_status="success"
            )
        
        top = anomalies[0]
        response_text = f"Found {len(anomalies)} unusual transactions. "
        response_text += f"Most significant: ${top['amount']:.2f} for '{top['description']}' "
        response_text += f"({top['deviation_percent']:+.0f}% vs usual)."

        return AIResponse(
            response=response_text,
            data={"anomalies": anomalies[:10], "total_anomalies": len(anomalies)},
            execution_status="success"
            )

# Smart categorize
def smart_categorize(expense_description: str) -> str:
    """Basic keyword-based categorization."""
    categories = ["food", "entertainment", "transportation", "utilities", "health", "shopping"]
    expense_description = expense_description.lower()
    for cat in categories:
        if cat in expense_description:
            return cat
    return "other"


# Budget suggestions
def budget_suggestions(parsed_intent: ParsedIntent, db: Session, user_id: int) -> AIResponse:
    """Generate dynamic budget suggestions based on historical spending trends."""
    # Fetch last 6 months of spending by category
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    query = db.query(
        models.Category.name,
        models.Category.category_id,
        func.sum(models.Expense.amount).label('total_amount'),
        func.extract('month', models.Expense.expense_date).label('month'),
        func.extract('year', models.Expense.expense_date).label('year')
    ).join(
        models.Expense,
        models.Expense.category_id == models.Category.category_id
    ).filter(
        models.Expense.user_id == user_id,
        models.Expense.deleted_at.is_(None),
        models.Expense.expense_date >= start_date
    ).group_by(
        models.Category.name,
        models.Category.category_id,
        'month',
        'year'
    ).order_by('year', 'month').all()

    if not query:
        return AIResponse(
            response="Not enough spending data to generate personalized suggestions.",
            execution_status="failed"
        )

    # Organize data by category
    category_spending = defaultdict(list)
    for cat_name, cat_id, total, month, year in query:
        category_spending[cat_name].append(float(total))

    suggestions = []
    total_potential_savings = 0
    
    for category, monthly_amounts in category_spending.items():
        if len(monthly_amounts) < 3:
            continue
        
        avg_spending = mean(monthly_amounts)
        recent_spending = mean(monthly_amounts[-2:])
        
        if len(monthly_amounts) > 2:
            trend = recent_spending - mean(monthly_amounts[:-2])
        else:
            trend = 0
        
        if len(monthly_amounts) > 1:
            volatility = stdev(monthly_amounts)
        else:
            volatility = 0
        
        advice_items = []
        potential_savings = 0
        priority = "low"
        
        # Check for increasing trend
        if trend > avg_spending * 0.15:
            pct_increase = (trend / avg_spending * 100)
            advice_items.append(f"Spending up {pct_increase:.0f}% recently")
            potential_savings = trend * 0.5
            priority = "high"
        
        # Check for high volatility
        if volatility > avg_spending * 0.3:
            advice_items.append("Spending is inconsistent - consider setting a monthly limit")
            if priority == "low":
                priority = "medium"
        
        # Check if above average
        if recent_spending > avg_spending * 1.2:
            excess = recent_spending - avg_spending
            advice_items.append(f"Currently ${excess:.0f}/month above your average")
            potential_savings += excess * 0.3
            priority = "high"
        
        # Add category-specific tips
        category_tips = get_category_tips(category, avg_spending)
        if category_tips:
            advice_items.extend(category_tips)
        
        if advice_items:
            suggestions.append({
                "category": category,
                "current_monthly_avg": round(recent_spending, 2),
                "historical_avg": round(avg_spending, 2),
                "trend": "increasing" if trend > 0 else "decreasing",
                "priority": priority,
                "advice": advice_items,
                "potential_monthly_savings": round(potential_savings, 2),
                "suggested_budget": round(avg_spending * 1.1, 2)
            })
            total_potential_savings += potential_savings

    # Sort by priority
    priority_order = {"high": 0, "medium": 1, "low": 2}
    suggestions.sort(key=lambda x: (priority_order[x['priority']], -x['potential_monthly_savings']))
    
    if not suggestions:
        return AIResponse(
            response="Great job! Your spending patterns look healthy across all categories.",
            data={"suggestions": [], "total_potential_savings": 0},
            execution_status="success"
        )
    
    top = suggestions[0]
    response_text = f"Found {len(suggestions)} areas for improvement. "
    response_text += f"Potential savings: ${total_potential_savings:.2f}/month (${total_potential_savings * 12:.2f}/year). "
    response_text += f"Priority focus: {top['category']} category."

    return AIResponse(
        response=response_text,
        data={
            "suggestions": suggestions,
            "total_potential_savings": round(total_potential_savings, 2),
            "annual_potential_savings": round(total_potential_savings * 12, 2)
        },
        execution_status="success"
    )


def get_category_tips(category: str, avg_spending: float) -> List[str]:
    """Generate category-specific saving tips based on spending level."""
    category_lower = category.lower()
    tips = []
    
    if "food" in category_lower and avg_spending > 400:
        tips.extend([
            "Try meal planning to reduce impulse purchases",
            "Consider cooking at home more often"
        ])
    elif "entertainment" in category_lower and avg_spending > 200:
        tips.extend([
            "Look for free local events",
            "Share streaming subscriptions with family"
        ])
    elif "transportation" in category_lower and avg_spending > 300:
        tips.extend([
            "Consider carpooling or public transit",
            "Check for fuel rewards programs"
        ])
    elif "shopping" in category_lower and avg_spending > 250:
        tips.extend([
            "Wait 24 hours before non-essential purchases",
            "Use price comparison tools"
        ])
    elif "utilities" in category_lower and avg_spending > 200:
        tips.extend([
            "Review for unused subscriptions",
            "Consider energy-efficient upgrades"
        ])
    
    return tips



def generate_personalized_advice(db: Session, user_id: int) -> AIResponse:
    """Generate comprehensive personalized financial advice."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    total_spending = db.query(func.sum(models.Expense.amount)).filter(
        models.Expense.user_id == user_id,
        models.Expense.deleted_at.is_(None),
        models.Expense.expense_date >= start_date
    ).scalar() or 0.0
    
    expense_count = db.query(func.count(models.Expense.expense_id)).filter(
        models.Expense.user_id == user_id,
        models.Expense.deleted_at.is_(None),
        models.Expense.expense_date >= start_date
    ).scalar() or 0
    
    monthly_avg = total_spending / 3
    
    advice_points = []
    advice_points.append(f"Your average monthly spending is ${monthly_avg:.2f}")
    
    if expense_count > 0:
        avg_per_transaction = total_spending / expense_count
        advice_points.append(f"Average transaction: ${avg_per_transaction:.2f}")
    
    advice_points.extend([
        "Track expenses consistently for better insights",
        "Set category-specific budgets to control spending",
        "Review your subscriptions monthly for potential savings"
    ])
    
    response_text = "Here are some personalized tips based on your spending: " + ". ".join(advice_points)
    
    return AIResponse(
        response=response_text,
        data={
            "advice": advice_points,
            "monthly_average": round(monthly_avg, 2),
            "total_expenses": expense_count
        },
        execution_status="success"
    )

def check_budget_alerts(db: Session, user_id: int) -> AIResponse:
    "Check if user is approaching or exceeding their budgets. Returns alerts and recommendations."

    statuses = db_crud.get_all_budget_statuses

    if not statuses:
        return AIResponse(
            response="You haven't set any budgets yet. Would you like to set some budget limits?",
            data={"has_budgets": False},
            execution_status="success"
        )
    
    alerts = []
    over_budget = []
    approaching_limit = []
    on_track = []


    for status in statuses:
        category_name = status.get("category_name", "Overall")
        percentage = status.get("percentage_used", 0)
        spent = status.get("spent_amount", 0)
        budget_amt = status.get("budget_amount", 0)
        remaining = status.get("remaining_amount", 0)
        
        if status.get("is_over_budget"):
            over_budget.append({
                "category": category_name,
                "budget": budget_amt,
                "spent": spent,
                "over_by": abs(remaining)
            })
        elif status.get("should_alert"):
            approaching_limit.append({
                "category": category_name,
                "budget": budget_amt,
                "spent": spent,
                "remaining": remaining,
                "percentage": percentage
            })
        else:
            on_track.append({
                "category": category_name,
                "percentage": percentage,
                "remaining": remaining
            })
    
    # Build response message
    if over_budget:
        response_parts = [f" Budget Alert: You're over budget in {len(over_budget)} categories!"]
        for item in over_budget:
            response_parts.append(
                f"- {item['category']}: ${item['spent']:.2f} spent (budget: ${item['budget']:.2f}, over by ${item['over_by']:.2f})"
            )
    elif approaching_limit:
        response_parts = [f" You're approaching your budget limit in {len(approaching_limit)} categories."]
        for item in approaching_limit:
            response_parts.append(
                f"- {item['category']}: ${item['spent']:.2f} / ${item['budget']:.2f} ({item['percentage']:.0f}% used)"
            )
    else:
        response_parts = [" Great job! You're on track with all your budgets."]
        for item in on_track[:3]:  # Show top 3
            response_parts.append(
                f"- {item['category']}: {item['percentage']:.0f}% used, ${item['remaining']:.2f} remaining"
            )
    
    return AIResponse(
        response="\n".join(response_parts),
        data={
            "over_budget": over_budget,
            "approaching_limit": approaching_limit,
            "on_track": on_track,
            "total_budgets": len(statuses)
        },
        execution_status="success"
    )



def suggest_budget_from_history(db: Session, user_id: int, category_id: Optional[int] = None) -> AIResponse:
    # Suggest a budget amount based on historical spending patterns.

    # Get last 3 months of spending
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    query = db.query(func.sum(models.Expense.amount)).filter(
        models.Expense.user_id == user_id,
        models.Expense.deleted_at.is_(None),
        models.Expense.expense_date >= start_date,
        models.Expense.expense_date < end_date
    )
    
    if category_id:
        query = query.filter(models.Expense.category_id == category_id)
        category = db_crud.get_category_by_id(db, category_id)
        category_name = category.name if category else "Unknown"
    else:
        category_name = "Overall"
    
    total_spent = query.scalar() or 0.0
    monthly_avg = total_spent / 3
    
    # Suggest budget with 10% buffer
    suggested_budget = monthly_avg * 1.1
    
    # Calculate stretch goal (reduce by 10%)
    stretch_goal = monthly_avg * 0.9
    
    if monthly_avg == 0:
        return AIResponse(
            response=f"No spending history found for {category_name}. Consider setting a budget based on your expected expenses.",
            data={"suggested_budget": 0},
            execution_status="success"
        )
    
    response_text = f"Based on your spending history:\n"
    response_text += f"- Average {category_name} spending: ${monthly_avg:.2f}/month\n"
    response_text += f"- Recommended budget: ${suggested_budget:.2f}/month (with 10% buffer)\n"
    response_text += f"- Stretch goal: ${stretch_goal:.2f}/month (10% reduction)"
    
    return AIResponse(
        response=response_text,
        data={
            "category": category_name,
            "average_monthly": round(monthly_avg, 2),
            "suggested_budget": round(suggested_budget, 2),
            "stretch_goal": round(stretch_goal, 2),
            "confidence": "high" if monthly_avg > 100 else "medium"
        },
        execution_status="success"
    )


def budget_suggestions_with_limits(parsed_intent: ParsedIntent, db: Session, user_id: int) -> AIResponse:
    # Enhanced budget suggestions that considers existing budget limits.
    # This REPLACES the existing budget_suggestions function.


    # Get existing budget suggestions
    base_suggestions = budget_suggestions(parsed_intent, db, user_id)
    
    # Get user's current budgets
    budgets = db_crud.get_user_budgets(db, user_id, active_only=True)
    budget_by_category = {}
    
    for budget in budgets:
        if budget.category_id:
            category = db_crud.get_category_by_id(db, budget.category_id)
            if category:
                budget_by_category[category.name] = {
                    "budget_amount": budget.amount,
                    "period": budget.period
                }
    
    # Enhance suggestions with budget info
    if base_suggestions.data and "suggestions" in base_suggestions.data:
        for suggestion in base_suggestions.data["suggestions"]:
            category = suggestion["category"]
            if category in budget_by_category:
                budget_info = budget_by_category[category]
                suggestion["has_budget"] = True
                suggestion["budget_limit"] = budget_info["budget_amount"]
                suggestion["budget_period"] = budget_info["period"]
                
                # Compare suggested budget to existing
                if suggestion["suggested_budget"] < budget_info["budget_amount"]:
                    suggestion["recommendation"] = f"Your current budget (${budget_info['budget_amount']:.2f}) could be reduced"
            else:
                suggestion["has_budget"] = False
                suggestion["recommendation"] = f"Consider setting a budget of ${suggestion['suggested_budget']:.2f}/month"
    
    # Update response text
    if budget_by_category:
        base_suggestions.response += f" You have {len(budget_by_category)} active budgets."
    else:
        base_suggestions.response += " Consider setting budget limits to track your progress."
    
    return base_suggestions