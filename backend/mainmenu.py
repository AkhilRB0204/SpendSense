# mainmenu.py
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

# Import from database folder
from database.databaseutility import engine, get_db
from database.models import Base, User, Category, Expense

app = FastAPI(title="SpendSense API")

# Create tables
Base.metadata.create_all(bind=engine)

# --- Pydantic Schemas ---
class UserCreate(BaseModel):
    username: str
    email: str

class CategoryCreate(BaseModel):
    name: str

class ExpenseCreate(BaseModel):
    user_id: int
    amount: float
    description: str
    category_name: str

#  Routes
@app.get("/")
def read_root():
    return {"message": "Welcome to SpendSense API"}

# Create User
@app.post("/users")
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    db_user = User(username=user.username, email=user.email)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {"user_id": db_user.user_id, "username": db_user.username, "email": db_user.email}

# Create a new category
@app.post("/categories")
def create_category(category: CategoryCreate, db: Session = Depends(get_db)):
    existing_category = db.query(Category).filter(Category.category_name == category.category_name).first()
    if existing_category:
        raise HTTPException(status_code=400, detail="Category already exists")
    
    db_category = Category(category_name=category.category_name)
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return {"category_id": db_category.category_id, "category_name": db_category.category_name}

# Add a new expense
@app.post("/expenses")
def create_expense(expense: ExpenseCreate, db: Session = Depends(get_db)):
    # Check if user exists
    user = db.query(User).filter(User.user_id == expense.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if category exists; create if not
    category = db.query(Category).filter(Category.category_name == expense.category_name).first()
    if not category:
        category = Category(category_name=expense.category_name)
        db.add(category)
        db.commit()
        db.refresh(category)

    # Add expense
    db_expense = Expense(
        user_id=user.user_id,
        category_id=category.category_id,
        amount=expense.amount,
        description=expense.description
    )
    db.add(db_expense)
    db.commit()
    db.refresh(db_expense)

    return {
        "expense_id": db_expense.expense_id,
        "user_id": db_expense.user_id,
        "amount": db_expense.amount,
        "description": db_expense.description,
        "category": category.category_name,
        "created_at": db_expense.created_at
    }

# --- Get all expenses ---
@app.get("/expenses")
def get_all_expenses(db: Session = Depends(get_db)):
    expenses = db.query(Expense).join(Category).all()
    return [
        {
            "expense_id": e.expense_id,
            "user_id": e.user_id,
            "amount": e.amount,
            "description": e.description,
            "category": db.query(Category).filter(Category.category_id == e.category_id).first().category_name,
            "created_at": e.created_at
        }
        for e in expenses
    ]