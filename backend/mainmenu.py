from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from database import models, database, schemas
from database.database import engine, SessionLocal

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
    # Check if user already exists
    existing_user = db.query(models.User).filter(models.User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    # Create new user
    db_user = models.User(name=user.name, email=user.email)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

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