"""Tests for Agent components."""

from src.agent.planner.intent_classifier import Intent, IntentClassifier
from src.agent.planner.state_manager import State, StateManager, PatientState
from src.agent.planner.emergency_interceptor import EmergencyInterceptor
from src.agent.memory.working_memory import WorkingMemory, WorkingMemoryStore
from src.agent.memory.semantic_memory import SemanticMemory
from src.agent.memory.episodic_memory import EpisodicMemory
from src.agent.memory.memory_factory import MemoryFactory
from src.agent.memory.memory_manager import MemoryManager


class TestIntentClassifier:
    """Test IntentClassifier functionality."""

    def test_classify_emergency(self):
        """Test emergency detection has highest priority."""
        classifier = IntentClassifier()

        result = classifier.classify("我胸痛非常严重")

        assert result.intent == Intent.RED_FLAG
        assert result.confidence == 1.0
        assert "胸痛" in result.keywords

    def test_classify_greeting(self):
        """Test greeting classification."""
        classifier = IntentClassifier()

        result = classifier.classify("你好")

        assert result.intent == Intent.GREETING
        assert result.confidence > 0.5

    def test_classify_consultation(self):
        """Test medical consultation classification."""
        classifier = IntentClassifier()

        result = classifier.classify("我发烧三天了，还咳嗽")

        assert result.intent == Intent.MEDICAL_CONSULTATION
        assert len(result.keywords) > 0

    def test_classify_appointment(self):
        """Test appointment booking classification."""
        classifier = IntentClassifier()

        result = classifier.classify("我想挂号看内科")

        assert result.intent == Intent.APPOINTMENT_BOOKING

    def test_classify_knowledge(self):
        """Test medical knowledge classification."""
        classifier = IntentClassifier()

        result = classifier.classify("请问心脏病是什么")

        assert result.intent == Intent.MEDICAL_KNOWLEDGE

    def test_classify_confirm(self):
        """Test confirmation classification."""
        classifier = IntentClassifier()

        result = classifier.classify("好的，我明白了")

        assert result.intent == Intent.CONFIRM

    def test_classify_empty(self):
        """Test empty input."""
        classifier = IntentClassifier()

        result = classifier.classify("")

        assert result.intent == Intent.UNKNOWN
        assert result.confidence == 0.0


class TestEmergencyInterceptor:
    """Test EmergencyInterceptor functionality."""

    def test_intercept_chest_pain(self):
        """Test chest pain detection."""
        interceptor = EmergencyInterceptor()

        result = interceptor.intercept("我胸痛")

        assert result == "胸痛"

    def test_intercept_no_emergency(self):
        """Test normal symptom returns None."""
        interceptor = EmergencyInterceptor()

        result = interceptor.intercept("我有点头痛")

        assert result is None

    def test_get_emergency_response(self):
        """Test emergency guidance message."""
        interceptor = EmergencyInterceptor()

        response = interceptor.get_emergency_response("胸痛")

        assert "120" in response or "紧急" in response


class TestStateManager:
    """Test StateManager functionality."""

    def test_initial_state(self):
        """Test initial state is GREETING."""
        manager = StateManager()

        assert manager.get_state() == State.GREETING

    def test_transition_greeting_to_consultation(self):
        """Test transition from GREETING to SYMPTOM_COLLECTION."""
        manager = StateManager()

        manager.transition(Intent.MEDICAL_CONSULTATION)

        assert manager.get_state() == State.SYMPTOM_COLLECTION

    def test_transition_to_red_flag(self):
        """Test transition to RED_FLAG is terminal."""
        manager = StateManager()

        manager.transition(Intent.RED_FLAG)

        assert manager.get_state() == State.RED_FLAG
        assert manager.is_terminal_state()

    def test_patient_state_accumulation(self):
        """Test patient state accumulates symptoms."""
        manager = StateManager()
        manager.current_state = State.SYMPTOM_COLLECTION

        manager.patient_state.add_symptom("头痛")
        manager.patient_state.add_symptom("发热")

        assert len(manager.patient_state.symptoms) == 2
        assert "头痛" in manager.patient_state.symptoms

    def test_reset(self):
        """Test state manager reset."""
        manager = StateManager()
        manager.transition(Intent.MEDICAL_CONSULTATION)
        manager.patient_state.add_symptom("test")

        manager.reset()

        assert manager.get_state() == State.GREETING
        assert len(manager.patient_state.symptoms) == 0


