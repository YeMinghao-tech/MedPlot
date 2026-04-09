"""Memory manager for memory lifecycle - distillation and injection."""

from typing import Optional, List, Dict, Any
import json

from src.agent.memory.working_memory import WorkingMemory
from src.agent.memory.semantic_memory import SemanticMemory
from src.agent.memory.episodic_memory import EpisodicMemory, Episode
from src.libs.llm.base_llm import BaseLLM


class MemoryManager:
    """Manages memory lifecycle across sessions.

    Handles:
    - G4: Session-end memory distillation (extract summary to episodic memory)
    - G5: Session-start memory injection (load patient history into working memory)
    """

    def __init__(
        self,
        semantic_memory: SemanticMemory,
        episodic_memory: EpisodicMemory,
        llm_client: Optional[BaseLLM] = None,
    ):
        """Initialize memory manager.

        Args:
            semantic_memory: Semantic memory for patient profiles.
            episodic_memory: Episodic memory for visit history.
            llm_client: Optional LLM client for summarization.
        """
        self.semantic = semantic_memory
        self.episodic = episodic_memory
        self.llm = llm_client

    def distill_session(
        self,
        memory: WorkingMemory,
        embedding: List[float],
    ) -> Optional[str]:
        """Distill session into episodic memory (G4).

        Extract key information from conversation and store as episode.
        Uses LLM to generate summary if available, otherwise uses rule-based.

        Args:
            memory: Working memory to distill.
            embedding: Vector embedding for the summary.

        Returns:
            Episode ID if successful, None otherwise.
        """
        patient_id = memory.patient_id
        if not patient_id:
            return None

        # Generate summary
        summary = self._generate_summary(memory)

        # Extract metadata
        metadata = {
            "symptoms": list(memory.symptom_tree.get("symptoms", [])),
            "intent": memory.current_intent,
            "turn_count": len(memory.message_history),
        }

        # Store in episodic memory
        episode_id = self.episodic.add(
            patient_id=patient_id,
            session_id=memory.session_id,
            summary=summary,
            embedding=embedding,
            metadata=metadata,
        )

        return episode_id

    def _generate_summary(self, memory: WorkingMemory) -> str:
        """Generate session summary.

        Uses LLM if available, otherwise rule-based extraction.

        Args:
            memory: Working memory to summarize.

        Returns:
            Summary string.
        """
        if self.llm:
            return self._generate_llm_summary(memory)
        return self._generate_rule_summary(memory)

    def _generate_llm_summary(self, memory: WorkingMemory) -> str:
        """Generate summary using LLM."""
        conversation = memory.get_conversation_text()

        prompt = f"""请为以下医疗问诊对话生成简短摘要（100字以内）：

{conversation}

摘要应包含：主要症状、医生建议、挂号科室（如有）。
"""

        try:
            response = self.llm.generate(prompt)
            return response.strip()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"LLM summary generation failed: {e}")
            return self._generate_rule_summary(memory)

    def _generate_rule_summary(self, memory: WorkingMemory) -> str:
        """Generate summary using rules (fallback)."""
        symptoms = memory.symptom_tree.get("symptoms", [])
        symptom_str = "、".join(symptoms) if symptoms else "未明确"

        return f"症状：{symptom_str}；对话轮次：{len(memory.message_history)}"

    def inject_into_session(
        self,
        memory: WorkingMemory,
        patient_id: str,
        top_k_similar: int = 3,
    ) -> Dict[str, Any]:
        """Inject patient history into working memory (G5).

        Loads:
        1. Patient profile from semantic memory
        2. Similar past visits from episodic memory

        Args:
            memory: Working memory to inject into.
            patient_id: Patient identifier.
            top_k_similar: Number of similar episodes to retrieve.

        Returns:
            Dict with 'profile' and 'history' keys.
        """
        result = {"profile": None, "history": []}

        # Load patient profile
        profile = self.semantic.get(patient_id)
        result["profile"] = profile

        # Inject key info into working memory context
        if profile:
            memory.patient_id = patient_id
            if "allergies" in profile:
                memory.context["allergies"] = profile["allergies"]
            if "chronic_conditions" in profile:
                memory.context["chronic_conditions"] = profile["chronic_conditions"]
            if "current_medications" in profile:
                memory.context["current_medications"] = profile["current_medications"]

        # Retrieve similar past visits if episodic memory available
        if self.episodic and self.llm:
            try:
                # Generate query embedding from symptoms if available
                symptoms = list(memory.symptom_tree.get("symptoms", []))
                if symptoms:
                    # Use first symptom as simple query (proper impl would use LLM embedding)
                    query_text = " ".join(symptoms)
                    # Note: In production, generate actual embedding via embedding model
                    # For now, we skip vector search if no embedding model
                    # episodes = self.episodic.search(patient_id, query_vector, top_k=top_k_similar)
                    # result["history"] = episodes
                    pass
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Episodic retrieval failed: {e}")

        return result

    def get_patient_history(
        self,
        patient_id: str,
        limit: int = 10,
    ) -> List[Episode]:
        """Get patient visit history.

        Args:
            patient_id: Patient identifier.
            limit: Maximum number of episodes.

        Returns:
            List of Episode objects.
        """
        return self.episodic.get_patient_history(patient_id, limit=limit)

    def update_patient_profile(
        self,
        patient_id: str,
        updates: Dict[str, Any],
    ):
        """Update patient profile with new information.

        Args:
            patient_id: Patient identifier.
            updates: Profile fields to update.
        """
        self.semantic.upsert(patient_id, updates)
