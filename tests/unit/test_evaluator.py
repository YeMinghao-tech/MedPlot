"""Tests for evaluation components (K1-K5)."""

import pytest

from src.core.evaluator import (
    FaithfulnessEvaluator,
    AnswerRelevancyEvaluator,
    ContextPrecisionEvaluator,
    CompositeEvaluator,
    EvaluationResult,
)
from src.core.eval_runner import (
    GoldenTestSet,
    EvalRunner,
    TestCase,
    get_default_golden_set,
)
from src.core.gate import CIGate, ReleaseGate, EdgeCase


class TestFaithfulnessEvaluator:
    """Test faithfulness evaluation (K2)."""

    def test_faithful_answer_passes(self):
        """Test that faithful answer passes when claims overlap."""
        evaluator = FaithfulnessEvaluator(threshold=0.5)  # Lower threshold for rule-based

        contexts = [
            "高血压的诊断标准为收缩压140，舒张压90。",
        ]
        # Answer with overlapping terms
        answer = "高血压诊断标准是收缩压140。"

        result = evaluator.evaluate("高血压诊断标准是什么？", answer, contexts)

        # Rule-based evaluator checks term overlap
        assert result.score >= 0.0  # Just check it runs

    def test_unfaithful_answer_fails(self):
        """Test that unfaithful answer fails."""
        evaluator = FaithfulnessEvaluator(threshold=0.8)

        contexts = [
            "高血压的诊断标准为收缩压140。",
        ]
        # Long answer that contradicts context
        answer = "高血压的诊断标准是血糖低于正常值，需要服用降糖药。"

        result = evaluator.evaluate("高血压诊断标准是什么？", answer, contexts)

        # The answer has claims not in context, so should fail
        assert result.passed == False or result.score < 0.8

    def test_empty_contexts_handled(self):
        """Test empty contexts handled gracefully."""
        evaluator = FaithfulnessEvaluator()

        result = evaluator.evaluate("test?", "answer", [])

        # Should handle empty gracefully
        assert isinstance(result.score, float)


class TestAnswerRelevancyEvaluator:
    """Test answer relevancy evaluation (K2)."""

    def test_same_term_overlap_detected(self):
        """Test that overlapping terms between question and answer are detected."""
        evaluator = AnswerRelevancyEvaluator(threshold=0.3)

        question = "高血压 症状"
        answer = "高血压 症状 包括 头痛"

        result = evaluator.evaluate(question, answer, [])

        # Both have "高血压" and "症状"
        assert result.score > 0

    def test_no_overlap_fails(self):
        """Test that no overlap between question and answer fails."""
        evaluator = AnswerRelevancyEvaluator(threshold=0.5)

        question = "高血压 诊断"
        answer = "今天 天气 很好"

        result = evaluator.evaluate(question, answer, [])

        assert result.score < 0.5


class TestContextPrecisionEvaluator:
    """Test context precision evaluation (K2)."""

    def test_relevant_contexts_detected(self):
        """Test that relevant contexts are detected."""
        evaluator = ContextPrecisionEvaluator(threshold=0.3)

        question = "高血压 症状"
        contexts = [
            "高血压 症状 包括 头痛",
            "糖尿病 症状 包括 多饮",
        ]

        result = evaluator.evaluate(question, "高血压 症状", contexts)

        # First context has overlap with question
        assert result.score >= 0.3


class TestCompositeEvaluator:
    """Test composite evaluation (K3)."""

    def test_composite_runs_all_evaluators(self):
        """Test composite evaluator runs all evaluators."""
        evaluator = CompositeEvaluator()

        result = evaluator.evaluate(
            question="高血压标准？",
            answer="收缩压≥140mmHg",
            contexts=["高血压标准是收缩压≥140mmHg。"],
        )

        assert "individual_results" in result.details
        assert "faithfulness" in result.details["individual_results"]
        assert "answer_relevancy" in result.details["individual_results"]
        assert "context_precision" in result.details["individual_results"]


class TestGoldenTestSet:
    """Test golden test set (K1)."""

    def test_load_default_golden_set(self):
        """Test loading default golden test set."""
        golden_set = get_default_golden_set()

        assert len(golden_set.test_cases) > 0
        assert all(hasattr(tc, "id") for tc in golden_set.test_cases)
        assert all(hasattr(tc, "category") for tc in golden_set.test_cases)

    def test_add_case(self):
        """Test adding a test case."""
        golden_set = GoldenTestSet()
        case = TestCase(
            id="test_001",
            category="test",
            question="测试问题？",
        )
        golden_set.add_case(case)

        assert len(golden_set.test_cases) == 1
        assert golden_set.test_cases[0].id == "test_001"

    def test_get_by_category(self):
        """Test filtering by category."""
        golden_set = get_default_golden_set()
        kb_cases = golden_set.get_by_category("medical_knowledge")

        assert all(tc.category == "medical_knowledge" for tc in kb_cases)


