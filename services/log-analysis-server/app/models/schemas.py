"""
Pydantic request/response models

Defines API schemas for requests and responses
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class QueryRequest(BaseModel):
    """Request model for Text-to-SQL query"""
    question: str
    max_results: Optional[int] = 100


class QueryResponse(BaseModel):
    """Response model for Text-to-SQL query"""
    sql: str
    results: List[Dict[str, Any]]
    count: int
    displayed: int
    truncated: bool
    execution_time_ms: float
    insight: Optional[str] = None
    error: Optional[str] = None


class ConversationMessage(BaseModel):
    """Single message in conversation"""
    role: str  # 'user' | 'ai' | 'error' | 'status' | 'clarification'
    content: str
    sql: Optional[str] = None
    count: Optional[int] = None
    insight: Optional[str] = None


class SummarizeRequest(BaseModel):
    """Request model for conversation summarization"""
    messages: List[ConversationMessage]


class SummarizeResponse(BaseModel):
    """Response model for conversation summarization"""
    summary: str
