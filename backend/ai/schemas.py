from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, Literal, List
from datetime import datetime
from enum import Enum

# This file contains the Pydantic schemas for the AI functionality of SpendSense. It defines the request and response models, time ranges, intent types, and parsed intent structures used for interpreting and handling user queries through the AI system.


# AI Request Schema
class AIRequest(BaseModel):
    user_id: int # ID of the user making the AI request
    query: str # Natural language query
    context: Optional[List[str]] = None # conversation history
    filters: Optional[Dict[str, Any]] = None # Additional context for the AI
    top_n: Optional[int] = Field(1, ge=1, le=10)  # Number of suggestions/responses

    @field_validator("query")
    @classmethod
    def query_not_empty(cls, v: str):
        if not v.strip():
            raise ValueError("Query cannot be empty")
        return v

# AI Response Schema
class AIResponse(BaseModel):
    response: str
    data: Optional[Dict[str, Any]] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    suggestions: Optional[List[str]] = None  # Optional alternative responses or actions
    next_action: Optional[str] = None  # AI suggested next action
    execution_status: Optional[str] = None  # e.g., "success", "failed"
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Time range for intents
class TimeRange(BaseModel):
    month: Optional[int] = Field(None, ge=1, le=12)
    year: Optional[int] = Field(None, ge=2000, le=2100)
    week: Optional[int] = Field(None, ge=1, le=53)
    quarter: Optional[int] = Field(None, ge=1, le=4)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

# Supported intent types
class IntentType(str, Enum):
    monthly_total = "monthly_total"
    category_breakdown = "category_breakdown"
    spending_trend = "spending_trend"
    highest_spend_category = "highest_spend_category"
    compare_months = "compare_months"
    forecast = "forecast"
    detect_anomalies = "detect_anomalies"
    budget_suggestions = "budget_suggestions"

class QueryType(str, Enum):
    summary = "summary"
    advice = "advice"
    forecast = "forecast"

# Parsed intent structure
class ParsedIntent(BaseModel):
    intent: IntentType
    time: Optional[TimeRange] = None
    category: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None  # e.g., merchant, tag, payment method
    raw_query: Optional[str] = None  # Original user query for debugging
    query_type: Optional[QueryType] = QueryType.summary

    @field_validator("category")
    @classmethod
    def normalize_category(cls, v: Optional[str]):
        return v.strip().lower() if v else v

