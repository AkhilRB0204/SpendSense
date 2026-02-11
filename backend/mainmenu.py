from fastapi import FastAPI, HTTPException, Depends, Query, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from typing import List
import os
from dotenv import load_dotenv

# Rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request


import auth  # Import the module, not individual functions yet
from database import models, database, schemas, crud
from database.database import engine, SessionLocal

from ai.processor import process_ai_query
from ai.intents import parse_intent_from_query
from ai.schemas import AIRequest, AIResponse, ParsedIntent, TimeRange, IntentType, QueryType
from fastapi.middleware.cors import CORSMiddleware

# Define the FastAPI app
app = FastAPI(title="SpendSense AI")

# Rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS config
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create all tables
models.Base.metadata.create_all(bind=engine)

# Dependency: get DB session
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# root endpoint
@app.get("/")
def read_root():
    return {"message": "Welcome to SpendSense AI, your personal AI powered expense tracker!"}

#  USERS 
@app.post("/users", response_model=schemas.UserResponse)
@limiter.limit("3/minute")  # Rate limit: 3 signups per minute
def create_user(request: Request, user: schemas.UserCreate, db: Session = Depends(get_db)):
    auth.validate_email(user.email)
    auth.validate_password(user.password)

    if crud.get_user_by_email(db, user.email):
        raise HTTPException(status_code=400, detail="User already exists")

    return crud.create_user(db, user.name, user.email, user.password)


@app.post("/users/login")
@limiter.limit("5/minute")  # Rate limit: 5 login attempts per minute
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = crud.verify_user_credentials(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    access_token = auth.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


@app.put("/users/{user_id}", response_model=schemas.UserResponse)
def update_user_endpoint(user_id: int, user_update: schemas.UserCreate, db: Session = Depends(get_db)):
    updated_user = crud.update_user(db, user_id, user_update.name, user_update.email, user_update.password)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found or deleted")
    return updated_user


@app.delete("/users/{user_id}", response_model=schemas.UserResponse)
def delete_user_endpoint(user_id: int, db: Session = Depends(get_db)):
    deleted_user = crud.soft_delete_user(db, user_id)
    if not deleted_user:
        raise HTTPException(status_code=404, detail="User not found")
    return deleted_user

#  CATEGORIES 
@app.post("/categories", response_model=schemas.CategoryResponse)
def create_category_endpoint(category: schemas.CategoryCreate, db: Session = Depends(get_db)):
    if crud.get_category_by_name(db, category.name):
        raise HTTPException(status_code=400, detail="Category already exists")
    return crud.create_category(db, category.name)

@app.put("/categories/{category_id}", response_model=schemas.CategoryResponse)
def update_category_endpoint(category_id: int, category_update: schemas.CategoryCreate, db: Session = Depends(get_db)):
    category = crud.get_category_by_id(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    category.name = category_update.name
    db.commit()
    db.refresh(category)
    return category

@app.delete("/categories/{category_id}", response_model=schemas.CategoryResponse)
def delete_category_endpoint(category_id: int, db: Session = Depends(get_db)):
    category = crud.get_category_by_id(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    db.delete(category)
    db.commit()
    return category

#  EXPENSES 
@app.post("/expenses", response_model=schemas.ExpenseResponse)
def create_expense_endpoint(expense: schemas.ExpenseCreate, db: Session = Depends(get_db)):
    if not crud.get_user_by_id(db, expense.user_id):
        raise HTTPException(status_code=404, detail="User not found")
    if not crud.get_category_by_id(db, expense.category_id):
        raise HTTPException(status_code=404, detail="Category not found")
    return crud.create_expense(db, expense.user_id, expense.category_id, expense.amount, expense.description, expense_date=expense.created_at)

@app.put("/expenses/{expense_id}", response_model=schemas.ExpenseResponse)
def update_expense_endpoint(expense_id: int, expense_update: schemas.ExpenseCreate, db: Session = Depends(get_db)):
    updated_expense = crud.update_expense(
        db,
        expense_id,
        amount=expense_update.amount,
        description=expense_update.description,
        category_id=expense_update.category_id
    )
    if not updated_expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    return updated_expense

@app.delete("/expenses/{expense_id}", response_model=schemas.ExpenseResponse)
def delete_expense_endpoint(expense_id: int, db: Session = Depends(get_db)):
    deleted_expense = crud.soft_delete_expense(db, expense_id)
    if not deleted_expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    return deleted_expense

# BUDGETS
@app.post("/budgets", response_model=schemas.BudgetResponse)
def create_budget(
    budget: schemas.BudgetCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user)  # Use auth.get_current_user
):
    """Create a new budget for authenticated user"""
    user = crud.get_user_by_id(db, current_user['user_id'])
    if not user or user.deleted_at:
        raise HTTPException(status_code=404, detail="User not found")
    
    if budget.category_id:
        category = crud.get_category_by_id(db, budget.category_id)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
    
    db_budget = crud.create_budget(
        db=db,
        user_id=user.user_id,
        amount=budget.amount,
        category_id=budget.category_id,
        period=budget.period,
        start_date=budget.start_date,
        end_date=budget.end_date,
        alert_threshold=budget.alert_threshold
    )

    response = schemas.BudgetResponse.from_orm(db_budget)
    if db_budget.category_id:
        category = crud.get_category_by_id(db, db_budget.category_id)
        response.category_name = category.name if category else None
    else:
        response.category_name = "Overall Budget"
    
    return response


@app.get("/budgets", response_model=List[schemas.BudgetResponse])
def get_budgets(
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user)
):
    """Get all budgets for authenticated user"""
    user = crud.get_user_by_id(db, current_user['user_id'])
    if not user or user.deleted_at:
        raise HTTPException(status_code=404, detail="User not found")
    
    budgets = crud.get_user_budgets(db, user.user_id, active_only=active_only)
    
    responses = []
    for budget in budgets:
        response = schemas.BudgetResponse.from_orm(budget)
        if budget.category_id:
            category = crud.get_category_by_id(db, budget.category_id)
            response.category_name = category.name if category else None
        else:
            response.category_name = "Overall Budget"
        responses.append(response)
    
    return responses


@app.get("/budgets/status", response_model=List[schemas.BudgetStatus])
def get_budget_statuses(
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user)
):
    """Get spending status for all budgets"""
    user = crud.get_user_by_id(db, current_user['user_id'])
    if not user or user.deleted_at:
        raise HTTPException(status_code=404, detail="User not found")
    
    return crud.get_all_budget_statuses(db, user.user_id)


