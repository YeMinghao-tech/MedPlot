"""Evaluation framework for RAG quality assessment.

Implements K2-K5: Evaluators for Faithfulness, Answer Relevancy, Context Precision.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import re


@dataclass
class EvaluationResult:
    """Result of an evaluation run."""

    metric_name: str
    score: float  # 0.0 - 1.0
    threshold: float
    passed: bool
    details: Dict[str, Any]
    reasoning: str = ""


class BaseEvaluator(ABC):
    """Base class for all evaluators."""

    def __init__(self, threshold: float = 0.7):
        """Initialize evaluator.

        Args:
            threshold: Minimum score to pass (0.0 - 1.0).
        """
        self.threshold = threshold

    @abstractmethod
    def evaluate(
        self,
        question: str,
        answer: str,
        contexts: List[str],
        ground_truth: Optional[str] = None,
    ) -> EvaluationResult:
        """Evaluate an answer.

        Args:
            question: The original question.
            answer: The generated answer.
            contexts: Retrieved context chunks.
            ground_truth: Optional ground truth answer.

        Returns:
            EvaluationResult with score and details.
        """
        pass

    def _normalize_score(self, score: float) -> float:
        """Normalize score to 0.0-1.0 range."""
        return max(0.0, min(1.0, score))


class FaithfulnessEvaluator(BaseEvaluator):
    """Evaluates faithfulness - whether answer is supported by context.

    Implements K2: Faithfulness metric.
    """

    def __init__(self, threshold: float = 0.8):
        super().__init__(threshold)

    def evaluate(
        self,
        question: str,
        answer: str,
        contexts: List[str],
        ground_truth: Optional[str] = None,
    ) -> EvaluationResult:
        """Evaluate faithfulness.

        Faithfulness checks if the answer claims that are supported by
        the retrieved contexts.

        Args:
            question: Original question.
            answer: Generated answer.
            contexts: Retrieved context chunks.
            ground_truth: Not used for faithfulness.

        Returns:
            EvaluationResult with faithfulness score.
        """
        if not answer or not contexts:
            return EvaluationResult(
                metric_name="faithfulness",
                score=1.0 if not answer else 0.0,
                threshold=self.threshold,
                passed=bool(answer),
                details={"reason": "empty_answer_or_context"},
                reasoning="Empty answer or context",
            )

        # Simple faithfulness check: look for unsupported claims
        # A more sophisticated version would use NER and linking
        context_text = " ".join(contexts).lower()
        answer_lower = answer.lower()

        # Extract potential medical claims from answer
        claims = self._extract_claims(answer)

        # Check each claim against context
        supported_claims = 0
        unsupported_claims = []

        for claim in claims:
            if self._is_claim_supported(claim, context_text):
                supported_claims += 1
            else:
                unsupported_claims.append(claim)

        score = supported_claims / len(claims) if claims else 1.0
        score = self._normalize_score(score)

        return EvaluationResult(
            metric_name="faithfulness",
            score=score,
            threshold=self.threshold,
            passed=score >= self.threshold,
            details={
                "total_claims": len(claims),
                "supported_claims": supported_claims,
                "unsupported_claims": unsupported_claims[:5],
            },
            reasoning=f"{supported_claims}/{len(claims)} claims supported by context",
        )

    def _extract_claims(self, text: str) -> List[str]:
        """Extract potential medical claims from text."""
        # Simple sentence-like chunking
        sentences = re.split(r'[。；！？\n]', text)
        return [s.strip() for s in sentences if len(s.strip()) > 10]

    def _is_claim_supported(self, claim: str, context: str) -> bool:
        """Check if a claim is supported by context."""
        # Extract key terms from claim
        words = re.findall(r'[\u4e00-\u9fa5a-zA-Z0-9]{2,}', claim.lower())
        # If most key terms appear in context, claim is likely supported
        if not words:
            return True
        matches = sum(1 for w in words if w in context)
        return matches >= len(words) * 0.6


class AnswerRelevancyEvaluator(BaseEvaluator):
    """Evaluates answer relevancy - whether answer addresses the question.

    Implements K2: Answer Relevancy metric.
    """

    def __init__(self, threshold: float = 0.7):
        super().__init__(threshold)

    def evaluate(
        self,
        question: str,
        answer: str,
        contexts: List[str],
        ground_truth: Optional[str] = None,
    ) -> EvaluationResult:
        """Evaluate answer relevancy.

        Checks if the answer actually addresses the question being asked.

        Args:
            question: Original question.
            answer: Generated answer.
            contexts: Retrieved context chunks.
            ground_truth: Optional ground truth for comparison.

        Returns:
            EvaluationResult with relevancy score.
        """
        if not answer:
            return EvaluationResult(
                metric_name="answer_relevancy",
                score=0.0,
                threshold=self.threshold,
                passed=False,
                details={"reason": "empty_answer"},
                reasoning="No answer provided",
            )

        # Extract key terms from question
        question_terms = set(re.findall(r'[\u4e00-\u9fa5a-zA-Z0-9]{2,}', question.lower()))
        # Extract key terms from answer
        answer_terms = set(re.findall(r'[\u4e00-\u9fa5a-zA-Z0-9]{2,}', answer.lower()))

        # Calculate overlap
        if not question_terms:
            score = 1.0
        else:
            overlap = len(question_terms & answer_terms)
            score = overlap / len(question_terms)

        score = self._normalize_score(score)

        return EvaluationResult(
            metric_name="answer_relevancy",
            score=score,
            threshold=self.threshold,
            passed=score >= self.threshold,
            details={
                "question_terms": len(question_terms),
                "answer_terms": len(answer_terms),
                "overlap": len(question_terms & answer_terms),
            },
            reasoning=f"Answer addresses {score:.0%} of question terms",
        )


class ContextPrecisionEvaluator(BaseEvaluator):
    """Evaluates context precision - whether retrieved contexts are relevant.

    Implements K2: Context Precision metric.
    """

    def __init__(self, threshold: float = 0.7):
        super().__init__(threshold)

    def evaluate(
        self,
        question: str,
        answer: str,
        contexts: List[str],
        ground_truth: Optional[str] = None,
    ) -> EvaluationResult:
        """Evaluate context precision.

        Checks if the retrieved contexts are actually relevant to the question.

        Args:
            question: Original question.
            answer: Generated answer (not used for context precision).
            contexts: Retrieved context chunks.
            ground_truth: Optional ground truth contexts.

        Returns:
            EvaluationResult with precision score.
        """
        if not contexts:
            return EvaluationResult(
                metric_name="context_precision",
                score=0.0,
                threshold=self.threshold,
                passed=False,
                details={"reason": "no_contexts"},
                reasoning="No contexts retrieved",
            )

        # Extract key terms from question
        question_terms = set(re.findall(r'[\u4e00-\u9fa5a-zA-Z0-9]{2,}', question.lower()))

        # Check each context for relevance
        relevant_contexts = 0
        for ctx in contexts:
            ctx_terms = set(re.findall(r'[\u4e00-\u9fa5a-zA-Z0-9]{2,}', ctx.lower()))
            if question_terms & ctx_terms:  # Any overlap
                relevant_contexts += 1

        score = relevant_contexts / len(contexts)
        score = self._normalize_score(score)

        return EvaluationResult(
            metric_name="context_precision",
            score=score,
            threshold=self.threshold,
            passed=score >= self.threshold,
            details={
                "total_contexts": len(contexts),
                "relevant_contexts": relevant_contexts,
            },
            reasoning=f"{relevant_contexts}/{len(contexts)} contexts are relevant",
        )


class CompositeEvaluator(BaseEvaluator):
    """Combines multiple evaluators for comprehensive evaluation.

    Implements K3: Multiple evaluators run in parallel, results aggregated.
    """

    def __init__(
        self,
        evaluators: List[BaseEvaluator] = None,
        weights: Dict[str, float] = None,
    ):
        """Initialize composite evaluator.

        Args:
            evaluators: List of evaluators to run.
            weights: Optional weights for each evaluator (for weighted average).
        """
        if evaluators is None:
            evaluators = [
                FaithfulnessEvaluator(),
                AnswerRelevancyEvaluator(),
                ContextPrecisionEvaluator(),
            ]
        self.evaluators = evaluators

        # Default weights if not provided
        if weights is None:
            weights = {e.__class__.__name__: 1.0 for e in evaluators}
        self.weights = weights

        # Use minimum threshold across all evaluators
        super().__init__(threshold=min(e.threshold for e in evaluators))

    def evaluate(
        self,
        question: str,
        answer: str,
        contexts: List[str],
        ground_truth: Optional[str] = None,
    ) -> EvaluationResult:
        """Run all evaluators and aggregate results.

        Args:
            question: Original question.
            answer: Generated answer.
            contexts: Retrieved context chunks.
            ground_truth: Optional ground truth.

        Returns:
            EvaluationResult with composite score.
        """
        results = {}
        total_weight = 0.0
        weighted_score = 0.0
        all_passed = True

        for evaluator in self.evaluators:
            result = evaluator.evaluate(question, answer, contexts, ground_truth)
            results[result.metric_name] = result

            weight = self.weights.get(result.metric_name, 1.0)
            weighted_score += result.score * weight
            total_weight += weight

            if not result.passed:
                all_passed = False

        composite_score = weighted_score / total_weight if total_weight > 0 else 0.0
        composite_score = self._normalize_score(composite_score)

        return EvaluationResult(
            metric_name="composite",
            score=composite_score,
            threshold=self.threshold,
            passed=all_passed and composite_score >= self.threshold,
            details={"individual_results": {k: {"score": v.score, "passed": v.passed} for k, v in results.items()}},
            reasoning=f"Composite score: {composite_score:.2f}",
        )


class LLMasJudgeFaithfulness(BaseEvaluator):
    """LLM-as-Judge for hallucination detection.

    Implements K5: Uses strong LLM model to compute Faithfulness.
    """

    def __init__(self, llm_client, threshold: float = 0.95):
        """Initialize LLM-as-Judge evaluator.

        Args:
            llm_client: LLM client for judgment.
            threshold: Threshold for faithfulness (higher than rule-based).
        """
        super().__init__(threshold)
        self.llm = llm_client

    def evaluate(
        self,
        question: str,
        answer: str,
        contexts: List[str],
        ground_truth: Optional[str] = None,
    ) -> EvaluationResult:
        """Evaluate faithfulness using LLM judgment.

        Uses a strong model to judge whether the answer is faithful
        to the retrieved contexts.

        Args:
            question: Original question.
            answer: Generated answer.
            contexts: Retrieved context chunks.
            ground_truth: Not used.

        Returns:
            EvaluationResult with LLM-judged faithfulness.
        """
        if not self.llm:
            # Fallback to rule-based if no LLM
            return EvaluationResult(
                metric_name="llm_faithfulness",
                score=0.0,
                threshold=self.threshold,
                passed=False,
                details={"reason": "no_llm_client"},
                reasoning="No LLM client available for judgment",
            )

        context_text = "\n".join(f"- {c}" for c in contexts)

        prompt = f"""请判断以下回答是否忠实于给定的上下文。

上下文：
{context_text}

问题：{question}

回答：{answer}

请判断回答是否与上下文一致。如果回答中的所有声明都能在上下文中找到支持，则为"一致"。如果存在上下文中没有的声明（可能是幻觉），则为"不一致"。

请只回答"一致"或"不一致"，不要做其他解释。"""

        try:
            response = self.llm.generate(prompt).strip()
            is_faithful = "一致" in response

            score = 1.0 if is_faithful else 0.0

            return EvaluationResult(
                metric_name="llm_faithfulness",
                score=score,
                threshold=self.threshold,
                passed=score >= self.threshold,
                details={"llm_response": response},
                reasoning=f"LLM判断：{response}",
            )
        except Exception as e:
            return EvaluationResult(
                metric_name="llm_faithfulness",
                score=0.0,
                threshold=self.threshold,
                passed=False,
                details={"error": str(e)},
                reasoning="LLM judgment failed",
            )
