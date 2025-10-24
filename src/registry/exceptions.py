"""
Registry-related exceptions

Provides a hierarchy of exceptions for different registry failure modes,
enabling precise error handling in client code.
"""


class RegistryError(Exception):
    """Base exception for registry operations"""

    pass


class RegistryConnectionError(RegistryError):
    """Registry connection failed"""

    pass


class RegistryValidationError(RegistryError):
    """Response validation failed"""

    pass
