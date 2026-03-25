"""E2E tests for follow-up memory retrieval (L2)."""

import tempfile
from pathlib import Path

from src.agent.memory.episodic_memory import EpisodicMemory, Episode
from src.agent.memory.semantic_memory import SemanticMemory
from src.agent.memory.memory_manager import MemoryManager
from src.agent.memory.working_memory import WorkingMemory


class FakeVectorStore:
    """Fake vector store for testing."""

    def __init__(self):
        self.vectors = {}

    def upsert(self, records, collection="default"):
        for r in records:
            self.vectors[r["id"]] = r["embedding"]

    def query(self, vector, top_k=5, filters=None, collection="default"):
        # Simple mock - return all stored vectors with fake scores
        results = []
        for vid, v in self.vectors.items():
            # Fake similarity score based on whether vector matches query
            score = 0.95 if vid.startswith("ep_") else 0.5
            results.append({"id": vid, "score": score, "text": ""})
        return results[:top_k]


class TestFollowUpMemoryRetrieval:
    """Test follow-up visit memory retrieval.

    Implements L2: E2E follow-up memory retrieval flow.
    """

    def test_episodic_memory_stores_and_retrieves(self):
        """Test that episodic memory stores visit summaries and can retrieve them."""
        # Setup
        fake_store = FakeVectorStore()
        with tempfile.TemporaryDirectory() as tmpdir:
            episodic = EpisodicMemory(
                vector_store=fake_store,
                metadata_db_path=str(Path(tmpdir) / "episodes.db"),
                collection="test_episodes",
            )

            # First visit - add episode
            episode_id = episodic.add(
                patient_id="p123",
                session_id="s1",
                summary="患者主诉头痛、发烧3天，诊断为上呼吸道感染",
                embedding=[0.1] * 128,
                metadata={"symptoms": ["头痛", "发烧"], "diagnosis": "上呼吸道感染"},
            )
            assert episode_id is not None

            # Retrieve patient history
            history = episodic.get_patient_history("p123")
            assert len(history) == 1
            assert history[0].patient_id == "p123"
            assert "头痛" in history[0].summary

    def test_episodic_memory_patient_isolation(self):
        """Test that episodic memory isolates patients."""
        fake_store = FakeVectorStore()
        with tempfile.TemporaryDirectory() as tmpdir:
            episodic = EpisodicMemory(
                vector_store=fake_store,
                metadata_db_path=str(Path(tmpdir) / "episodes.db"),
            )

            # Add episodes for two patients
            episodic.add(
                patient_id="p1",
                session_id="s1",
                summary="患者p1主诉高血压",
                embedding=[0.1] * 128,
            )
            episodic.add(
                patient_id="p2",
                session_id="s2",
                summary="患者p2主诉糖尿病",
                embedding=[0.2] * 128,
            )

            # Each patient only sees their own history
            p1_history = episodic.get_patient_history("p1")
            p2_history = episodic.get_patient_history("p2")

            assert len(p1_history) == 1
            assert "高血压" in p1_history[0].summary
            assert "糖尿病" not in p1_history[0].summary

            assert len(p2_history) == 1
            assert "糖尿病" in p2_history[0].summary
            assert "高血压" not in p2_history[0].summary

    def test_memory_manager_distill_session(self):
        """Test memory distillation from working memory to episodic."""
        fake_store = FakeVectorStore()
        with tempfile.TemporaryDirectory() as tmpdir:
            semantic = SemanticMemory(db_path=str(Path(tmpdir) / "semantic.db"))
            episodic = EpisodicMemory(
                vector_store=fake_store,
                metadata_db_path=str(Path(tmpdir) / "episodes.db"),
            )
            manager = MemoryManager(semantic_memory=semantic, episodic_memory=episodic)

            # Create working memory with patient session
            memory = WorkingMemory(session_id="s1", patient_id="p123")
            memory.add_turn("user", "我发烧三天了")
            memory.add_turn("assistant", "了解，请问还有其他症状吗？")
            memory.add_turn("user", "还有咳嗽")
            memory.symptom_tree = {"symptoms": ["发烧", "咳嗽"]}

            # Distill session
            episode_id = manager.distill_session(memory, embedding=[0.5] * 128)
            assert episode_id is not None

            # Verify episodic memory has the episode
            history = episodic.get_patient_history("p123")
            assert len(history) == 1

    def test_memory_manager_inject_into_session(self):
        """Test memory injection into new working memory."""
        fake_store = FakeVectorStore()
        with tempfile.TemporaryDirectory() as tmpdir:
            semantic = SemanticMemory(db_path=str(Path(tmpdir) / "semantic.db"))
            episodic = EpisodicMemory(
                vector_store=fake_store,
                metadata_db_path=str(Path(tmpdir) / "episodes.db"),
            )
            manager = MemoryManager(semantic_memory=semantic, episodic_memory=episodic)

            # Create patient profile
            semantic.upsert("p123", {
                "name": "张三",
                "allergies": ["青霉素"],
                "chronic_conditions": ["高血压"],
            })

            # Create new working memory
            memory = WorkingMemory(session_id="s2", patient_id="p123")

            # Inject memory
            result = manager.inject_into_session(memory, patient_id="p123")

            # Verify profile injected
            assert result["profile"] is not None
            assert result["profile"]["name"] == "张三"
            assert memory.context.get("allergies") == ["青霉素"]
            assert memory.context.get("chronic_conditions") == ["高血压"]

    def test_follow_up_context_retrieval(self):
        """Test that follow-up visits can retrieve relevant historical context."""
        fake_store = FakeVectorStore()
        with tempfile.TemporaryDirectory() as tmpdir:
            episodic = EpisodicMemory(
                vector_store=fake_store,
                metadata_db_path=str(Path(tmpdir) / "episodes.db"),
            )

            # First visit - hypertension follow-up
            episodic.add(
                patient_id="p456",
                session_id="visit_1",
                summary="高血压随访，血压140/90，服用降压药",
                embedding=[0.1] * 128,
                metadata={"condition": "hypertension"},
            )

            # Second visit - new symptoms
            episodic.add(
                patient_id="p456",
                session_id="visit_2",
                summary="因头晕就诊，有高血压史",
                embedding=[0.2] * 128,
                metadata={"condition": "dizziness"},
            )

            # Retrieve all history
            history = episodic.get_patient_history("p456")
            assert len(history) == 2

            # History should mention hypertension context
            summaries = [h.summary for h in history]
            assert any("高血压" in s for s in summaries)

    def test_working_memory_sessions_are_isolated(self):
        """Test that different sessions maintain isolated state."""
        # Session 1
        memory1 = WorkingMemory(session_id="s1", patient_id="p1")
        memory1.add_turn("user", "我有高血压")
        memory1.symptom_tree = {"symptoms": ["高血压"]}

        # Session 2
        memory2 = WorkingMemory(session_id="s2", patient_id="p1")
        memory2.add_turn("user", "我有糖尿病")

        # Verify isolation
        history1 = memory1.get_conversation_text()
        history2 = memory2.get_conversation_text()

        assert "高血压" in history1
        assert "糖尿病" not in history1
        assert "糖尿病" in history2
        assert "高血压" not in history2
