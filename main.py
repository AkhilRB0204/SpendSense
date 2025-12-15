from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Replace USER and PASSWORD with your PostgreSQL credentials
SQLALCHEMY_DATABASE_URL = "postgresql://USER:PASSWORD@localhost/spendsense"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

app = FastAPI()

# SQLAlchemy model
class ExpenseDB(Base):
    __tablename__ = "expenses"
    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    description = Column(String, nullable=False)

Base.metadata.create_all(bind=engine)

# Pydantic model
class Expense(BaseModel):
    id: int = None
    amount: float
    description: str

    class Config:
        orm_mode = True

# POST /expenses
@app.post("/expenses", response_model=Expense)
def add_expense(expense: Expense):
    db = SessionLocal()
    db_exp = ExpenseDB(amount=expense.amount, description=expense.description)
    db.add(db_exp)
    db.commit()
    db.refresh(db_exp)
    db.close()
    return db_exp

# GET /expenses
@app.get("/expenses", response_model=List[Expense])
def get_expenses():
    db = SessionLocal()
    expenses = db.query(ExpenseDB).all()
    db.close()
    return expenses

