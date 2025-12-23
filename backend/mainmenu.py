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
from fastapi import Query


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
    # welcome message
    return {"message": "Welcome to SpendSense AI, your personal AI powered expense tracker!"}

#  USERS 
@app.post("/users", response_model=schemas.UserResponse)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):

    # Validate email and password
    validate_email(user.email)
    validate_password(user.password)

    # Check if user already exists
    if crud.get_user_by_email(db, user.email):
        raise HTTPException(status_code=400, detail="User already exists")

    # Create and return new user
    return crud.create_user(db, user.name, user.email, user.password)


@app.post("/users/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Authenticate user
    user = crud.verify_user_credentials(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    # Generate and return JWT token
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

#  CATEGORIES 
@app.post("/categories", response_model=schemas.CategoryResponse)
def create_category_endpoint(category: schemas.CategoryCreate, db: Session = Depends(get_db)):
    # Check if category already exists
    if crud.get_category_by_name(db, category.name):
        raise HTTPException(status_code=400, detail="Category already exists")
    # Create and return new category
    return crud.create_category(db, category.name)

#  EXPENSES 
@app.post("/expenses", response_model=schemas.ExpenseResponse)
def create_expense_endpoint(expense: schemas.ExpenseCreate, db: Session = Depends(get_db)):
    # Check if user exists
    if not crud.get_user_by_id(db, expense.user_id):
        raise HTTPException(status_code=404, detail="User not found")
    # Check if category exists
    if not crud.get_category_by_name(db, expense.category_id):
        raise HTTPException(status_code=404, detail="Category not found")
    # Create and return new expense
    return crud.create_expense(db, expense.user_id, expense.category_id, expense.amount, expense.description)

# Debug endpoint to view all data
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
    if not crud.get_user_by_id(db, user_id):
        raise HTTPException(status_code=404, detail="User not found")

    # Get monthly summary from crud
    summary = crud.get_monthly_expense_summary(db, user_id, month, year)

    # Return summary with proper schema
    return schemas.ExpenseSummaryResponse(user_id=user_id, month=month, year=year, **summary)
