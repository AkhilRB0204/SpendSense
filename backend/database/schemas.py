from pydantic import BaseModel, EmailStr
from typing import Dict
from typing import List

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

class ExpenseResponse(BaseModel):
    expense_id: int
    user_id: int
    category_id: int
    amount: float
    class Config:
        from_attributes = True


# Expense Summary Schemas
class ExpenseSummaryResponse(BaseModel):
    user_id: int
    month: int
    year: int
    total_spent: float
    by_category: Dict[str, float]  # e.g., {"Food": 120.5, "Transport": 50}

    class Config:
        from_attributes = True