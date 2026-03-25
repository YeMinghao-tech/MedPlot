"""Distributed tracing context for observability."""

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from contextvars import ContextVar


# Context variable for current trace
_current_trace: ContextVar[Optional["TraceContext"]] = ContextVar(
    "current_trace", default=None
)


@dataclass
class Span:
    """A single span within a trace."""

    span_id: str
    name: str
    start_time: float
    end_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    children: List["Span"] = field(default_factory=list)
    parent_id: Optional[str] = None

    def finish(self, metadata: Optional[Dict[str, Any]] = None):
        """Finish the span.

        Args:
            metadata: Optional metadata to add before finishing.
        """
        self.end_time = time.time()
        if metadata:
            self.metadata.update(metadata)

    @property
    def duration_ms(self) -> float:
        """Get duration in milliseconds."""
        if self.end_time is None:
            return (time.time() - self.start_time) * 1000
        return (self.end_time - self.start_time) * 1000


@dataclass
class TraceContext:
    """Distributed tracing context for a single request.

    Implements J1: trace_id generation, phase recording, finish summary.
    """

    trace_id: str
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    root_span: Optional[Span] = None
    spans: List[Span] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    _current_span: Optional[Span] = None

    def __post_init__(self):
        """Initialize trace context."""
        if self.trace_id is None:
            self.trace_id = str(uuid.uuid4())[:16]

    @classmethod
    def create(cls, trace_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> "TraceContext":
        """Create a new trace context.

        Args:
            trace_id: Optional trace ID. Generated if not provided.
            metadata: Optional metadata to attach to trace.

        Returns:
            New TraceContext instance.
        """
        ctx = cls(
            trace_id=trace_id or str(uuid.uuid4())[:16],
            metadata=metadata or {},
        )
        ctx.root_span = Span(
            span_id=f"{ctx.trace_id}-root",
            name="root",
            start_time=ctx.start_time,
        )
        ctx._current_span = ctx.root_span
        _current_trace.set(ctx)
        return ctx

    @classmethod
    def get_current(cls) -> Optional["TraceContext"]:
        """Get the current trace context.

        Returns:
            Current TraceContext or None if not in a traced context.
        """
        return _current_trace.get()

    def start_span(
        self,
        name: str,
        parent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Span:
        """Start a new span within this trace.

        Args:
            name: Name of the span (e.g., "intent_classification").
            parent_id: Parent span ID. Uses current span if not provided.
            metadata: Optional metadata for the span.

        Returns:
            New Span instance.
        """
        parent = self._current_span
        if parent_id:
            parent = self._find_span(parent_id)

        span = Span(
            span_id=f"{self.trace_id}-{name}-{len(self.spans)}",
            name=name,
            start_time=time.time(),
            parent_id=parent.span_id if parent else None,
            metadata=metadata or {},
        )

        if parent:
            parent.children.append(span)

        self.spans.append(span)
        self._current_span = span

        return span

    def _find_span(self, span_id: str) -> Optional[Span]:
        """Find a span by ID."""
        if self.root_span and self.root_span.span_id == span_id:
            return self.root_span
        for span in self.spans:
            if span.span_id == span_id:
                return span
        return None

    def end_span(self, span: Span, metadata: Optional[Dict[str, Any]] = None):
        """End a span.

        Args:
            span: The span to end.
            metadata: Optional metadata to add before ending.
        """
        span.finish(metadata)

        # Restore to parent
        if span.parent_id:
            self._current_span = self._find_span(span.parent_id)
        else:
            self._current_span = self.root_span

    def finish(self, metadata: Optional[Dict[str, Any]] = None):
        """Finish the trace.

        Args:
            metadata: Optional metadata to add to trace.
        """
        self.end_time = time.time()
        if metadata:
            self.metadata.update(metadata)

        if self.root_span and self.root_span.end_time is None:
            self.root_span.finish()

        _current_trace.set(None)

    def to_dict(self) -> Dict[str, Any]:
        """Convert trace to dictionary for JSON serialization.

        Returns:
            Dictionary representation of trace.
        """
        return {
            "trace_id": self.trace_id,
            "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
            "end_time": datetime.fromtimestamp(self.end_time).isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
            "spans": [self._span_to_dict(s) for s in self.spans],
        }

    def _span_to_dict(self, span: Span) -> Dict[str, Any]:
        """Convert span to dictionary."""
        return {
            "span_id": span.span_id,
            "name": span.name,
            "parent_id": span.parent_id,
            "start_time": datetime.fromtimestamp(span.start_time).isoformat(),
            "end_time": datetime.fromtimestamp(span.end_time).isoformat() if span.end_time else None,
            "duration_ms": span.duration_ms,
            "metadata": span.metadata,
            "children": [self._span_to_dict(c) for c in span.children],
        }

    @property
    def duration_ms(self) -> float:
        """Get total duration in milliseconds."""
        if self.end_time is None:
            return (time.time() - self.start_time) * 1000
        return (self.end_time - self.start_time) * 1000


def get_current_trace() -> Optional[TraceContext]:
    """Get the current trace context.

    Returns:
        Current TraceContext or None.
    """
    return _current_trace.get()


def traced(
    name: str,
    metadata: Optional[Dict[str, Any]] = None,
):
    """Decorator for tracing a function.

    Args:
        name: Name of the span.
        metadata: Optional metadata.

    Usage:
        @traced("my_function")
        def my_function():
            pass
    """
    import functools

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            trace = get_current_trace()
            if trace:
                span = trace.start_span(name, metadata=metadata)
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    trace.end_span(span)
            else:
                return func(*args, **kwargs)

        return wrapper

    return decorator
