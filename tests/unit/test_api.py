"""Tests for API routes."""

from src.api.app import create_app
from src.api.routers.session import _session_store as session_store, _session_metadata as session_metadata
from src.api.routers.chat import _session_store as chat_session_store
from src.api.routers import patient


class TestSessionRoutes:
    """Test session management endpoints."""

    def setup_method(self):
        """Reset session stores before each test."""
        session_store._memories.clear()
        session_metadata.clear()
        chat_session_store._memories.clear()

    def test_create_session(self):
        """Test session creation."""
        from fastapi.testclient import TestClient
        app = create_app()
        client = TestClient(app)

        response = client.post("/sessions")

        assert response.status_code == 201
        data = response.json()
        assert "session_id" in data
        assert data["patient_id"] is None

    def test_create_session_with_patient_id(self):
        """Test session creation with patient ID."""
        from fastapi.testclient import TestClient
        app = create_app()
        client = TestClient(app)

        response = client.post("/sessions?patient_id=p123")

        assert response.status_code == 201
        data = response.json()
        assert data["patient_id"] == "p123"

    def test_get_session(self):
        """Test getting session info."""
        from fastapi.testclient import TestClient
        app = create_app()
        client = TestClient(app)

        # Create session
        create_resp = client.post("/sessions")
        session_id = create_resp.json()["session_id"]

        # Get session
        response = client.get(f"/sessions/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id

    def test_get_session_not_found(self):
        """Test getting non-existent session."""
        from fastapi.testclient import TestClient
        app = create_app()
        client = TestClient(app)

        response = client.get("/sessions/nonexistent")

        assert response.status_code == 404

    def test_list_sessions(self):
        """Test listing sessions."""
        from fastapi.testclient import TestClient
        app = create_app()
        client = TestClient(app)

        # Create multiple sessions
        client.post("/sessions")
        client.post("/sessions?patient_id=p1")
        client.post("/sessions?patient_id=p1")

        response = client.get("/sessions")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    def test_list_sessions_filtered_by_patient(self):
        """Test listing sessions filtered by patient."""
        from fastapi.testclient import TestClient
        app = create_app()
        client = TestClient(app)

        client.post("/sessions")
        client.post("/sessions?patient_id=p1")
        client.post("/sessions?patient_id=p2")

        response = client.get("/sessions?patient_id=p1")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["patient_id"] == "p1"

    def test_delete_session(self):
        """Test deleting session."""
        from fastapi.testclient import TestClient
        app = create_app()
        client = TestClient(app)

        # Create session
        create_resp = client.post("/sessions")
        session_id = create_resp.json()["session_id"]

        # Delete session
        response = client.delete(f"/sessions/{session_id}")

        assert response.status_code == 200

        # Verify deleted
        get_resp = client.get(f"/sessions/{session_id}")
        assert get_resp.status_code == 404

    def test_update_activity(self):
        """Test updating session activity."""
        from fastapi.testclient import TestClient
        app = create_app()
        client = TestClient(app)

        # Create session
        create_resp = client.post("/sessions")
        session_id = create_resp.json()["session_id"]

        # Update activity
        response = client.patch(f"/sessions/{session_id}/activity")

        assert response.status_code == 200
        assert "last_activity" in response.json()


class TestChatRoutes:
    """Test chat endpoints."""

    def setup_method(self):
        """Reset session stores before each test."""
        session_store._memories.clear()
        session_metadata.clear()
        chat_session_store._memories.clear()

    def test_chat_session_not_found(self):
        """Test chat with non-existent session."""
        from fastapi.testclient import TestClient
        app = create_app()
        client = TestClient(app)

        response = client.post("/chat/nonexistent", json={"content": "hello"})

        assert response.status_code == 404

    def test_chat_empty_content(self):
        """Test chat with empty content."""
        from fastapi.testclient import TestClient
        app = create_app()
        client = TestClient(app)

        # Create session first
        create_resp = client.post("/sessions")
        session_id = create_resp.json()["session_id"]

        response = client.post(f"/chat/{session_id}", json={"content": ""})

        assert response.status_code == 400

    def test_chat_success(self):
        """Test successful chat message."""
        from fastapi.testclient import TestClient
        app = create_app()
        client = TestClient(app)

        # Create session
        create_resp = client.post("/sessions")
        session_id = create_resp.json()["session_id"]

        response = client.post(f"/chat/{session_id}", json={"content": "我发烧了"})

        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "intent" in data

    def test_get_history(self):
        """Test getting conversation history."""
        from fastapi.testclient import TestClient
        app = create_app()
        client = TestClient(app)

        # Create session
        create_resp = client.post("/sessions")
        session_id = create_resp.json()["session_id"]

        # Send message
        client.post(f"/chat/{session_id}", json={"content": "我发烧了"})

        # Get history
        response = client.get(f"/chat/{session_id}/history")

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert len(data["messages"]) >= 1

    def test_get_history_not_found(self):
        """Test getting history for non-existent session."""
        from fastapi.testclient import TestClient
        app = create_app()
        client = TestClient(app)

        response = client.get("/chat/nonexistent/history")

        assert response.status_code == 404


class TestPatientRoutes:
    """Test patient profile endpoints."""

    def test_get_patient_not_found(self):
        """Test getting non-existent patient."""
        from fastapi.testclient import TestClient
        app = create_app()
        client = TestClient(app)

        response = client.get("/patients/nonexistent")

        assert response.status_code == 404

    def test_upsert_patient(self):
        """Test creating/updating patient profile."""
        from fastapi.testclient import TestClient
        app = create_app()
        client = TestClient(app)

        response = client.put("/patients/p1", json={"name": "张三", "age": 30})

        assert response.status_code == 200
        data = response.json()
        assert data["patient_id"] == "p1"
        assert data["name"] == "张三"

    def test_get_patient(self):
        """Test getting patient profile."""
        from fastapi.testclient import TestClient
        app = create_app()
        client = TestClient(app)

        # Create patient
        client.put("/patients/p1", json={"name": "张三", "age": 30})

        # Get patient
        response = client.get("/patients/p1")

        assert response.status_code == 200
        data = response.json()
        assert data["patient_id"] == "p1"
        assert data["name"] == "张三"

    def test_delete_patient(self):
        """Test deleting patient profile."""
        from fastapi.testclient import TestClient
        app = create_app()
        client = TestClient(app)

        # Create patient
        client.put("/patients/p1", json={"name": "张三"})

        # Delete patient
        response = client.delete("/patients/p1")

        assert response.status_code == 200

        # Verify deleted
        get_resp = client.get("/patients/p1")
        assert get_resp.status_code == 404

    def test_delete_patient_not_found(self):
        """Test deleting non-existent patient."""
        from fastapi.testclient import TestClient
        app = create_app()
        client = TestClient(app)

        response = client.delete("/patients/nonexistent")

        assert response.status_code == 404


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health(self):
        """Test health endpoint."""
        from fastapi.testclient import TestClient
        app = create_app()
        client = TestClient(app)

        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    def test_root(self):
        """Test root endpoint."""
        from fastapi.testclient import TestClient
        app = create_app()
        client = TestClient(app)

        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "MedPilot API"
        assert data["status"] == "running"
