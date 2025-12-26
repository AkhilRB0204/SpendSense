from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

from .schemas import AIRequest, AIResponse, ParsedIntent, IntentType, QueryType
from .processor import process_ai_query