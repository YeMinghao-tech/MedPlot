"""Base Transform interface for chunk processing."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from src.core.types import Chunk


class BaseTransform(ABC):
    """Abstract base class for chunk transformers."""

    @abstractmethod
    def transform(self, chunks: List[Chunk], trace: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """Transform a list of chunks.

        Args:
            chunks: List of chunks to transform.
            trace: Optional trace context for logging.

        Returns:
            List of transformed chunks.
        """
        pass

    def _update_trace(self, trace: Optional[Dict[str, Any]], stage: str, info: Any) -> None:
        """Update trace with stage information.

        Args:
            trace: Trace context dict.
            stage: Stage name.
            info: Stage information.
        """
        if trace is not None:
            if "stages" not in trace:
                trace["stages"] = []
            trace["stages"].append({"stage": stage, "info": info})
