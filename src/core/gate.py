"""CI/Release gates for evaluation.

Implements K6-K7: CI automated gate and Release manual gate.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from src.core.eval_runner import EvaluationReport


@dataclass
class EdgeCase:
    """An edge case requiring human attention."""

    case_id: str
    question: str
    answer: str
    score: float
    reason: str
    suggested_action: str
    status: str = "pending"  # "pending", "approved", "rejected"


class CIGate:
    """CI automated gate for pull request evaluation.

    Implements K6: PR stage auto-run evaluation, block if below threshold.
    """

    def __init__(
        self,
        threshold: float = 0.8,
        critical_categories: List[str] = None,
    ):
        """Initialize CI gate.

        Args:
            threshold: Minimum score to pass CI.
            critical_categories: Categories that must pass (e.g., ["symptom_to_dept"]).
        """
        self.threshold = threshold
        self.critical_categories = critical_categories or ["symptom_to_dept", "booking"]

    def check(self, report: EvaluationReport) -> tuple[bool, List[str]]:
        """Check if CI gate passes.

        Args:
            report: EvaluationReport from EvalRunner.

        Returns:
            Tuple of (passed, reasons).
        """
        reasons = []
        passed = True

        # Check overall score
        if report.overall_score < self.threshold:
            passed = False
            reasons.append(
                f"Overall score {report.overall_score:.2f} < threshold {self.threshold}"
            )

        # Check critical categories
        for cat in self.critical_categories:
            if cat in report.category_results:
                cat_stats = report.category_results[cat]
                if cat_stats["pass_rate"] < 0.9:  # 90% pass rate for critical
                    passed = False
                    reasons.append(
                        f"Critical category '{cat}' pass rate {cat_stats['pass_rate']:.0%} < 90%"
                    )

        # Check for regressions (if previous report exists)
        regression_issues = self._check_regressions(report)
        if regression_issues:
            passed = False
            reasons.extend(regression_issues)

        return passed, reasons

    def _check_regressions(
        self,
        report: EvaluationReport,
        baseline_path: str = "data/eval/baseline.json",
    ) -> List[str]:
        """Check for regressions against baseline.

        Args:
            report: Current evaluation report.
            baseline_path: Path to baseline report JSON.

        Returns:
            List of regression issues.
        """
        if not Path(baseline_path).exists():
            return []

        issues = []
        with open(baseline_path) as f:
            baseline = json.load(f)

        baseline_scores = baseline.get("summary", {})
        current_scores = {
            "overall_score": report.overall_score,
            "total_cases": report.total_cases,
        }

        # Check for significant score drop (>5%)
        baseline_overall = baseline_scores.get("overall_score", 1.0)
        if report.overall_score < baseline_overall - 0.05:
            issues.append(
                f"Regression: overall score dropped from {baseline_overall:.2f} to {report.overall_score:.2f}"
            )

        return issues

    def get_blocking_cases(self, report: EvaluationReport) -> List[EdgeCase]:
        """Get cases that are blocking CI.

        Args:
            report: EvaluationReport.

        Returns:
            List of EdgeCases that need attention.
        """
        blocking = []

        for case in report.case_results:
            if not case["passed"] and case["score"] < self.threshold:
                edge_case = EdgeCase(
                    case_id=case["id"],
                    question=case["question"],
                    answer=case.get("answer", ""),
                    score=case["score"],
                    reason=case["reasoning"],
                    suggested_action=f"Improve answer to reach {self.threshold} threshold",
                )
                blocking.append(edge_case)

        return blocking


class ReleaseGate:
    """Release manual gate for human sign-off.

    Implements K7: Extract low-confidence edge cases for human review.
    """

    def __init__(self, low_confidence_threshold: float = 0.85):
        """Initialize release gate.

        Args:
            low_confidence_threshold: Score below which cases need human review.
        """
        self.low_confidence_threshold = low_confidence_threshold

    def extract_edge_cases(
        self,
        report: EvaluationReport,
        max_cases: int = 10,
    ) -> List[EdgeCase]:
        """Extract edge cases for human review.

        Args:
            report: EvaluationReport.
            max_cases: Maximum number of edge cases to extract.

        Returns:
            List of EdgeCases requiring human sign-off.
        """
        edge_cases = []

        # Failed cases always need attention
        for case in report.case_results:
            if not case["passed"]:
                edge_case = EdgeCase(
                    case_id=case["id"],
                    question=case["question"],
                    answer=case.get("answer", ""),
                    score=case["score"],
                    reason=f"Failed with score {case['score']:.2f}",
                    suggested_action=self._get_suggested_action(case),
                )
                edge_cases.append(edge_case)

        # Low confidence cases (borderline)
        for case in report.case_results:
            if case["passed"] and case["score"] < self.low_confidence_threshold:
                edge_case = EdgeCase(
                    case_id=case["id"],
                    question=case["question"],
                    answer=case.get("answer", ""),
                    score=case["score"],
                    reason=f"Low confidence ({case['score']:.2f})",
                    suggested_action="Review for potential issues",
                )
                edge_cases.append(edge_case)

        # Sort by score and limit
        edge_cases.sort(key=lambda e: e.score)
        return edge_cases[:max_cases]

    def _get_suggested_action(self, case: dict) -> str:
        """Get suggested action for a failed case."""
        if "faithfulness" in str(case.get("details", {})):
            return "Check for hallucination - answer may contain unsupported claims"
        if "relevancy" in str(case.get("details", {})):
            return "Review if answer addresses the question"
        return "Investigate and improve answer quality"

    def generate_signoff_report(
        self,
        edge_cases: List[EdgeCase],
        report: EvaluationReport,
    ) -> str:
        """Generate human-readable sign-off report.

        Args:
            edge_cases: List of EdgeCases.
            report: Original evaluation report.

        Returns:
            Markdown report string.
        """
        lines = [
            "# Release Sign-Off Report",
            f"Generated: {datetime.now().isoformat()}",
            "",
            f"## Summary",
            f"- Total cases evaluated: {report.total_cases}",
            f"- Passed: {report.passed_cases}",
            f"- Failed: {report.failed_cases}",
            f"- Overall score: {report.overall_score:.2f}",
            "",
            f"## Edge Cases Requiring Review ({len(edge_cases)})",
            "",
        ]

        for i, ec in enumerate(edge_cases, 1):
            lines.append(f"### {i}. {ec.case_id} (Score: {ec.score:.2f})")
            lines.append(f"- **Question**: {ec.question}")
            lines.append(f"- **Answer**: {ec.answer[:200]}..." if len(ec.answer) > 200 else f"- **Answer**: {ec.answer}")
            lines.append(f"- **Reason**: {ec.reason}")
            lines.append(f"- **Suggested Action**: {ec.suggested_action}")
            lines.append(f"- **Status**: {ec.status}")
            lines.append("")

        lines.append("## Approval")
        lines.append("")
        lines.append("- [ ] Reviewed by Medical Expert: _______")
        lines.append("- [ ] Approved for Release: _______")
        lines.append("")

        return "\n".join(lines)
