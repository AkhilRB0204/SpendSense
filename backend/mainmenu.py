from datetime import datetime, date
from fastapi import FastAPI, Depends
from pydantic import BaseModel
from typing import List
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session


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
class ExpenseIn(BaseModel):
    user_id: int
    description: str
    amount: float
    category: str            # <-- make sure this exists
    transaction_date: date = None

class ExpenseOut(BaseModel):
    id: int
    amount: float
    description: str
    category: str 
    created_at: str

    class Config:
        from_attributes = True


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# POST /expenses
@app.post("/expenses", response_model=ExpenseOut)
def add_expense(expense: ExpenseIn, db: Session = Depends(get_db)):
    db_expense = ExpenseDB(
        amount=expense.amount,
        description=expense.description,
        category=expense.category,
        created_at=(expense.transaction_date or datetime.utcnow()).isoformat()
    )
    db.add(db_expense)
    db.commit()
    db.refresh(db_expense)
    return db_expense

# GET /expenses
@app.get("/expenses", response_model=List[ExpenseOut])
def get_expenses(db: Session = Depends(get_db)):
    """
    Returns all expenses in the database.
    """
    return db.query(ExpenseDB).all()

# Root Endpoint
@app.get("/")
def root():
    return {"status": "SpendSense backend running"}