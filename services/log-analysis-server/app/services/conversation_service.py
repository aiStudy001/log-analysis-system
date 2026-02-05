"""
Conversation Service

Manages conversation sessions with history and context tracking.
"""
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ConversationTurn:
    """Single conversation turn (Q&A pair)"""
    question: str
    resolved_question: str
    sql: str
    result_count: int
    focus: dict
    timestamp: datetime


@dataclass
class ConversationSession:
    """Conversation session with history and focus tracking"""
    conversation_id: str
    turns: List[ConversationTurn] = field(default_factory=list)
    current_focus: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def add_turn(self, question: str, response: dict):
        """
        Add Q&A turn to conversation

        Args:
            question: Original user question
            response: Agent response with SQL and results
        """
        turn = ConversationTurn(
            question=question,
            resolved_question=response.get("resolved_question", question),
            sql=response.get("sql", ""),
            result_count=response.get("count", 0),
            focus=response.get("current_focus", {}),
            timestamp=datetime.now()
        )
        self.turns.append(turn)
        self.current_focus = turn.focus

        # Keep only last 10 turns (memory management)
        if len(self.turns) > 10:
            self.turns = self.turns[-10:]

    def get_context_summary(self) -> str:
        """
        Get conversation context summary for prompt

        Returns:
            Formatted string with recent turns
        """
        if not self.turns:
            return ""

        recent_turns = self.turns[-3:]  # Last 3 turns
        summary = []
        for i, turn in enumerate(recent_turns, 1):
            summary.append(
                f"{i}. Q: {turn.question}\n"
                f"   A: {turn.result_count}건 ({turn.focus})"
            )

        return "\n".join(summary)


class ConversationService:
    """Manages multiple conversation sessions"""

    def __init__(self):
        self._sessions: Dict[str, ConversationSession] = {}

    def get_or_create_session(self, conversation_id: str) -> ConversationSession:
        """
        Get existing session or create new one

        Args:
            conversation_id: Unique session identifier

        Returns:
            ConversationSession instance
        """
        if conversation_id not in self._sessions:
            self._sessions[conversation_id] = ConversationSession(conversation_id)
        return self._sessions[conversation_id]

    def add_turn(self, conversation_id: str, question: str, response: dict):
        """
        Add turn to session

        Args:
            conversation_id: Session identifier
            question: User question
            response: Agent response
        """
        session = self.get_or_create_session(conversation_id)
        session.add_turn(question, response)

    def get_context(self, conversation_id: str) -> dict:
        """
        Get current context for session

        Args:
            conversation_id: Session identifier

        Returns:
            Dict with focus and history
        """
        session = self._sessions.get(conversation_id)
        if not session:
            return {"focus": {}, "history": []}

        return {
            "focus": session.current_focus,
            "history": [
                {
                    "question": t.question,
                    "sql": t.sql,
                    "count": t.result_count
                }
                for t in session.turns[-3:]
            ]
        }

    def clear_session(self, conversation_id: str):
        """
        Clear conversation session

        Args:
            conversation_id: Session identifier to clear
        """
        if conversation_id in self._sessions:
            del self._sessions[conversation_id]


# Singleton instance
_conversation_service: Optional[ConversationService] = None


def get_conversation_service() -> ConversationService:
    """
    Get global conversation service instance

    Returns:
        ConversationService singleton
    """
    global _conversation_service
    if _conversation_service is None:
        _conversation_service = ConversationService()
    return _conversation_service
