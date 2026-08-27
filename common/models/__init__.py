"""Reusable abstract base models for the project.

Each base lives in its own module. They are *abstract* — inheriting from them
never creates a table of its own; the fields are merged into the concrete
subclass.
"""

from .public_id import (
    PUBLIC_ID_ALPHABET,
    PUBLIC_ID_LENGTH,
    PublicIdModel,
    generate_public_id,
)
from .random_id import RandomIdModel
from .soft_deleted import AllObjectsManager, SoftDeletedManager, SoftDeletedModel
from .timestamped import TimeStampedModel, indian_now

__all__ = [
    "TimeStampedModel",
    "SoftDeletedModel",
    "SoftDeletedManager",
    "AllObjectsManager",
    "RandomIdModel",
    "PublicIdModel",
    "generate_public_id",
    "PUBLIC_ID_ALPHABET",
    "PUBLIC_ID_LENGTH",
    "indian_now",
]
