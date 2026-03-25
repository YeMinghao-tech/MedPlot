"""E2E tests for privacy data isolation (L5)."""

import tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from src.agent.memory.semantic_memory import SemanticMemory
from src.agent.memory.working_memory import WorkingMemory, WorkingMemoryStore


class TestPrivacyDataIsolation:
    """Test multi-session concurrent privacy isolation.

    Implements L5: E2E privacy data isolation.
    Verifies session A cannot read session B's patient data.
    """

    def setup_method(self):
        """Create fresh test database."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = str(Path(self.temp_dir) / "test_privacy.db")
        self.semantic = SemanticMemory(db_path=self.db_path)

    def teardown_method(self):
        """Clean up test database."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_patient_profile_isolation(self):
        """Test that patient A cannot access patient B's profile."""
        # Create two patient profiles
        self.semantic.upsert("patient_A", {
            "name": "张三",
            "age": 45,
            "allergies": ["青霉素"],
            "medical_history": ["高血压"],
        })

        self.semantic.upsert("patient_B", {
            "name": "李四",
            "age": 30,
            "allergies": ["虾"],
            "medical_history": ["糖尿病"],
        })

        # Retrieve profiles
        profile_A = self.semantic.get("patient_A")
        profile_B = self.semantic.get("patient_B")

        # Verify isolation
        assert profile_A["name"] == "张三"
        assert profile_B["name"] == "李四"

        # Patient A should not see patient B's data
        assert "李四" not in str(profile_A)
        assert "虾" not in str(profile_A)

        # Patient B should not see patient A's data
        assert "张三" not in str(profile_B)
        assert "青霉素" not in str(profile_B)

    def test_concurrent_profile_access_isolation(self):
        """Test concurrent access to different patient profiles."""
        # Create patient profiles
        profiles = {}
        for i in range(5):
            pid = f"patient_{i}"
            self.semantic.upsert(pid, {
                "name": f"患者{i}",
                "secret_data": f"敏感数据{i}",
            })
            profiles[pid] = self.semantic.get(pid)

        # Verify all profiles are isolated
        for i in range(5):
            pid = f"patient_{i}"
            profile = self.semantic.get(pid)
            assert profile["name"] == f"患者{i}"
            assert profile["secret_data"] == f"敏感数据{i}"

            # Verify no cross-contamination
            for j in range(5):
                if i != j:
                    assert f"患者{j}" not in str(profile)
                    assert f"敏感数据{j}" not in str(profile)

    def test_working_memory_session_isolation(self):
        """Test that different sessions maintain isolated working memory."""
        store = WorkingMemoryStore()

        # Create two sessions for different patients
        memory_A = store.get("session_A")
        memory_A.patient_id = "patient_A"
        memory_A.add_turn("user", "我有高血压病史")

        memory_B = store.get("session_B")
        memory_B.patient_id = "patient_B"
        memory_B.add_turn("user", "我对虾过敏")

        # Verify history is isolated
        history_A = memory_A.get_conversation_text()
        history_B = memory_B.get_conversation_text()

        assert "高血压病史" in history_A
        assert "高血压病史" not in history_B

        assert "虾过敏" in history_B
        assert "虾过敏" not in history_A

    def test_concurrent_working_memory_isolation(self):
        """Test concurrent access to working memory maintains isolation."""
        store = WorkingMemoryStore()
        num_sessions = 10

        def access_session(session_num):
            """Access a session and verify isolation."""
            session_id = f"session_{session_num}"
            patient_id = f"patient_{session_num}"
            secret = f"secret_data_{session_num}"

            memory = store.get(session_id)
            memory.patient_id = patient_id
            memory.add_turn("user", f"My secret is {secret}")

            # Verify own data
            own_history = memory.get_conversation_text()
            assert secret in own_history

            # Verify no other session's data
            for other_num in range(num_sessions):
                if other_num != session_num:
                    other_session = f"session_{other_num}"
                    other_memory = store.get(other_session)
                    other_history = other_memory.get_conversation_text()
                    assert secret not in other_history

            return True

        # Run concurrent access
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(access_session, i) for i in range(num_sessions)]
            results = [f.result() for f in futures]

        assert all(results)

    def test_semantic_memory_delete_isolation(self):
        """Test that deleting one patient doesn't affect another."""
        # Create two patient profiles
        self.semantic.upsert("patient_X", {"name": "X患者", "data": "X数据"})
        self.semantic.upsert("patient_Y", {"name": "Y患者", "data": "Y数据"})

        # Verify both exist
        assert self.semantic.get("patient_X") is not None
        assert self.semantic.get("patient_Y") is not None

        # Delete patient X
        self.semantic.delete("patient_X")

        # Verify only X is deleted
        assert self.semantic.get("patient_X") is None
        assert self.semantic.get("patient_Y") is not None
        assert self.semantic.get("patient_Y")["name"] == "Y患者"

    def test_nonexistent_patient_returns_none(self):
        """Test that querying non-existent patient returns None."""
        result = self.semantic.get("totally_fake_patient")
        assert result is None

    def test_profile_update_only_affects_target(self):
        """Test that updating one patient's profile doesn't affect others."""
        # Create initial profiles
        self.semantic.upsert("patient_P", {"name": "P患者", "score": 100})
        self.semantic.upsert("patient_Q", {"name": "Q患者", "score": 200})

        # Update only patient P
        self.semantic.upsert("patient_P", {"score": 150})

        # Verify P is updated but Q is unchanged
        profile_P = self.semantic.get("patient_P")
        profile_Q = self.semantic.get("patient_Q")

        assert profile_P["score"] == 150
        assert profile_Q["score"] == 200
        assert profile_P["name"] == "P患者"  # Preserved from original
        assert profile_Q["name"] == "Q患者"  # Unchanged