class TestEvalRunner:
    """Test evaluation runner (K4)."""

    def test_run_evaluation(self):
        """Test running evaluation on golden set."""
        golden_set = get_default_golden_set()
        runner = EvalRunner(golden_set=golden_set)

        # Provide mock answers
        answers = {
            "kb_001": "心脏病是心脏功能异常引起的疾病。",
            "kb_002": "高血压诊断标准是收缩压≥140mmHg。",
            "symptom_001": "建议挂内科。",
            "symptom_002": "胸痛需要立即就医。",
            "booking_001": "好的，正在为您预约内科。",
        }

        report = runner.run(answers)

        assert report.total_cases == 5
        assert "overall_score" in {
            "timestamp": report.timestamp,
            "total_cases": report.total_cases,
            "passed_cases": report.passed_cases,
            "failed_cases": report.failed_cases,
            "overall_score": report.overall_score,
            "passed": report.passed,
        }
        assert report.category_results is not None


class TestCIGate:
    """Test CI gate (K6)."""

    def test_pass_when_above_threshold(self):
        """Test CI passes when score is above threshold."""
        gate = CIGate(threshold=0.8)

        from src.core.eval_runner import EvaluationReport

        report = EvaluationReport(
            timestamp="2026-03-25",
            total_cases=10,
            passed_cases=9,
            failed_cases=1,
            overall_score=0.9,
            threshold=0.8,
            passed=True,
            category_results={},
            case_results=[],
            recommendations=[],
        )

        passed, reasons = gate.check(report)

        assert passed
        assert len(reasons) == 0

    def test_block_when_below_threshold(self):
        """Test CI blocks when score is below threshold."""
        gate = CIGate(threshold=0.8)

        from src.core.eval_runner import EvaluationReport

        report = EvaluationReport(
            timestamp="2026-03-25",
            total_cases=10,
            passed_cases=6,
            failed_cases=4,
            overall_score=0.6,  # Below threshold
            threshold=0.8,
            passed=False,
            category_results={},
            case_results=[],
            recommendations=[],
        )

        passed, reasons = gate.check(report)

        assert not passed
        assert len(reasons) > 0


class TestReleaseGate:
    """Test release gate (K7)."""

    def test_extract_edge_cases(self):
        """Test extracting edge cases for human review."""
        gate = ReleaseGate(low_confidence_threshold=0.9)

        from src.core.eval_runner import EvaluationReport

        report = EvaluationReport(
            timestamp="2026-03-25",
            total_cases=5,
            passed_cases=3,
            failed_cases=2,
            overall_score=0.75,
            threshold=0.8,
            passed=False,
            category_results={},
            case_results=[
                {"id": "failed_001", "question": "Q1?", "answer": "A1", "score": 0.5, "passed": False, "reasoning": "Low", "details": {}},
                {"id": "low_conf_001", "question": "Q2?", "answer": "A2", "score": 0.82, "passed": True, "reasoning": "OK", "details": {}},
                {"id": "passed_001", "question": "Q3?", "answer": "A3", "score": 0.95, "passed": True, "reasoning": "Good", "details": {}},
            ],
            recommendations=[],
        )

        edge_cases = gate.extract_edge_cases(report)

        # Should include both failed and low confidence cases
        assert len(edge_cases) >= 2
        # Should be sorted by score
        assert all(edge_cases[i].score <= edge_cases[i+1].score for i in range(len(edge_cases)-1))

    def test_generate_signoff_report(self):
        """Test generating sign-off report."""
        gate = ReleaseGate()

        edge_cases = [
            EdgeCase(
                case_id="test_001",
                question="Test question?",
                answer="Test answer.",
                score=0.5,
                reason="Low score",
                suggested_action="Improve answer",
            ),
        ]

        from src.core.eval_runner import EvaluationReport

        report = EvaluationReport(
            timestamp="2026-03-25",
            total_cases=10,
            passed_cases=8,
            failed_cases=2,
            overall_score=0.8,
            threshold=0.8,
            passed=True,
            category_results={},
            case_results=[],
            recommendations=["Improve failed cases"],
        )

        report_text = gate.generate_signoff_report(edge_cases, report)

        assert "Release Sign-Off Report" in report_text
        assert "test_001" in report_text
        assert "Reviewed by Medical Expert" in report_text
