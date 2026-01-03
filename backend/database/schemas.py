from pydantic import BaseModel, EmailStr
from typing import Dict, List, Optional
from datetime import datetime

# User Schemas
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str  # hashed password expected

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    user_id: int
    name: str
    email: str

    class Config:
        from_attributes = True


# Category Schemas
class CategoryCreate(BaseModel):
    name: str

class CategoryResponse(BaseModel):
    category_id: int
    name: str

    class Config:
        from_attributes = True

class CategoryExpenseSummary(BaseModel):
    category_name: str
    total: float


# Expense Schemas
class ExpenseCreate(BaseModel):
    user_id: int
    category_id: int
    amount: float
    description: str

class ExpenseResponse(BaseModel):
    expense_id: int
    user_id: int
    category_id: int
    amount: float
    description: str
    expense_date: datetime
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None 
    class Config:
        from_attributes = True


# Expense Summary Schemas
class ExpenseSummaryResponse(BaseModel):
    user_id: int
    month: int
    year: int
    day: Optional[int] = None
    week: Optional[int] = None
    quarter: Optional[int] = None
    total_expense: float
    by_category: Dict[str, float]  # e.g., {"Food": 120.5, "Transport": 50}
    total_days: int
    average_per_day: float
    start_date: datetime
    end_date: datetime

    class Config:
        from_attributes = True
    
class CategoryExpenseSummary(BaseModel):
    category_name: str
    total: float
