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

def create_expense(db: Session, user_id: int, category_id: int, amount: float, description: str):
    # Create a new expense linked to a user and category
    db_expense = models.Expense(
        user_id=user_id,
        category_id=category_id,
        amount=amount,
        description=description
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
        .filter(models.Expense.created_at >= start_date)
        .filter(models.Expense.created_at < end_date)
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
        .filter(models.Expense.created_at >= start_date)
        .filter(models.Expense.created_at < end_date)
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