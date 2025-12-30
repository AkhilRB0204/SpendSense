from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.database import get_db
from database import crud
from auth import get_current_user

from .schemas import AIRequest, AIResponse
from .processor import process_ai_query
from .intent_parser import parse_intent

router = APIRouter(prefix="/ai", tags=["AI"])

" This router exposes endpoints that allow authenticated users to interact with SpendSense’s AI-powered insights layer. It acts as the orchestration layer between user requests, intent parsing, and backend data processing. "


@router.post("/ai/query", response_model=AIResponse)
def ai_query_endpoint(
    request: AIRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):

    # Check if user is deleted
    if current_user.deleted_user:
        raise HTTPException(status_code=404, detail="User account is deleted")

    # Check if user ID in request matches current user
    if request.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Unauthorized access to user data")

    
# parse and process intent
parsed_intent = parse_intent(request.query)
result = process_ai_query(parsed_intent=parsed_intent, user_id=current_user.user_id, db=db)

return AIResponse(
    response=result("response"),
    data=result.get("data"),
    confidence=result.get("confidence"),
    suggestions=result.get("suggestions"),
    next_action=result.get("next_action"),
    execution_status="success"
)