@app.get("/budgets/{budget_id}", response_model=schemas.BudgetResponse)
def get_budget(
    budget_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user)
):
    """Get specific budget"""
    budget = crud.get_budget_by_id(db, budget_id)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    if budget.user_id != current_user['user_id']:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    response = schemas.BudgetResponse.from_orm(budget)
    if budget.category_id:
        category = crud.get_category_by_id(db, budget.category_id)
        response.category_name = category.name if category else None
    else:
        response.category_name = "Overall Budget"
    
    return response


@app.put("/budgets/{budget_id}", response_model=schemas.BudgetResponse)
def update_budget(
    budget_id: int,
    budget_update: schemas.BudgetUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user)
):
    """Update existing budget"""
    budget = crud.get_budget_by_id(db, budget_id)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    if budget.user_id != current_user['user_id']:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    updated = crud.update_budget(
        db=db,
        budget_id=budget_id,
        amount=budget_update.amount,
        period=budget_update.period,
        end_date=budget_update.end_date,
        is_active=budget_update.is_active,
        alert_threshold=budget_update.alert_threshold
    )
    
    response = schemas.BudgetResponse.from_orm(updated)
    if updated.category_id:
        category = crud.get_category_by_id(db, updated.category_id)
        response.category_name = category.name if category else None
    else:
        response.category_name = "Overall Budget"
    
    return response


@app.delete("/budgets/{budget_id}")
def delete_budget(
    budget_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user)
):
    """Delete budget"""
    budget = crud.get_budget_by_id(db, budget_id)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    if budget.user_id != current_user['user_id']:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    crud.soft_delete_budget(db, budget_id)
    return {"message": "Budget deleted successfully"}

