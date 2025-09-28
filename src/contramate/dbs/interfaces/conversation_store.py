from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from contramate.dbs.models.conversation import FeedbackType


class AbstractConversationRepository(ABC):
    @abstractmethod
    async def create_conversation(
        self, 
        user_id: str, 
        title: str = "", 
        conversation_id: Optional[str] = None,
        filter_values: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def get_conversations(
        self,
        user_id: str,
        limit: int = 10,
        last_evaluated_key: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def get_conversation_by_id(self, user_id: str, conversation_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    async def delete_conversation(self, user_id: str, conversation_id: str) -> None:
        pass

    @abstractmethod
    async def create_message(
        self, 
        user_id: str, 
        conversation_id: str, 
        role: str, 
        content: str, 
        feedback: str = "", 
        message_id: Optional[str] = None,
        filter_value: Optional[Dict[str, Any]] = None,
        is_user_filter_text: bool = False
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def get_messages(self, user_id: str, conversation_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def delete_conversation_and_messages(self, user_id: str, conversation_id: str) -> bool:
        pass

    @abstractmethod
    async def get_conversations_last_90_days(
        self,
        user_id: str,
        limit: int = 100,
        last_evaluated_key: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def update_message_feedback(
        self,
        message_id: str,
        conversation_id: str,
        user_id: str,
        feedback: FeedbackType,
    ) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    async def update_conversation_title(self, user_id: str, conversation_id: str, title: str) -> bool:
        pass

    @abstractmethod
    async def update_conversation_filters(
        self, 
        user_id: str, 
        conversation_id: str, 
        filter_values: Optional[Dict[str, Any]] = None
    ) -> bool:
        pass

    @abstractmethod
    async def touch_conversation(self, user_id: str, conversation_id: str) -> bool:
        pass

    @abstractmethod
    async def update_conversation_status(
        self,
        user_id: str,
        conversation_id: str,
        is_active: bool,
    ) -> None:
        pass
