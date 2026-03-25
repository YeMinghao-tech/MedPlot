"""Tests for batch processor."""

from src.ingestion.embedding.batch_processor import BatchProcessor


class TestBatchProcessor:
    """Test BatchProcessor functionality."""

    def test_process_single_batch(self):
        """Test processing items that fit in one batch."""
        processor = BatchProcessor(batch_size=10)
        items = [1, 2, 3, 4, 5]
        func = lambda batch: [x * 2 for x in batch]

        result = processor.process(items, func)

        assert result == [2, 4, 6, 8, 10]

    def test_process_multiple_batches(self):
        """Test processing items that span multiple batches."""
        processor = BatchProcessor(batch_size=3)
        items = [1, 2, 3, 4, 5, 6, 7]
        func = lambda batch: [x * 2 for x in batch]

        result = processor.process(items, func)

        assert result == [2, 4, 6, 8, 10, 12, 14]

    def test_process_preserves_order(self):
        """Test that processing preserves item order."""
        processor = BatchProcessor(batch_size=2)
        items = ["a", "b", "c", "d", "e"]
        func = lambda batch: [x.upper() for x in batch]

        result = processor.process(items, func)

        assert result == ["A", "B", "C", "D", "E"]

    def test_process_empty_list(self):
        """Test processing empty list."""
        processor = BatchProcessor(batch_size=10)
        func = lambda batch: [x * 2 for x in batch]

        result = processor.process([], func)

        assert result == []

    def test_process_with_callback(self):
        """Test processing with progress callback."""
        processor = BatchProcessor(batch_size=3)
        items = [1, 2, 3, 4, 5, 6]
        func = lambda batch: [x * 2 for x in batch]

        progress_calls = []

        def callback(completed, total):
            progress_calls.append((completed, total))

        result = processor.process_with_callback(items, func, callback)

        assert result == [2, 4, 6, 8, 10, 12]
        assert len(progress_calls) == 2
        assert progress_calls[0] == (3, 6)
        assert progress_calls[1] == (6, 6)

    def test_process_with_callback_final_progress(self):
        """Test that callback reports final progress correctly."""
        processor = BatchProcessor(batch_size=10)
        items = [1, 2, 3]
        func = lambda batch: [x * 2 for x in batch]

        progress_calls = []

        def callback(completed, total):
            progress_calls.append((completed, total))

        processor.process_with_callback(items, func, callback)

        assert progress_calls[-1] == (3, 3)

    def test_batch_size_customization(self):
        """Test custom batch size."""
        processor = BatchProcessor(batch_size=5)
        items = list(range(12))
        func = lambda batch: [len(batch)]  # Returns batch length as list

        result = processor.process(items, func)

        # 12 items with batch_size 5: [5, 5, 2]
        assert result == [5, 5, 2]