# Debug endpoint
@app.get("/debug")
def debug(db: Session = Depends(get_db)):
    return {
        "users": db.query(models.User).all(),
        "categories": db.query(models.Category).all(),
        "expenses": db.query(models.Expense).all()
    }

# AI query endpoint
@app.post("/ai/query", response_model=AIResponse)
@limiter.limit("20/minute")  # Rate limit AI queries
def ai_query(request: AIRequest, db: Session = Depends(get_db)):
    current_user = crud.get_user_by_id(db, request.user_id)
    if current_user is None or current_user.deleted_at:
        raise HTTPException(status_code=404, detail="User not found or inactive")

    parsed_intent = parse_intent_from_query(request.query)
    result = process_ai_query(parsed_intent=parsed_intent, db=db, user_id=current_user.user_id)
    return result 

# Monthly Expense Summary
@app.get("/users/{user_id}/expenses/summary", response_model=schemas.ExpenseSummaryResponse)
def monthly_summary(
    user_id: int,
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2000, le=2100),
    db: Session = Depends(get_db)
):
    if not crud.get_user_by_id(db, user_id):
        raise HTTPException(status_code=404, detail="User not found")

    summary = crud.get_monthly_expense_summary(db, user_id, month, year)
    return schemas.ExpenseSummaryResponse(user_id=user_id, month=month, year=year, **summary)

# Get current authenticated user's profile
@app.get("/users/me", response_model=schemas.UserResponse)
def get_current_user_profile(
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user)
):
    """Get current authenticated user's profile"""
    user = crud.get_user_by_id(db, current_user['user_id'])
    
    if not user or user.deleted_at:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user

# Save a chat message
@app.post("/users/{user_id}/chat", response_model=schemas.ChatMessageResponse)
def save_chat_message(chat: schemas.ChatMessageCreate, db: Session = Depends(get_db)):
    db_chat = models.ChatMessage(
        user_id=chat.user_id,
        sender=chat.sender,
        message=chat.message
    )
    db.add(db_chat)
    db.commit()
    db.refresh(db_chat)
    return db_chat

# Get chat history
@app.get("/users/{user_id}/chat", response_model=list[schemas.ChatMessageResponse])
def get_chat_history(user_id: int, db: Session = Depends(get_db), current_user: dict = Depends(auth.get_current_user)):
    if user_id != current_user['user_id']:
        raise HTTPException(status_code=403, detail="Not authorized")
    return db.query(models.ChatMessage)\
             .filter(models.ChatMessage.user_id == user_id)\
             .order_by(models.ChatMessage.created_at)\
             .all()

# Get all categories
@app.get("/categories", response_model=List[schemas.CategoryResponse])
def get_all_categories(db: Session = Depends(get_db)):
    categories = db.query(models.Category).all()
    return categories

@app.get("/expenses", response_model=List[schemas.ExpenseResponse])
def get_user_expenses(
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user)
):
    """Get all expenses for authenticated user"""
    user = crud.get_user_by_id(db, current_user['user_id'])
    if not user or user.deleted_at:
        raise HTTPException(status_code=404, detail="User not found")
    
    expenses = db.query(models.Expense)\
        .filter(models.Expense.user_id == current_user['user_id'])\
        .filter(models.Expense.deleted_at == None)\
        .order_by(models.Expense.expense_date.desc())\
        .all()
    
    return expenses

@app.get("/expenses/summary", response_model=schemas.ExpenseSummaryResponse)
def get_expense_summary(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2000, le=2100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(auth.get_current_user)
):
    """Get expense summary for authenticated user"""
    user = crud.get_user_by_id(db, current_user['user_id'])
    if not user or user.deleted_at:
        raise HTTPException(status_code=404, detail="User not found")

    summary = crud.get_monthly_expense_summary(db, current_user['user_id'], month, year)
    return schemas.ExpenseSummaryResponse(
        user_id=current_user['user_id'], 
        month=month, 
        year=year, 
        **summary
    )