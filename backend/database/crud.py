from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from database import models
from auth import hash_password, verify_password
from typing import Dict, List

#  USERS 

def create_user(db: Session, name: str, email: str, password: str):
    # Hash the password and create a new user
    hashed_pwd = hash_password(password)
    db_user = models.User(name=name, email=email, password=hashed_pwd)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, user_id: int, name: str = None, email: str = None, password: str = None):
    # Update user details
    user = get_user_by_id(db, user_id)
    if not user:
        return None
    if name:
        user.name = name
    if email:
        user.email = email
    if password:
        user.password = hash_password(password)
    db.commit()
    db.refresh(user)
    return user

def soft_delete_user(db: Session, user_id: int):
    # delete a user by setting deleted_at timestamp
    user = get_user_by_id(db, user_id)
    if not user:
        return None
    user.deleted_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    return user


def get_user_by_email(db: Session, email: str):
    # Retrieve a user from the database by email
    return db.query(models.User).filter(models.User.email == email, models.User.deleted_at.is_(None)).first()

def get_user_by_id(db: Session, user_id: int):
    # Retrieve a user from the database by user_id
    return db.query(models.User).filter(models.User.user_id == user_id, models.User.deleted_at.is_(None)).first()


def verify_user_credentials(db: Session, email: str, password: str):
    # Verify user credentials; return user if valid, else None
    user = get_user_by_email(db, email)
    if user and verify_password(password, user.password):
        return user
    return None

#  CATEGORIES 

def get_category_by_name(db: Session, name: str):
    # Retrieve a category by name
    return db.query(models.Category).filter(models.Category.name == name).first()

def get_category_by_id(db: Session, category_id: int):
    # Retrieve a category by its ID
    return db.query(models.Category).filter(models.Category.category_id == category_id).first()

def create_category(db: Session, name: str):
    # Create a new category
    db_category = models.Category(name=name)
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

#  EXPENSES 

def create_expense(db: Session, user_id: int, category_id: int, amount: float, description: str, expense_date: datetime = None):
    # Create a new expense linked to a user and category
    db_expense = models.Expense(
        user_id=user_id,
        category_id=category_id,
        amount=amount,
        description=description,
        expense_date=expense_date if expense_date else datetime.utcnow()
        # created_at will be set automatically by default in the model
    )
    db.add(db_expense)
    db.commit()
    db.refresh(db_expense)
    return db_expense

def get_expense_by_id(db: Session, expense_id: int):
    # Retrieve an expense by its ID
    return db.query(models.Expense).filter(models.Expense.expense_id == expense_id).first()

def update_expense(db: Session, expense_id: int, amount: float = None, description: str = None, category_id: int = None):
    # Update expense details
    expense = get_expense_by_id(db, expense_id)
    if not expense:
        return None
    if amount is not None:
        expense.amount = amount
    if description is not None:
        expense.description = description
    if category_id is not None:
        expense.category_id = category_id
    db.commit()
    db.refresh(expense)
    return expense

def soft_delete_expense(db: Session, expense_id: int):
    # Soft delete an expense by setting deleted_at timestamp
    expense = get_expense_by_id(db, expense_id)
    if not expense:
        return None
    expense.deleted_at = datetime.utcnow()
    db.commit()
    db.refresh(expense)
    return expense

def get_expenses(db: Session):
    # Retrieve all expenses
    return db.query(models.Expense).all()


def get_monthly_expense_summary(db: Session, user_id: int, month: int, year: int):
    # Compute start and end dates for the month
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)

    # Total number of days in the month
    total_days = (end_date - start_date).days

    # Calculate total spent by user in the month 
    total_expense = (
        db.query(func.sum(models.Expense.amount))
        .filter(models.Expense.user_id == user_id)
        .filter(models.Expense.deleted_at.is_(None))
        .filter(models.Expense.expense_date >= start_date)
        .filter(models.Expense.expense_date < end_date)
        .scalar()
    ) or 0.0

    # Calculate average spending per day
    average_per_day = round(total_expense / total_days, 2) if total_days > 0 else 0.0

    # Calculate spending breakdown by category
    category_data = (
        db.query(
            models.Category.name,
            func.sum(models.Expense.amount)
        )
        .join(models.Expense, models.Expense.category_id == models.Category.category_id)
        .filter(models.Expense.user_id == user_id)
        .filter(models.Expense.deleted_at.is_(None))
        .filter(models.Expense.expense_date >= start_date)
        .filter(models.Expense.expense_date < end_date)
        .group_by(models.Category.name)
        .all()
    )

    # Format results as dictionary {category_name: total_amount}
    category_breakdown: Dict[str, float] = {name: round(total, 2) for name, total in category_data}

    # Return summary dictionary
    return {
        "total_expense": round(total_expense, 2),
        "average_per_day": average_per_day,
        "total_days": total_days,
        "start_date": start_date,
        "end_date": end_date,
        "by_category": category_breakdown
    }



def create_budget(db: Session, user_id: int, category_id: int = None, amount: float = 0, 
                  start_date: datetime = None, period: str = "monthly", 
                  end_date: datetime = None, alert_threshold: float = 0.8):
    """Create a new budget"""
    db_budget = models.Budget(
        user_id=user_id,
        category_id=category_id,
        amount=amount,
        period=period,
        start_date=start_date if start_date else datetime.utcnow(),
        end_date=end_date,
        alert_threshold=alert_threshold,
        is_active=1
    )
    db.add(db_budget)
    db.commit()
    db.refresh(db_budget)
    return db_budget

