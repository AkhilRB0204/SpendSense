from pydantic import BaseModel
from typing import Dict
from typing import List

# User schemas
class UserCreate(BaseModel):
    name: str
    email: str

class UserResponse(BaseModel):
    user_id: int
    name: str
    email: str
    model_config = {
        "from_attributes" : True
    }
# Category schemas
class CategoryCreate(BaseModel):
    name: str

class CategoryResponse(BaseModel):
    category_id: int
    name: str
    model_config = {
        "from_attributes": True
}

class CategoryExpenseSummary(BaseModel):
    category_name: str
    total: float

class ExpenseSummaryResponse(BaseModel):
    user_id: int
    month: int
    year: int
    total_expense: float
    category_breakdown: List[CategoryExpenseSummary]
    class Config:
        model_config = {
        "from_attributes": True
}


# Expense schemas
class ExpenseCreate(BaseModel):
    user_id: int
    category_id: int
    amount: float
    description: str | None = None  

class ExpenseResponse(BaseModel):
    expense_id: int
    user_id: int
    category_id: int
    amount: float
    description: str | None = None
    class Config:
        model_config = {
        "from_attributes": True
}

# Expense summary schema
class ExpenseSummaryResponse(BaseModel):
    total_spent: float
    by_category: Dict[str, float]