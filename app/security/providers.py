"""Replaceable media-provider interfaces.

The gateway owns authentication, authorization, task lifecycle, and
provider selection. Concrete providers must not make authorization
decisions. No commercial providers are wired in this phase.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class MediaProvider(ABC):
    @abstractmethod
    def generate(self, params: dict[str, Any], task_id: str) -> dict[str, Any]:
        """Start or complete a generation. Returns provider-specific result metadata."""


class VideoProvider(MediaProvider):
    pass


class ImageProvider(MediaProvider):
    pass


class SpeechProvider(MediaProvider):
    pass


class SubtitleProvider(MediaProvider):
    pass


class PostProductionProvider(MediaProvider):
    pass


class ExistingEngineAdapter(VideoProvider):
    """Controlled adapter around the current video engine.

    Does not reimplement generation. Only routes already-authorized work.
    """

    def generate(self, params: dict[str, Any], task_id: str) -> dict[str, Any]:
        # Existing engine is invoked by the task manager; this adapter
        # is a boundary marker so future providers can be swapped here.
        return {"adapter": "existing-engine", "task_id": task_id}