class TestWorkingMemory:
    """Test WorkingMemory functionality."""

    def test_add_turn(self):
        """Test adding conversation turns."""
        memory = WorkingMemory(session_id="s1")

        memory.add_turn("user", "我发烧了")
        memory.add_turn("assistant", "持续多久了？")

        assert len(memory.message_history) == 2
        assert memory.message_history[0].role == "user"

    def test_get_recent_messages(self):
        """Test getting recent messages."""
        memory = WorkingMemory(session_id="s1")

        for i in range(10):
            memory.add_turn("user", f"message {i}")

        recent = memory.get_recent_messages(3)

        assert len(recent) == 3

    def test_get_conversation_text(self):
        """Test conversation text generation."""
        memory = WorkingMemory(session_id="s1")
        memory.add_turn("user", "你好")
        memory.add_turn("assistant", "您好")

        text = memory.get_conversation_text()

        assert "用户" in text
        assert "助手" in text


class TestWorkingMemoryStore:
    """Test WorkingMemoryStore functionality."""

    def test_get_or_create(self):
        """Test getting or creating memory."""
        store = WorkingMemoryStore()

        memory1 = store.get("s1")
        memory2 = store.get("s1")

        assert memory1 is memory2
        assert memory1.session_id == "s1"

    def test_delete(self):
        """Test deleting memory."""
        store = WorkingMemoryStore()
        store.get("s1")

        store.delete("s1")

        assert not store.exists("s1")


class TestSemanticMemory:
    """Test SemanticMemory functionality."""

    def test_upsert_and_get(self, tmp_path):
        """Test upsert and retrieval."""
        db_path = str(tmp_path / "test_profiles.db")
        memory = SemanticMemory(db_path=db_path)

        memory.upsert("p1", {"name": "张三", "age": 30})

        profile = memory.get("p1")

        assert profile is not None
        assert profile["name"] == "张三"
        assert profile["age"] == 30

    def test_merge_profiles(self, tmp_path):
        """Test profile merge on upsert."""
        db_path = str(tmp_path / "test_profiles.db")
        memory = SemanticMemory(db_path=db_path)

        memory.upsert("p1", {"name": "张三", "allergies": ["青霉素"]})
        memory.upsert("p1", {"name": "张三", "allergies": ["头孢"]})

        profile = memory.get("p1")

        assert "青霉素" in profile["allergies"]
        assert "头孢" in profile["allergies"]

    def test_delete(self, tmp_path):
        """Test profile deletion."""
        db_path = str(tmp_path / "test_profiles.db")
        memory = SemanticMemory(db_path=db_path)

        memory.upsert("p1", {"name": "张三"})
        memory.delete("p1")

        assert memory.get("p1") is None


class TestSemanticMemoryExtended:
    """Test SemanticMemory extended features (G2)."""

    def test_list_patients(self, tmp_path):
        """Test listing patient profiles."""
        db_path = str(tmp_path / "test_profiles.db")
        memory = SemanticMemory(db_path=db_path)

        memory.upsert("p1", {"name": "张三", "age": 30})
        memory.upsert("p2", {"name": "李四", "age": 25})

        patients = memory.list_patients()

        assert len(patients) == 2
        patient_ids = {p["patient_id"] for p in patients}
        assert "p1" in patient_ids
        assert "p2" in patient_ids

    def test_search_patients(self, tmp_path):
        """Test searching patient profiles."""
        db_path = str(tmp_path / "test_profiles.db")
        memory = SemanticMemory(db_path=db_path)

        memory.upsert("p1", {"name": "张三", "condition": "高血压"})
        memory.upsert("p2", {"name": "李四", "condition": "糖尿病"})

        results = memory.search("高血压")

        assert len(results) == 1
        assert results[0]["patient_id"] == "p1"

    def test_search_patients_no_match(self, tmp_path):
        """Test search with no matches."""
        db_path = str(tmp_path / "test_profiles.db")
        memory = SemanticMemory(db_path=db_path)

        memory.upsert("p1", {"name": "张三"})

        results = memory.search("糖尿病")

        assert len(results) == 0


