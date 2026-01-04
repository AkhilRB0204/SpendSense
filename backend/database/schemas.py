from pydantic import BaseModel, EmailStr, condecimal, validator
from typing import Dict, List, Optional
from datetime import datetime, date

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
    created_at: Optional[datetime] = None


    @validator("created_at", pre=True, always=True)
    def parse_created_at(cls, v):
        if v is None:
            return datetime.utcnow()
        if isinstance(v, datetime):
            return v
        try:
            # Parse MM/DD/YYYY format
            return datetime.strptime(v, "%m/%d/%Y")
        except ValueError:
            raise ValueError("created_at must be in MM/DD/YYYY format, e.g., 12/15/2025")




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
