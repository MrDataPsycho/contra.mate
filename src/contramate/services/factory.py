"""Base class for all services with factory pattern support."""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic
from pathlib import Path

T = TypeVar('T')


class ServiceFactoryABC(ABC, Generic[T]):
    """
    Abstract base class for all services in the application.

    This class enforces a factory pattern where each service must implement
    a create_default() class method for standardized service instantiation.
    """

    @classmethod
    @abstractmethod
    def create_default(cls) -> T:
        """
        Create a default instance of the service with standard configuration.

        This factory method should initialize the service with default settings
        from the application configuration, ensuring consistent service creation
        across the application.

        Returns:
            T: Configured instance of the service

        Raises:
            NotImplementedError: If subclass doesn't implement this method
        """
        raise NotImplementedError("Subclasses must implement create_default() factory method")
    
    @classmethod
    def from_env_file(cls, env_path: str | Path) -> T:
        """
        Create an instance of the service using settings from a specific environment file.

        This factory method allows for service instantiation with configurations
        loaded from a designated .env file, facilitating environment-specific setups.

        Args:
            env_path (str): Path to the .env file to load settings from.

        Returns:
            T: Configured instance of the service

        Raises:
            NotImplementedError: If subclass doesn't implement this method
        """
        raise NotImplementedError("Subclasses must implement from_env_file() factory method")