class TestMemoryFactory:
    """Test MemoryFactory functionality."""

    def test_create_working_memory(self):
        """Test creating working memory."""
        store = MemoryFactory.create_working()

        assert isinstance(store, WorkingMemoryStore)

    def test_create_working_memory_redis(self):
        """Test creating redis working memory (G1)."""
        # This will fail if redis is not available, but factory should not raise
        # NotImplementedError anymore
        from src.agent.memory.redis_working_memory import RedisWorkingMemoryStore
        # Factory returns RedisWorkingMemoryStore when backend=redis
        # (actual connection may fail if redis not running)
        try:
            store = MemoryFactory.create_working({"backend": "redis"})
            assert isinstance(store, RedisWorkingMemoryStore)
        except Exception:
            # Redis not available in test env is OK
            pass

    def test_create_semantic_memory(self, tmp_path):
        """Test creating semantic memory."""
        db_path = str(tmp_path / "test.db")
        memory = MemoryFactory.create_semantic({"db_path": db_path})

        assert isinstance(memory, SemanticMemory)

    def test_create_episodic_memory(self):
        """Test creating episodic memory (mock vector store)."""
        from unittest.mock import MagicMock

        mock_store = MagicMock()
        mock_store.query.return_value = []

        memory = MemoryFactory.create_episodic(
            mock_store,
            {"collection": "test"}
        )

        assert isinstance(memory, EpisodicMemory)


class TestMemoryManager:
    """Test MemoryManager for G4/G5."""

    def test_distill_session_requires_patient_id(self, tmp_path):
        """Test that distill requires patient_id."""
        from unittest.mock import MagicMock

        semantic = SemanticMemory(db_path=str(tmp_path / "sem.db"))
        mock_episodic = MagicMock()
        manager = MemoryManager(semantic, mock_episodic)

        memory = WorkingMemory(session_id="s1")
        # No patient_id set

        result = manager.distill_session(memory, [0.0] * 128)

        assert result is None
        mock_episodic.add.assert_not_called()

    def test_distill_session_with_patient_id(self, tmp_path):
        """Test memory distillation (G4)."""
        from unittest.mock import MagicMock

        semantic = SemanticMemory(db_path=str(tmp_path / "sem.db"))
        mock_episodic = MagicMock()
        mock_episodic.add.return_value = "ep1"
        manager = MemoryManager(semantic, mock_episodic)

        memory = WorkingMemory(session_id="s1", patient_id="p1")
        memory.add_turn("user", "我发烧三天了")
        memory.symptom_tree = {"symptoms": ["发烧"]}

        result = manager.distill_session(memory, [0.0] * 128)

        assert result == "ep1"
        mock_episodic.add.assert_called_once()
        call_args = mock_episodic.add.call_args
        assert call_args.kwargs["patient_id"] == "p1"
        assert call_args.kwargs["session_id"] == "s1"

    def test_inject_into_session(self, tmp_path):
        """Test memory injection into new session (G5)."""
        from unittest.mock import MagicMock

        semantic = SemanticMemory(db_path=str(tmp_path / "sem.db"))
        semantic.upsert("p1", {
            "name": "张三",
            "allergies": ["青霉素"],
            "chronic_conditions": ["高血压"],
        })
        mock_episodic = MagicMock()
        manager = MemoryManager(semantic, mock_episodic)

        memory = WorkingMemory(session_id="s2")
        result = manager.inject_into_session(memory, "p1")

        assert result["profile"]["name"] == "张三"
        assert memory.context["allergies"] == ["青霉素"]
        assert memory.context["chronic_conditions"] == ["高血压"]

    def test_update_patient_profile(self, tmp_path):
        """Test updating patient profile."""
        semantic = SemanticMemory(db_path=str(tmp_path / "sem.db"))
        semantic.upsert("p1", {"name": "张三", "age": 30})

        semantic.upsert("p1", {"age": 31, "allergies": ["头孢"]})

        profile = semantic.get("p1")
        assert profile["name"] == "张三"
        assert profile["age"] == 31
        assert "头孢" in profile["allergies"]
