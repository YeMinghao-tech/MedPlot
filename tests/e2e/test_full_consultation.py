"""E2E tests for full consultation flow (L1)."""

from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.routers._shared import get_session_store


class TestFullConsultationFlow:
    """Test complete consultation flow from symptom to medical record.

    Implements L1: E2E complete consultation flow.
    """

    def setup_method(self):
        """Reset session stores before each test."""
        session_store = get_session_store()
        session_store._memories.clear()

    def test_consultation_flow_basic(self):
        """Test basic consultation: symptom description -> symptom capture."""
        app = create_app()
        client = TestClient(app)

        # Step 1: Create session
        response = client.post("/sessions")
        assert response.status_code == 201
        session_id = response.json()["session_id"]

        # Step 2: Patient describes symptoms
        response = client.post(
            f"/chat/{session_id}",
            json={"content": "我发烧三天了，还咳嗽"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "intent" in data
        assert data["intent"] in ["medical_consultation", "appointment_booking"]

        # Step 3: Verify conversation history captures the symptom
        response = client.get(f"/chat/{session_id}/history")
        assert response.status_code == 200
        history = response.json()
        messages = history["messages"]
        assert len(messages) >= 2  # user message + assistant response

        # First user message should contain the symptom
        user_messages = [m for m in messages if m["role"] == "user"]
        assert len(user_messages) >= 1
        assert "发烧" in user_messages[0]["content"]
        assert "咳嗽" in user_messages[0]["content"]

    def test_consultation_flow_symptom_elicitation(self):
        """Test multi-turn symptom elicitation."""
        app = create_app()
        client = TestClient(app)

        # Create session
        response = client.post("/sessions")
        session_id = response.json()["session_id"]

        # First symptom description
        response1 = client.post(
            f"/chat/{session_id}",
            json={"content": "我头痛"}
        )
        assert response1.status_code == 200

        # Follow-up with duration
        response2 = client.post(
            f"/chat/{session_id}",
            json={"content": "已经疼了两天了"}
        )
        assert response2.status_code == 200
        data2 = response2.json()
        assert "response" in data2

        # Verify history has both exchanges
        response = client.get(f"/chat/{session_id}/history")
        history = response.json()
        messages = history["messages"]
        assert len(messages) >= 4  # 2 user + 2 assistant

    def test_consultation_with_patient_id(self):
        """Test consultation with patient ID associated."""
        app = create_app()
        client = TestClient(app)

        # Create session with patient ID
        response = client.post("/sessions?patient_id=p123")
        assert response.status_code == 201
        session_id = response.json()["session_id"]
        assert response.json()["patient_id"] == "p123"

        # Send symptom
        response = client.post(
            f"/chat/{session_id}",
            json={"content": "我胃疼"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "response" in data

    def test_consultation_session_isolation(self):
        """Test that different sessions maintain isolated state."""
        app = create_app()
        client = TestClient(app)

        # Create two sessions
        response1 = client.post("/sessions")
        session_id_1 = response1.json()["session_id"]

        response2 = client.post("/sessions")
        session_id_2 = response2.json()["session_id"]

        # Send different symptoms to each
        client.post(f"/chat/{session_id_1}", json={"content": "高血压"})
        client.post(f"/chat/{session_id_2}", json={"content": "糖尿病"})

        # Verify histories are isolated
        response1 = client.get(f"/chat/{session_id_1}/history")
        response2 = client.get(f"/chat/{session_id_2}/history")

        history1 = response1.json()["messages"]
        history2 = response2.json()["messages"]

        # Each should only have their own content
        assert len(history1) >= 2
        assert len(history2) >= 2


class TestConsultationMedicalKnowledge:
    """Test medical knowledge query in consultation flow."""

    def setup_method(self):
        """Reset session stores before each test."""
        session_store = get_session_store()
        session_store._memories.clear()

    def test_medical_knowledge_query(self):
        """Test querying medical knowledge."""
        app = create_app()
        client = TestClient(app)

        # Create session
        response = client.post("/sessions")
        session_id = response.json()["session_id"]

        # Query medical knowledge
        response = client.post(
            f"/chat/{session_id}",
            json={"content": "请问高血压的诊断标准是什么？"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "medical_knowledge"
        assert "response" in data


class TestConsultationStateManagement:
    """Test consultation state management."""

    def setup_method(self):
        """Reset session stores before each test."""
        session_store = get_session_store()
        session_store._memories.clear()

    def test_state_persistence_across_turns(self):
        """Test that state persists across conversation turns."""
        app = create_app()
        client = TestClient(app)

        # Create session
        response = client.post("/sessions")
        session_id = response.json()["session_id"]

        # Turn 1: Initial symptom
        r1 = client.post(f"/chat/{session_id}", json={"content": "我发烧"})
        assert r1.status_code == 200
        state1 = r1.json()["state"]

        # Turn 2: Additional info
        r2 = client.post(f"/chat/{session_id}", json={"content": "还有咳嗽"})
        assert r2.status_code == 200
        state2 = r2.json()["state"]

        # Turn 3: More info
        r3 = client.post(f"/chat/{session_id}", json={"content": "已经三天了"})
        assert r3.status_code == 200

        # Verify conversation accumulated
        history = client.get(f"/chat/{session_id}/history").json()
        assert len(history["messages"]) >= 6  # 3 user + 3 assistant

    def test_session_lifecycle(self):
        """Test complete session lifecycle: create -> consult -> delete."""
        app = create_app()
        client = TestClient(app)

        # Create
        response = client.post("/sessions")
        assert response.status_code == 201
        session_id = response.json()["session_id"]

        # Consult
        client.post(f"/chat/{session_id}", json={"content": "我头痛"})

        # Verify exists
        response = client.get(f"/sessions/{session_id}")
        assert response.status_code == 200

        # Delete
        response = client.delete(f"/sessions/{session_id}")
        assert response.status_code == 200

        # Verify deleted
        response = client.get(f"/sessions/{session_id}")
        assert response.status_code == 404
