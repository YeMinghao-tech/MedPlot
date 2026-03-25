"""Evaluation runner for running test sets and generating reports.

Implements K1, K4: Golden Test Set loading and EvalRunner with metrics report.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.evaluator import (
    BaseEvaluator,
    CompositeEvaluator,
    EvaluationResult,
)


@dataclass
class TestCase:
    """A single test case in the golden test set."""

    id: str
    category: str  # "medical_knowledge", "symptom_to_dept", "record_generation", "booking"
    question: str
    ground_truth: Optional[str] = None
    contexts: List[str] = field(default_factory=list)
    expected_intent: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationReport:
    """Report of a complete evaluation run."""

    timestamp: str
    total_cases: int
    passed_cases: int
    failed_cases: int
    overall_score: float
    threshold: float
    passed: bool
    category_results: Dict[str, Dict[str, Any]]
    case_results: List[Dict[str, Any]]
    recommendations: List[str]


class GoldenTestSet:
    """Golden test set for evaluation.

    Implements K1: Golden test set construction.
    """

    def __init__(self, test_set_path: Optional[str] = None):
        """Initialize golden test set.

        Args:
            test_set_path: Optional path to JSON test set file.
        """
        self.test_cases: List[TestCase] = []
        if test_set_path:
            self.load_from_file(test_set_path)

    def load_from_file(self, path: str):
        """Load test set from JSON file.

        Args:
            path: Path to test set JSON file.
        """
        with open(path) as f:
            data = json.load(f)

        self.test_cases = [
            TestCase(
                id=tc["id"],
                category=tc["category"],
                question=tc["question"],
                ground_truth=tc.get("ground_truth"),
                contexts=tc.get("contexts", []),
                expected_intent=tc.get("expected_intent"),
                metadata=tc.get("metadata", {}),
            )
            for tc in data.get("test_cases", [])
        ]

    def add_case(self, case: TestCase):
        """Add a test case.

        Args:
            case: TestCase to add.
        """
        self.test_cases.append(case)

    def get_by_category(self, category: str) -> List[TestCase]:
        """Get test cases by category.

        Args:
            category: Category to filter by.

        Returns:
            List of matching test cases.
        """
        return [tc for tc in self.test_cases if tc.category == category]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "test_cases": [
                {
                    "id": tc.id,
                    "category": tc.category,
                    "question": tc.question,
                    "ground_truth": tc.ground_truth,
                    "contexts": tc.contexts,
                    "expected_intent": tc.expected_intent,
                    "metadata": tc.metadata,
                }
                for tc in self.test_cases
            ]
        }


class EvalRunner:
    """Runner for executing evaluations on golden test sets.

    Implements K4: Load golden test set, run evaluators, output metrics report.
    """

    def __init__(
        self,
        evaluator: BaseEvaluator = None,
        golden_set: GoldenTestSet = None,
    ):
        """Initialize eval runner.

        Args:
            evaluator: Evaluator to use (default: CompositeEvaluator).
            golden_set: Golden test set to evaluate against.
        """
        self.evaluator = evaluator or CompositeEvaluator()
        self.golden_set = golden_set or GoldenTestSet()

    def run(
        self,
        answers: Dict[str, str] = None,  # question_id -> answer
        contexts: Dict[str, List[str]] = None,  # question_id -> contexts
    ) -> EvaluationReport:
        """Run evaluation on all test cases.

        Args:
            answers: Dict mapping question_id to generated answer.
            contexts: Dict mapping question_id to retrieved contexts.

        Returns:
            EvaluationReport with metrics and recommendations.
        """
        answers = answers or {}
        contexts = contexts or {}

        case_results = []
        category_stats: Dict[str, Dict[str, Any]] = {}
        all_passed = True

        for case in self.golden_set.test_cases:
            answer = answers.get(case.id, "")
            ctx = contexts.get(case.id, case.contexts)

            result = self.evaluator.evaluate(
                question=case.question,
                answer=answer,
                contexts=ctx,
                ground_truth=case.ground_truth,
            )

            case_result = {
                "id": case.id,
                "category": case.category,
                "question": case.question[:50] + "..." if len(case.question) > 50 else case.question,
                "score": result.score,
                "passed": result.passed,
                "reasoning": result.reasoning,
                "details": result.details,
            }
            case_results.append(case_result)

            # Aggregate by category
            if case.category not in category_stats:
                category_stats[case.category] = {"total": 0, "passed": 0, "scores": []}

            category_stats[case.category]["total"] += 1
            category_stats[case.category]["scores"].append(result.score)
            if result.passed:
                category_stats[case.category]["passed"] += 1
            else:
                all_passed = False

        # Calculate overall score
        total_cases = len(case_results)
        passed_cases = sum(1 for r in case_results if r["passed"])
        failed_cases = total_cases - passed_cases
        overall_score = sum(r["score"] for r in case_results) / total_cases if total_cases else 0.0

        # Build category results
        category_results = {}
        for cat, stats in category_stats.items():
            avg_score = sum(stats["scores"]) / len(stats["scores"]) if stats["scores"] else 0.0
            category_results[cat] = {
                "total": stats["total"],
                "passed": stats["passed"],
                "failed": stats["total"] - stats["passed"],
                "pass_rate": stats["passed"] / stats["total"] if stats["total"] > 0 else 0.0,
                "avg_score": avg_score,
            }

        # Generate recommendations
        recommendations = self._generate_recommendations(category_results, case_results)

        return EvaluationReport(
            timestamp=datetime.now().isoformat(),
            total_cases=total_cases,
            passed_cases=passed_cases,
            failed_cases=failed_cases,
            overall_score=overall_score,
            threshold=self.evaluator.threshold,
            passed=all_passed and overall_score >= self.evaluator.threshold,
            category_results=category_results,
            case_results=case_results,
            recommendations=recommendations,
        )

    def _generate_recommendations(
        self,
        category_results: Dict[str, Dict[str, Any]],
        case_results: List[Dict[str, Any]],
    ) -> List[str]:
        """Generate recommendations based on evaluation results."""
        recommendations = []

        # Check each category
        for cat, stats in category_results.items():
            if stats["pass_rate"] < 0.8:
                recommendations.append(
                    f"类别 '{cat}' 通过率仅 {stats['pass_rate']:.0%}，需要改进"
                )

        # Find worst performing cases
        failed_cases = [c for c in case_results if not c["passed"]]
        if failed_cases:
            worst = min(failed_cases, key=lambda c: c["score"])
            recommendations.append(
                f"最低分案例：{worst['id']} (得分 {worst['score']:.2f})，问题：{worst['question']}"
            )

        # Check for specific issues
        low_faithfulness = [
            c for c in case_results
            if c["details"].get("faithfulness", 1.0) < 0.7
        ]
        if low_faithfulness:
            recommendations.append(
                f"发现 {len(low_faithfulness)} 个可能存在幻觉的案例"
            )

        return recommendations[:5]  # Limit to top 5

    def save_report(self, report: EvaluationReport, output_path: str):
        """Save evaluation report to JSON file.

        Args:
            report: EvaluationReport to save.
            output_path: Path to output JSON file.
        """
        report_dict = {
            "timestamp": report.timestamp,
            "summary": {
                "total_cases": report.total_cases,
                "passed_cases": report.passed_cases,
                "failed_cases": report.failed_cases,
                "overall_score": report.overall_score,
                "threshold": report.threshold,
                "passed": report.passed,
            },
            "category_results": report.category_results,
            "case_results": report.case_results,
            "recommendations": report.recommendations,
        }

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(report_dict, f, ensure_ascii=False, indent=2)


# Default golden test set data
DEFAULT_GOLDEN_TEST_SET = {
    "test_cases": [
        {
            "id": "kb_001",
            "category": "medical_knowledge",
            "question": "请问心脏病是什么？",
            "ground_truth": "心脏病是心脏功能异常或结构异常引起的疾病。",
            "contexts": [
                "心脏病是由心脏功能异常引起的疾病，包括冠心病、心肌炎、心包炎等。",
                "常见症状包括胸痛、呼吸困难、心悸等。",
            ],
        },
        {
            "id": "kb_002",
            "category": "medical_knowledge",
            "question": "高血压的诊断标准是什么？",
            "ground_truth": "收缩压≥140mmHg或舒张压≥90mmHg。",
            "contexts": [
                "高血压的诊断标准为收缩压≥140mmHg，舒张压≥90mmHg。",
            ],
        },
        {
            "id": "symptom_001",
            "category": "symptom_to_dept",
            "question": "我发烧三天了，还咳嗽，应该挂什么科？",
            "expected_intent": "APPOINTMENT_BOOKING",
            "contexts": ["发烧、咳嗽属内科症状。"],
        },
        {
            "id": "symptom_002",
            "category": "symptom_to_dept",
            "question": "我胸痛非常严重，放射到左肩",
            "expected_intent": "RED_FLAG",
            "contexts": ["胸痛放射是心脏病急症信号。"],
        },
        {
            "id": "booking_001",
            "category": "booking",
            "question": "我想挂号看内科",
            "expected_intent": "APPOINTMENT_BOOKING",
            "contexts": [],
        },
    ]
}


def get_default_golden_set() -> GoldenTestSet:
    """Get the default golden test set.

    Returns:
        GoldenTestSet with default medical evaluation cases.
    """
    golden_set = GoldenTestSet()
    for tc_data in DEFAULT_GOLDEN_TEST_SET["test_cases"]:
        golden_set.add_case(TestCase(**tc_data))
    return golden_set
