from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Replace USER and PASSWORD with your PostgreSQL credentials
SQLALCHEMY_DATABASE_URL = "sqlite:///./spendsense.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

app = FastAPI()

# SQLAlchemy model
class ExpenseDB(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    description = Column(String, nullable=False)
    category = Column(String, nullable=False)
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())

Base.metadata.create_all(bind=engine)

# Pydantic model
class Expense(BaseModel):
    amount: float
    description: str

class ExpenseOut(BaseModel):
    id: int
    amount: float
    description: str
    category: str 
    created_at: str

    class Config:
        orm_mode = True

# POST /expenses
@app.post("/expenses", response_model=ExpenseOut)
def add_expense(expense: Expense):
    db = SessionLocal()
    try:
        db_expense = ExpenseDB(
            amount=expense.amount,
            description=expense.description,
            category=expense.category
        )
        db.add(db_expense)
        db.commit()
        db.refresh(db_expense)
    finally:
        db.close()
    return db_expense

# GET /expenses
@app.get("/expenses", response_model=List[ExpenseOut])
def get_expenses():
    db = SessionLocal()
    try :
        expenses = db.query(ExpenseDB).all()
    finally :
        db.close()
    return expenses


# Root Endpoint
@app.get("/")
def root():
    return {"status": "SpendSense backend running"}