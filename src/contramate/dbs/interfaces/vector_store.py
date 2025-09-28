from typing import Any, List
from abc import ABC, abstractmethod


# Abstract base class for vector databases
class VectorDBABC(ABC):
    @property
    @abstractmethod
    def dimension(self) -> int:
        """Property to get the dimension of the vectors used in the database."""
        pass

    @abstractmethod
    def save(self) -> None:
        """Save the database to the specified path."""
        pass

    @abstractmethod
    def load(self) -> None:
        """Load the database from the specified path."""
        pass

    @abstractmethod
    def search(self, query: str, top_k: int = 20) -> List[Any]:
        """Search for the top_k most similar vectors to the query_vector."""
        pass

    @abstractmethod
    def insert(self, documents: list[Any]) -> None:
        """Insert a new vector with associated metadata into the database."""
        pass

    @abstractmethod
    def delete(self, index_id: str) -> None:
        """Delete the vector from the database."""
        pass

    @abstractmethod
    def upsert(self, documents: list[Any]) -> None:
        """Insert a new vector with associated metadata into the database."""
        pass
