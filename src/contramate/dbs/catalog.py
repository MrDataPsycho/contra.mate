"""Database catalog containing enums and constants for database operations"""

from enum import StrEnum


class IndexName(StrEnum):
    """OpenSearch index names for different environments and purposes"""

    CONTRACTS_V1 = "contracts-v1"
    CONTRACTS_TEST = "contracts-test"
    DEFAULT = CONTRACTS_V1

    @classmethod
    def default(cls) -> str:
        """Get the default index name"""
        return cls.DEFAULT