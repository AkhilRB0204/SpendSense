from pydantic import BaseModel

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