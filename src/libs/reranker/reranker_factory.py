"""Reranker Factory for creating Reranker instances based on configuration."""

from typing import Dict, Type

from src.core.settings import Settings
from src.libs.reranker.base_reranker import BaseReranker
from src.libs.reranker.bge_reranker import BGEReranker
from src.libs.reranker.llm_reranker import LLMReranker
from src.libs.reranker.none_reranker import NoneReranker


class RerankerFactory:
    """Factory for creating Reranker instances based on configuration."""

    _providers: Dict[str, Type[BaseReranker]] = {
        "bge": BGEReranker,
        "llm": LLMReranker,
        "none": NoneReranker,
    }

    @classmethod
    def create(cls, settings: Settings) -> BaseReranker:
        """Create a Reranker instance based on settings.

        Args:
            settings: Settings object containing Reranker configuration.

        Returns:
            An instance of a BaseReranker subclass.

        Raises:
            ValueError: If the provider is not supported.
        """
        provider = settings.retrieval.rerank_backend.lower()

        if provider not in cls._providers:
            raise ValueError(
                f"Unsupported Reranker provider: {provider}. "
                f"Supported providers: {list(cls._providers.keys())}"
            )

        reranker_class = cls._providers[provider]

        if provider == "bge":
            return reranker_class(model=settings.retrieval.rerank_model)
        elif provider == "llm":
            from src.libs.llm.llm_factory import LLMFactory

            llm = LLMFactory.create(settings)
            return reranker_class(llm=llm)
        else:
            return reranker_class()

    @classmethod
    def register_provider(cls, name: str, reranker_class: Type[BaseReranker]) -> None:
        """Register a new Reranker provider.

        Args:
            name: Provider name (e.g., 'bge').
            reranker_class: The Reranker class to register.
        """
        cls._providers[name.lower()] = reranker_class
