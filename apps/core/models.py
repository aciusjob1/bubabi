import uuid
from django.db import models


class BaseModel(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ImmutableModel(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self._state.adding is False:
            from apps.core.exceptions import ImmutableRecordError
            raise ImmutableRecordError(
                f"{self.__class__.__name__} cannot be modified."
            )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        from apps.core.exceptions import ImmutableRecordError
        raise ImmutableRecordError(
            f"{self.__class__.__name__} cannot be deleted."
        )