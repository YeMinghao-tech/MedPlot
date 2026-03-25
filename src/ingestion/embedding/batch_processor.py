"""Batch processor for optimized batch API calls."""

from typing import Any, Callable, List, TypeVar

T = TypeVar("T")
R = TypeVar("R")


class BatchProcessor:
    """Processes items in batches for efficient API usage.

    Reduces API overhead by batching multiple items into single calls.
    """

    def __init__(self, batch_size: int = 32):
        """Initialize the batch processor.

        Args:
            batch_size: Number of items per batch.
        """
        self.batch_size = batch_size

    def process(
        self, items: List[T], processor_func: Callable[[List[T]], List[R]]
    ) -> List[R]:
        """Process items in batches.

        Args:
            items: List of items to process.
            processor_func: Function that processes a batch of items.
                           Must accept a list and return a list.

        Returns:
            List of processed results, preserving order.
        """
        if not items:
            return []

        results = []
        for i in range(0, len(items), self.batch_size):
            batch = items[i : i + self.batch_size]
            batch_results = processor_func(batch)
            results.extend(batch_results)

        return results

    def process_with_callback(
        self,
        items: List[T],
        processor_func: Callable[[List[T]], List[R]],
        on_progress: Callable[[int, int], None] = None,
    ) -> List[R]:
        """Process items in batches with progress callback.

        Args:
            items: List of items to process.
            processor_func: Function that processes a batch.
            on_progress: Callback function called with (completed, total).

        Returns:
            List of processed results.
        """
        if not items:
            return []

        results = []
        total = len(items)

        for i in range(0, len(items), self.batch_size):
            batch = items[i : i + self.batch_size]
            batch_results = processor_func(batch)
            results.extend(batch_results)

            if on_progress:
                completed = min(i + self.batch_size, total)
                on_progress(completed, total)

        return results
