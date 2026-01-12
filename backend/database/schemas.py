from pydantic import BaseModel, EmailStr, validator
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

# 
class ChatMessageCreate(BaseModel):
    # Used when creating a new chat message
    user_id: int
    sender: str
    message: str

class ChatMessageResponse(BaseModel):
    # Used when returning messages to frontend
    id: int
    user_id: int
    sender: str
    message: str
    created_at: datetime

    class Config:
        from_attributes = True

class BudgetCreate(BaseModel):
    user_id: int
    category_id: Optional[int] = None
    amount: float # Positive decimal value
    start_date: Optional[datetime] = None
    period: str = "monthly"
    end_date: Optional[datetime] = None
    alert_threshold: float = 0.8  # Alert at 80%

    @validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("Budget amount must be positive")
        return v
    
    @validator("period")
    @classmethod
    def period_must_be_valid(cls, v):
        valid_periods = ["monthly", "weekly", "yearly", "daily"]
        if v.lower() not in valid_periods:
            raise ValueError(f"Period must be one of: {', '.join(valid_periods)}")
        return v.lower()
    
    @validator("alert_threshold")
    @classmethod
    def threshold_must_be_valid(cls, v):
        if v < 0 or v > 1:
            raise ValueError("Alert threshold must be between 0 and 1")
        return v
    
    @validator("start_date", "end_date", pre=True, always=True)
    def parse_dates(cls, v):
        if v is None:
            return None
        if isinstance(v, datetime):
            return v
        try:
            # Parse MM/DD/YYYY format
            return datetime.strptime(v, "%m/%d/%Y")
        except ValueError:
            raise ValueError("Date must be in MM/DD/YYYY format, e.g., 12/15/2025")

class BudgetUpdate(BaseModel):
    """Schema for updating an existing budget"""
    amount: Optional[float] = None
    period: Optional[str] = None
    end_date: Optional[datetime] = None
    is_active: Optional[bool] = None
    alert_threshold: Optional[float] = None

    @validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Budget amount must be positive")
        return v
    


class BudgetResponse(BaseModel):
    """Schema for budget response"""
    budget_id: int
    user_id: int
    category_id: Optional[int]
    category_name: Optional[str] = None
    amount: float
    period: str
    start_date: datetime
    end_date: Optional[datetime]
    is_active: bool
    alert_threshold: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BudgetStatus(BaseModel):
    """Schema for budget status with spending info"""
    budget_id: int
    category_id: Optional[int]
    category_name: Optional[str]
    budget_amount: float
    spent_amount: float
    remaining_amount: float
    percentage_used: float
    period: str
    is_over_budget: bool
    should_alert: bool
    days_remaining: Optional[int] = None
    
    class Config:
        from_attributes = True