def get_budget_by_id(db: Session, budget_id: int):
    """Retrieve a budget by its ID"""
    return db.query(models.Budget).filter(
        models.Budget.budget_id == budget_id,
        models.Budget.deleted_at.is_(None)
    ).first()

def get_user_budgets(db: Session, user_id: int, active_only: bool = True):
    """Get all budgets for a user"""
    query = db.query(models.Budget).filter(
        models.Budget.user_id == user_id,
        models.Budget.deleted_at.is_(None)
    )
    if active_only:
        query = query.filter(models.Budget.is_active == 1)
    return query.all()

def get_budget_by_category(db: Session, user_id: int, category_id: int = None):
    """Get budget for a specific category (or overall budget if category_id is None)"""
    return db.query(models.Budget).filter(
        models.Budget.user_id == user_id,
        models.Budget.category_id == category_id,
        models.Budget.is_active == 1,
        models.Budget.deleted_at.is_(None)
    ).first()

def update_budget(db: Session, budget_id: int, amount: float = None, 
                  period: str = None, end_date: datetime = None, 
                  is_active: int = None, alert_threshold: float = None):
    """Update an existing budget"""
    budget = get_budget_by_id(db, budget_id)
    if not budget:
        return None
    
    if amount is not None:
        budget.amount = amount
    if period is not None:
        budget.period = period
    if end_date is not None:
        budget.end_date = end_date
    if is_active is not None:
        budget.is_active = is_active
    if alert_threshold is not None:
        budget.alert_threshold = alert_threshold
    
    budget.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(budget)
    return budget

def soft_delete_budget(db: Session, budget_id: int):
    """Soft delete a budget by setting deleted_at timestamp"""
    budget = get_budget_by_id(db, budget_id)
    if not budget:
        return None
    
    budget.deleted_at = datetime.utcnow()
    db.commit()
    db.refresh(budget)
    return budget

def deactivate_budget(db: Session, budget_id: int):
    """Deactivate a budget (set is_active to 0)"""
    return update_budget(db, budget_id, is_active=0)

def activate_budget(db: Session, budget_id: int):
    """Activate a budget (set is_active to 1)"""
    return update_budget(db, budget_id, is_active=1)

def get_budget_period_dates(budget: models.Budget):
    """Calculate the current period start and end dates for a budget"""
    now = datetime.utcnow()
    
    if budget.period == "daily":
        start = datetime(now.year, now.month, now.day)
        end = start.replace(hour=23, minute=59, second=59)
    elif budget.period == "weekly":
        # Start from Monday of current week
        days_since_monday = now.weekday()
        start = now - datetime.timedelta(days=days_since_monday)
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + datetime.timedelta(days=7)
    elif budget.period == "monthly":
        start = datetime(now.year, now.month, 1)
        if now.month == 12:
            end = datetime(now.year + 1, 1, 1)
        else:
            end = datetime(now.year, now.month + 1, 1)
    elif budget.period == "yearly":
        start = datetime(now.year, 1, 1)
        end = datetime(now.year + 1, 1, 1)
    else:
        # Default to monthly
        start = datetime(now.year, now.month, 1)
        if now.month == 12:
            end = datetime(now.year + 1, 1, 1)
        else:
            end = datetime(now.year, now.month + 1, 1)
    
    # Respect budget start_date if it's later than calculated start
    if budget.start_date > start:
        start = budget.start_date
    
    # Respect budget end_date if set and earlier than calculated end
    if budget.end_date and budget.end_date < end:
        end = budget.end_date
    
    return start, end

def get_budget_status(db: Session, budget_id: int):
    """Get spending status for a specific budget"""
    budget = get_budget_by_id(db, budget_id)
    if not budget:
        return None
    
    start_date, end_date = get_budget_period_dates(budget)
    
    # Calculate total spent in current period
    query = db.query(func.sum(models.Expense.amount)).filter(
        models.Expense.user_id == budget.user_id,
        models.Expense.deleted_at.is_(None),
        models.Expense.expense_date >= start_date,
        models.Expense.expense_date < end_date
    )
    
    # Filter by category if budget is category-specific
    if budget.category_id:
        query = query.filter(models.Expense.category_id == budget.category_id)
    
    spent_amount = query.scalar() or 0.0
    
    remaining_amount = budget.amount - spent_amount
    percentage_used = (spent_amount / budget.amount * 100) if budget.amount > 0 else 0
    is_over_budget = spent_amount > budget.amount
    should_alert = percentage_used >= (budget.alert_threshold * 100)
    
    # Calculate days remaining in period
    now = datetime.utcnow()
    if now < end_date:
        days_remaining = (end_date - now).days
    else:
        days_remaining = 0
    
    # Get category name
    category_name = None
    if budget.category_id:
        category = get_category_by_id(db, budget.category_id)
        category_name = category.name if category else None
    else:
        category_name = "Overall Budget"
    
    return {
        "budget_id": budget.budget_id,
        "category_id": budget.category_id,
        "category_name": category_name,
        "budget_amount": budget.amount,
        "spent_amount": round(spent_amount, 2),
        "remaining_amount": round(remaining_amount, 2),
        "percentage_used": round(percentage_used, 2),
        "period": budget.period,
        "is_over_budget": is_over_budget,
        "should_alert": should_alert,
        "days_remaining": days_remaining
    }

def get_all_budget_statuses(db: Session, user_id: int) -> List[Dict]:
    """Get spending status for all active budgets of a user"""
    budgets = get_user_budgets(db, user_id, active_only=True)
    statuses = []
    
    for budget in budgets:
        status = get_budget_status(db, budget.budget_id)
        if status:
            statuses.append(status)
    
    return statuses