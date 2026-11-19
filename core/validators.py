from pathlib import Path
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator


AVATAR_EXTENSIONS = ("jpg", "jpeg", "png", "webp")
MAX_AVATAR_BYTES = 2 * 1024 * 1024


def validate_avatar_size(value):
    if value.size > MAX_AVATAR_BYTES:
        raise ValidationError("Размер аватара не должен превышать 2 МБ.")


def avatar_upload_to(instance, filename):
    return f"avatars/{uuid4().hex}{Path(filename).suffix.lower()}"


avatar_validators = [
    FileExtensionValidator(allowed_extensions=AVATAR_EXTENSIONS),
    validate_avatar_size,
]
