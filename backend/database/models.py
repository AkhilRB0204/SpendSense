from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    sender = Column(String, nullable=False)  # "User" or "AI"
    message = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="chats")

class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)         # User's name
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False) # hashed password
    deleted_at = Column(DateTime, nullable=True) # delete column
    chats = relationship("ChatMessage", back_populates="user") # allows a user object to access its chat messages via user.chats
    budgets = relationship("Budget", back_populates="user")

    # Relationship with expenses
    expenses = relationship("Expense", back_populates="user")


class Category(Base):
    __tablename__ = "categories"

    category_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)  # Category name
    budgets = relationship("Budget", back_populates="category")

    # Relationship with expenses
    expenses = relationship("Expense", back_populates="category")


class Expense(Base):
    __tablename__ = "expenses"

    expense_id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer, 
        ForeignKey("users.user_id"),
        nullable=False,
        index=True
    )

    category_id = Column(
        Integer, 
        ForeignKey("categories.category_id"),
        nullable=False,
        index=True
    )

    amount = Column(Float, nullable=False)
    description = Column(String, nullable=True)

    expense_date = Column(DateTime, default=datetime.utcnow)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="expenses")
    category = relationship("Category", back_populates="expenses")

class Budget(Base):
    __tablename__ = "budgets"

    budget_id = Column(Integer, primary_key=True, index=True)
    
    user_id = Column(
        Integer, 
        ForeignKey("users.user_id"),
        nullable=False,
        index=True
    )
    
    category_id = Column(
        Integer, 
        ForeignKey("categories.category_id"),
        nullable=True,  # NULL means overall budget
        index=True
    )

    amount = Column(Float, nullable=False)  # Budget limit
    period = Column(String, nullable=False, default="monthly")  # monthly, weekly, yearly
    
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)  # NULL means ongoing
    
    is_active = Column(Integer, default=1)  # 1=active, 0=inactive
    alert_threshold = Column(Float, default=0.8)  # Alert at 80% of budget
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="budgets")
    category = relationship("Category", back_populates="budgets")