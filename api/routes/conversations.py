"""
Conversation routes - Chat history management
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import desc
import uuid

from api.auth.deps import get_current_active_user
from src.database.db import get_db
from src.database.models import User, Conversation, Message
import logging

logger = logging.getLogger("api.conversations")

router = APIRouter(prefix="/conversations", tags=["Conversations"])


# ================== SCHEMAS ==================

class MessageResponse(BaseModel):
    """Message response schema"""
    id: int
    role: str
    content: str
    image_url: Optional[str] = None
    analysis_id: Optional[str] = None
    extra_data: Dict[str, Any] = {}
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    """Conversation response schema"""
    id: str
    title: str
    subject: Optional[str] = None
    grade: Optional[int] = None
    is_archived: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    message_count: int = 0

    class Config:
        from_attributes = True


class ConversationWithMessages(ConversationResponse):
    """Conversation with all messages"""
    messages: List[MessageResponse] = []


class CreateConversationRequest(BaseModel):
    """Create conversation request schema"""
    title: Optional[str] = "Yeni Sohbet"
    subject: Optional[str] = None
    grade: Optional[int] = Field(None, ge=1, le=12)


class UpdateConversationRequest(BaseModel):
    """Update conversation request schema"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    subject: Optional[str] = None
    grade: Optional[int] = Field(None, ge=1, le=12)
    is_archived: Optional[bool] = None


class AddMessageRequest(BaseModel):
    """Add message to conversation request schema"""
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str
    image_url: Optional[str] = None
    analysis_id: Optional[str] = None
    extra_data: Dict[str, Any] = {}


class ConversationListResponse(BaseModel):
    """Paginated conversation list response"""
    items: List[ConversationResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


# ================== ROUTES ==================

@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    archived: bool = Query(False),
    subject: Optional[str] = None,
):
    """
    List user's conversations with pagination.
    """
    query = db.query(Conversation).filter(
        Conversation.user_id == current_user.id,
        Conversation.is_archived == archived
    )

    if subject:
        query = query.filter(Conversation.subject == subject)

    # Get total count
    total = query.count()

    # Apply pagination
    offset = (page - 1) * page_size
    conversations = query.order_by(desc(Conversation.updated_at)).offset(offset).limit(page_size).all()

    # Add message counts
    items = []
    for conv in conversations:
        conv_dict = ConversationResponse.model_validate(conv)
        conv_dict.message_count = db.query(Message).filter(Message.conversation_id == conv.id).count()
        items.append(conv_dict)

    return ConversationListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + page_size) < total
    )


@router.post("", response_model=ConversationResponse)
async def create_conversation(
    request: CreateConversationRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new conversation.
    """
    conversation = Conversation(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        title=request.title or "Yeni Sohbet",
        subject=request.subject,
        grade=request.grade or current_user.grade,
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    logger.info(f"Conversation created: {conversation.id} by user {current_user.email}")

    response = ConversationResponse.model_validate(conversation)
    response.message_count = 0
    return response


@router.get("/{conversation_id}", response_model=ConversationWithMessages)
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a conversation with all messages.
    """
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sohbet bulunamadı"
        )

    # Load messages
    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at).all()

    response = ConversationWithMessages.model_validate(conversation)
    response.messages = [MessageResponse.model_validate(m) for m in messages]
    response.message_count = len(messages)

    return response


@router.put("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: str,
    request: UpdateConversationRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update a conversation.
    """
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sohbet bulunamadı"
        )

    update_data = request.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Güncellenecek alan belirtilmedi"
        )

    for field, value in update_data.items():
        setattr(conversation, field, value)

    conversation.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(conversation)

    logger.info(f"Conversation updated: {conversation_id}")

    response = ConversationResponse.model_validate(conversation)
    response.message_count = db.query(Message).filter(Message.conversation_id == conversation_id).count()
    return response


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete a conversation and all its messages.
    """
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sohbet bulunamadı"
        )

    db.delete(conversation)  # Cascade deletes messages
    db.commit()

    logger.info(f"Conversation deleted: {conversation_id}")

    return {"message": "Sohbet silindi"}


@router.post("/{conversation_id}/messages", response_model=MessageResponse)
async def add_message(
    conversation_id: str,
    request: AddMessageRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Add a message to a conversation.
    """
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sohbet bulunamadı"
        )

    message = Message(
        conversation_id=conversation_id,
        role=request.role,
        content=request.content,
        image_url=request.image_url,
        analysis_id=request.analysis_id,
        extra_data=request.extra_data,
    )
    db.add(message)

    # Update conversation timestamp and title if first message
    conversation.updated_at = datetime.utcnow()
    if conversation.title == "Yeni Sohbet" and request.role == "user":
        # Use first few words of user message as title
        title_text = request.content[:50]
        if len(request.content) > 50:
            title_text += "..."
        conversation.title = title_text

    db.commit()
    db.refresh(message)

    return MessageResponse.model_validate(message)


@router.post("/{conversation_id}/archive")
async def archive_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Archive a conversation.
    """
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sohbet bulunamadı"
        )

    conversation.is_archived = True
    conversation.updated_at = datetime.utcnow()
    db.commit()

    logger.info(f"Conversation archived: {conversation_id}")

    return {"message": "Sohbet arşivlendi"}


@router.post("/{conversation_id}/unarchive")
async def unarchive_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Unarchive a conversation.
    """
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sohbet bulunamadı"
        )

    conversation.is_archived = False
    conversation.updated_at = datetime.utcnow()
    db.commit()

    logger.info(f"Conversation unarchived: {conversation_id}")

    return {"message": "Sohbet arşivden çıkarıldı"}
