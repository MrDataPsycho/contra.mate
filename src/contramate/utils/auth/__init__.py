"""Authentication utilities for Azure services"""

from .certificate_provider import get_cert_token_provider

__all__ = [
    "get_cert_token_provider",
]