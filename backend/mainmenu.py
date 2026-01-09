from fastapi import FastAPI, HTTPException, Depends, Query, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime

from auth import hash_password, validate_password, verify_password, create_access_token, validate_email
from database import models, database, schemas, crud
from database.database import engine, SessionLocal

from ai.processor import process_ai_query
from ai.intents import parse_intent_from_query
from ai.schemas import AIRequest, AIResponse, ParsedIntent, TimeRange, IntentType, QueryType
from fastapi.middleware.cors import CORSMiddleware

# Define the FastAPI app first
app = FastAPI(title="SpendSense AI")

# CORS config
origins = [
    "http://localhost:5173",  #  Vite dev server
    "http://127.0.0.1:5173",
    "*",  # optional for testing
]

# Allow React frontend (Vite default: http://localhost:5173) to talk to FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create all tables
models.Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(title="SpendSense AI")

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


@app.put("/users/{user_id}", response_model=schemas.UserResponse)
# Update user details
def update_user_endpoint(user_id: int, user_update: schemas.UserCreate, db: Session = Depends(get_db)):
    updated_user = crud.update_user(db, user_id, user_update.name, user_update.email, user_update.password)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found or deleted")
    return updated_user


@app.delete("/users/{user_id}", response_model=schemas.UserResponse)
# delete a user
def delete_user_endpoint(user_id: int, db: Session = Depends(get_db)):
    deleted_user = crud.soft_delete_user(db, user_id)
    if not deleted_user:
        raise HTTPException(status_code=404, detail="User not found")
    return deleted_user

#  CATEGORIES 
@app.post("/categories", response_model=schemas.CategoryResponse)
def create_category_endpoint(category: schemas.CategoryCreate, db: Session = Depends(get_db)):
    # Check if category already exists
    if crud.get_category_by_name(db, category.name):
        raise HTTPException(status_code=400, detail="Category already exists")
    # Create and return new category
    return crud.create_category(db, category.name)

@app.put("/categories/{category_id}", response_model=schemas.CategoryResponse)
def update_category_endpoint(category_id: int, category_update: schemas.CategoryCreate, db: Session = Depends(get_db)):
    #Update a category
    category = crud.get_category_by_id(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    category.name = category_update.name
    db.commit()
    db.refresh(category)
    return category

@app.delete("/categories/{category_id}", response_model=schemas.CategoryResponse)
def delete_category_endpoint(category_id: int, db: Session = Depends(get_db)):
    #Delete a category
    category = crud.get_category_by_id(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    db.delete(category)
    db.commit()
    return category

#  EXPENSES 
@app.post("/expenses", response_model=schemas.ExpenseResponse)
def create_expense_endpoint(expense: schemas.ExpenseCreate, db: Session = Depends(get_db)):
    # Check if user exists
    if not crud.get_user_by_id(db, expense.user_id):
        raise HTTPException(status_code=404, detail="User not found")
    # Check if category exists
    if not crud.get_category_by_id(db, expense.category_id):
        raise HTTPException(status_code=404, detail="Category not found")
    # Create and return new expense
    return crud.create_expense(db, expense.user_id, expense.category_id, expense.amount, expense.description, created_at=expense.created_at)

@app.put("/expenses/{expense_id}", response_model=schemas.ExpenseResponse)
def update_expense_endpoint(expense_id: int, expense_update: schemas.ExpenseCreate, db: Session = Depends(get_db)):
    # Update an expense
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
    # Soft delete an expense
    deleted_expense = crud.soft_delete_expense(db, expense_id)
    if not deleted_expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    return deleted_expense

# Debug endpoint to view all data
@app.get("/debug")
def debug(db: Session = Depends(get_db)):
    return {
        "users": db.query(models.User).all(),
        "categories": db.query(models.Category).all(),
        "expenses": db.query(models.Expense).all()
    }

# Ai query endpoint
@app.post("/ai/query", response_model=AIResponse)
def ai_query(request: AIRequest, db: Session = Depends(get_db)):
    # Validate user exists
    current_user = crud.get_user_by_id(db, request.user_id)
    if current_user is None or current_user.deleted_at:
        raise HTTPException(status_code=404, detail="User not found or inactive")

    # Parse user query
    parsed_intent = parse_intent_from_query(request.query)

    # Process AI query via processor
    result = process_ai_query(parsed_intent=parsed_intent, db=db, user_id=current_user.user_id)

    return result 



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

#Save a chat message
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

# Get chat history for a user
@app.get("/users/{user_id}/chat", response_model=list[schemas.ChatMessageResponse])
def get_chat_history(user_id: int, db: Session = Depends(get_db)):
    return db.query(models.ChatMessage)\
             .filter(models.ChatMessage.user_id == user_id)\
             .order_by(models.ChatMessage.created_at)\
             .all()