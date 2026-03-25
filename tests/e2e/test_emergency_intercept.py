"""E2E tests for emergency red flag interception (L3)."""

from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.routers._shared import get_session_store
from src.agent.planner.emergency_interceptor import EmergencyInterceptor
from src.agent.planner.intent_classifier import Intent, IntentClassifier


class TestEmergencyInterception:
    """Test emergency red flag interception.

    Implements L3: E2E emergency red flag intercept.
    """

    def setup_method(self):
        """Reset session stores before each test."""
        session_store = get_session_store()
        session_store._memories.clear()

    def test_chest_pain_radiation_triggers_red_flag(self):
        """Test that '胸痛放射至左肩' triggers red flag response."""
        app = create_app()
        client = TestClient(app)

        # Create session
        response = client.post("/sessions")
        session_id = response.json()["session_id"]

        # Report emergency symptom
        response = client.post(
            f"/chat/{session_id}",
            json={"content": "我胸痛，放射到左肩"}
        )
        assert response.status_code == 200
        data = response.json()

        # Should detect red flag
        assert data["intent"] == "red_flag"
        assert "120" in data["response"] or "急救" in data["response"] or "紧急" in data["response"]

    def test_emergency_interceptor_keyword_detection(self):
        """Test EmergencyInterceptor detects all red flag keywords."""
        interceptor = EmergencyInterceptor()

        # Test various emergency symptoms
        emergencies = [
            "胸痛",
            "胸闷",
            "大出血",
            "意识模糊",
            "呼吸困难",
            "中风",
            "休克",
        ]

        for symptom in emergencies:
            result = interceptor.intercept(f"我{symptom}")
            assert result is not None, f"Failed to detect: {symptom}"
            assert result in symptom or symptom in result

    def test_partial_match_emergency_detection(self):
        """Test partial match emergency detection."""
        interceptor = EmergencyInterceptor()

        # Partial matches should still trigger
        partial_inputs = [
            "我胸痛很严重",
            "出现胸闷症状",
            "感觉意识模糊",
        ]

        for inp in partial_inputs:
            result = interceptor.intercept(inp)
            assert result is not None, f"Failed to detect partial: {inp}"

    def test_non_emergency_returns_none(self):
        """Test that non-emergency inputs return None."""
        interceptor = EmergencyInterceptor()

        normal_inputs = [
            "我有点头痛",
            "想挂个内科",
            "高血压怎么办",
            "请问糖尿病的症状",
        ]

        for inp in normal_inputs:
            result = interceptor.intercept(inp)
            assert result is None, f"False positive for: {inp}"

    def test_emergency_blocks_booking(self):
        """Test that emergency detection blocks booking flow."""
        app = create_app()
        client = TestClient(app)

        # Create session
        response = client.post("/sessions")
        session_id = response.json()["session_id"]

        # Try to book appointment with emergency symptom
        response = client.post(
            f"/chat/{session_id}",
            json={"content": "我胸痛，要挂心内科"}
        )
        assert response.status_code == 200
        data = response.json()

        # Should NOT proceed to booking - should be red_flag
        assert data["intent"] == "red_flag"

        # Response should mention emergency
        response_text = data["response"]
        assert any(kw in response_text for kw in ["120", "急救", "紧急", "立即"])

    def test_intent_classifier_red_flag_priority(self):
        """Test that RED_FLAG intent has highest priority in classifier."""
        classifier = IntentClassifier()

        # Red flag symptoms should always be classified as RED_FLAG
        red_flag_inputs = [
            "胸痛",
            "胸闷",
            "呼吸困难",
            "意识模糊",
        ]

        for inp in red_flag_inputs:
            result = classifier.classify(inp)
            assert result.intent == Intent.RED_FLAG, f"Failed for: {inp}"

    def test_emergency_response_content(self):
        """Test that emergency response contains required elements."""
        interceptor = EmergencyInterceptor()

        # Get response for known emergency
        response = interceptor.get_emergency_response("胸痛")

        assert "紧急" in response or "120" in response
        assert "就医" in response or "急救" in response

    def test_radiation_symptom_detection(self):
        """Test detection of symptoms with radiation description."""
        interceptor = EmergencyInterceptor()

        # Symptom with radiation should be detected when it contains known emergency keywords
        inputs = [
            "胸痛放射到左肩",
            "胸痛辐射到背部",
        ]

        for inp in inputs:
            result = interceptor.intercept(inp)
            assert result is not None, f"Failed to detect radiation: {inp}"
