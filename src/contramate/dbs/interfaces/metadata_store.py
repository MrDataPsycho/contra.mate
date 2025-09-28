from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class AbstractMetadataStore(ABC):
    @abstractmethod
    async def execute_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute a SQL query and return results as list of dictionaries."""
        pass

    @abstractmethod
    async def execute_query_single(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Execute a SQL query and return single result or None."""
        pass

    @abstractmethod
    async def execute_query_scalar(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Execute a SQL query and return single scalar value."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the metadata store connection is healthy."""
        pass