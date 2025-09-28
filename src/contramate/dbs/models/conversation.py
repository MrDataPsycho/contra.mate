"""Database models and types for Contramate"""

from enum import StrEnum


class FeedbackType(StrEnum):
    """Enumeration for message feedback types"""

    LIKE = "LIKE"
    DISLIKE = "DISLIKE"