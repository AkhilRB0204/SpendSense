from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)         # User's name
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False) # hashed password
    deleted_at = Column(DateTime, nullable=True) # delete column

    # Relationship with expenses
    expenses = relationship("Expense", back_populates="user")


class Category(Base):
    __tablename__ = "categories"

    category_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)  # Category name

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
