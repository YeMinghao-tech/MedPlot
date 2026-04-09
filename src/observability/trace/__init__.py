"""Distributed tracing for observability.

Exports:
    TraceContext: Main trace context for request tracking.
    Span: Individual span within a trace.
    get_current_trace: Get current trace from context.
    traced: Decorator for tracing functions.
"""

from src.core.trace import (
    TraceContext,
    Span,
    get_current_trace,
    traced,
)

__all__ = [
    "TraceContext",
    "Span",
    "get_current_trace",
    "traced",
]
