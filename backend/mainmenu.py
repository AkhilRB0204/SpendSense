import re
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from database import models, database, schemas
from database.database import engine, SessionLocal
from sqlalchemy import func 
from datetime import datetime
from auth import hash_password, validate_password, verify_password, create_access_token, validate_email
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import EmailStr, ValidationError


# Create all tables
models.Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI()

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
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):

    # Validate email
    validate_email(user.email)

    validate_password(user.password)

    # Check if user already exists
    existing_user = db.query(models.User).filter(models.User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    # Hash the password
    hashed_pwd = hash_password(user.password)

    # Create new user
    db_user = models.User(
        name=user.name,
        email=user.email, 
        password=hashed_pwd
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/users/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    print("FORM DATA:", form_data)
    #Authenticate User
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    if not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

#  CATEGORIES 
@app.post("/categories", response_model=schemas.CategoryResponse)
def create_category(category: schemas.CategoryCreate, db: Session = Depends(get_db)):
    # Check if category already exists
    existing_category = db.query(models.Category).filter(models.Category.name == category.name).first()
    if existing_category:
        raise HTTPException(status_code=400, detail="Category already exists")

    # Create new category
    db_category = models.Category(name=category.name)
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

#  EXPENSES 
@app.post("/expenses", response_model=schemas.ExpenseResponse)
def create_expense(expense: schemas.ExpenseCreate, db: Session = Depends(get_db)):
    # Validate user exists
    user = db.query(models.User).filter(models.User.user_id == expense.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Validate category exists
    category = db.query(models.Category).filter(models.Category.category_id == expense.category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Create new expense
    db_expense = models.Expense(
        user_id=expense.user_id,
        category_id=expense.category_id,
        amount=expense.amount,
        description=expense.description
    )
    db.add(db_expense)
    db.commit()
    db.refresh(db_expense)
    return db_expense

@app.get("/debug")
def debug(db: Session = Depends(get_db)):
    return {
        "users": db.query(models.User).all(),
        "categories": db.query(models.Category).all(),
        "expenses": db.query(models.Expense).all()
    }

#  Monthly Expense Summary
@app.get("/users/{user_id}/expenses/summary", response_model=schemas.ExpenseSummaryResponse)
def monthly_summary(
        user_id: int,
        month: int = Query(..., ge=1, le=12),
        year: int = Query(..., ge=2000, le=2100),
    db: Session = Depends(get_db)
):
    # Validate user exists
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Determine start and end dates
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)

    total_days = (end_date - start_date).days

    # Total spent by user in the month
    total_expense = (
        db.query(func.sum(models.Expense.amount))
        .filter(models.Expense.user_id == user_id)
        .filter(models.Expense.created_at >= start_date)
        .filter(models.Expense.created_at < end_date)
        .scalar()
    )or 0.0

    average_per_day = round(total_expense / total_days, 2) if total_days > 0 else 0.0

    # Group by category
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

    # Format results
    category_breakdown: Dict[str, float] = {name: round(total, 2) for name, total in category_data}
    # return summary
    return schemas.ExpenseSummaryResponse(
        user_id=user_id,
        year=year,
        month=month,
        total_expense=round(total_expense, 2),
        by_category=category_breakdown,
        total_days=total_days,
        average_per_day=average_per_day,
        start_date=start_date,
        end_date=end_date
    )
