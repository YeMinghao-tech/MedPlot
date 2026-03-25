"""Tests for observability components (J1-J4)."""

import pytest
import time

from src.core.trace import TraceContext, get_current_trace, traced
from src.core.logging import JSONLinesHandler, AuditLogger, setup_logging


class TestTraceContext:
    """Test distributed tracing (J1)."""

    def test_create_trace(self):
        """Test trace creation."""
        trace = TraceContext.create("test-trace-001")

        assert trace.trace_id == "test-trace-001"
        assert trace.root_span is not None
        assert trace.root_span.name == "root"

    def test_trace_auto_generates_id(self):
        """Test trace auto-generates ID if not provided."""
        trace = TraceContext.create()

        assert trace.trace_id is not None
        assert len(trace.trace_id) > 0

    def test_start_and_end_span(self):
        """Test starting and ending spans."""
        trace = TraceContext.create("test-span-001")

        span = trace.start_span("test_operation")
        assert span.name == "test_operation"
        assert span.end_time is None

        trace.end_span(span)
        assert span.end_time is not None
        assert span.duration_ms >= 0

    def test_nested_spans(self):
        """Test nested span hierarchy."""
        trace = TraceContext.create("nested-test")

        parent = trace.start_span("parent")
        child = trace.start_span("child")

        assert child.parent_id == parent.span_id
        assert child in parent.children

        trace.end_span(child)
        trace.end_span(parent)

    def test_trace_to_dict(self):
        """Test trace serialization to dict."""
        trace = TraceContext.create("serialize-test")
        span = trace.start_span("op1")
        trace.end_span(span)
        trace.finish()

        result = trace.to_dict()

        assert "trace_id" in result
        assert "spans" in result
        assert "duration_ms" in result

    def test_get_current_trace(self):
        """Test getting current trace context."""
        trace = TraceContext.create("current-test")

        current = TraceContext.get_current()
        assert current is trace

        trace.finish()
        current = TraceContext.get_current()
        assert current is None

    def test_traced_decorator(self):
        """Test traced decorator."""
        @traced("my_operation")
        def my_function():
            return 42

        trace = TraceContext.create("decorator-test")
        result = my_function()
        trace.finish()

        assert result == 42
        assert len(trace.spans) == 1
        assert trace.spans[0].name == "my_operation"


class TestJSONLinesHandler:
    """Test JSON Lines logging (J2)."""

    def test_handler_creation(self, tmp_path):
        """Test JSON lines handler creation."""
        log_file = str(tmp_path / "test.jsonl")
        handler = JSONLinesHandler(log_file=log_file)

        assert handler.log_file.name == "test.jsonl"

    def test_log_entry_format(self, tmp_path):
        """Test log entry is valid JSON."""
        log_file = str(tmp_path / "test.jsonl")
        handler = JSONLinesHandler(log_file=log_file)

        import logging
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        entry = handler._format_entry(record)
        parsed = __import__("json").loads(entry)

        assert "timestamp" in parsed
        assert parsed["message"] == "Test message"
        assert parsed["level"] == "INFO"


class TestAuditLogger:
    """Test audit logging (J2)."""

    def test_audit_logger_creation(self, tmp_path):
        """Test audit logger creation."""
        audit_file = str(tmp_path / "audit.jsonl")
        logger = AuditLogger(audit_log_file=audit_file)

        assert logger.audit_log_file.name == "audit.jsonl"

    def test_anonymize_id(self):
        """Test patient ID anonymization."""
        logger = AuditLogger()

        # Normal ID: len=13, so middle = 13-4=9 stars
        anon = logger._anonymize_id("patient_12345")
        assert anon == "pa*********45"
        assert "patient_12345" not in anon

        # Short ID returns "***"
        anon = logger._anonymize_id("abc")
        assert anon == "***"

        # Empty/None ID returns "***"
        anon = logger._anonymize_id(None)
        assert anon == "***"

    def test_audit_log_entry(self, tmp_path):
        """Test audit log creates proper entry."""
        audit_file = str(tmp_path / "audit.jsonl")
        logger = AuditLogger(audit_log_file=audit_file)

        logger.log(
            action="TEST_ACTION",
            patient_id="patient_12345",
            result="SUCCESS",
        )

        with open(audit_file) as f:
            entry = f.readline()
            parsed = __import__("json").loads(entry)

        assert parsed["action"] == "TEST_ACTION"
        assert parsed["patient_id"] == "pa*********45"  # Anonymized
        assert parsed["result"] == "SUCCESS"


class TestAgentTracing:
    """Test agent tracing instrumentation (J3)."""

    def test_router_returns_trace_id(self):
        """Test that router.route returns trace_id."""
        from src.agent.planner.router import Router

        router = Router()
        result = router.route("我发烧了")

        assert "trace_id" in result
        # trace_id may be None if no trace context

    def test_router_with_trace_context(self):
        """Test router with explicit trace context."""
        from src.agent.planner.router import Router

        router = Router()
        trace = TraceContext.create("router-test")

        result = router.route("我发烧了", trace=trace)

        assert result["trace_id"] == "router-test"
        trace.finish()
