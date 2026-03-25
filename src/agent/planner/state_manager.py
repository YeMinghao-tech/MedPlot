"""State manager for dialog flow."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any

from src.agent.planner.intent_classifier import Intent


class State(Enum):
    """Dialog states."""

    GREETING = "greeting"  # 初始问候
    SYMPTOM_COLLECTION = "symptom_collection"  # 症状收集
    DEPARTMENT_RECOMMENDATION = "department_recommendation"  # 科室推荐
    CASE_CONFIRMATION = "case_confirmation"  # 病历确认
    BOOKING = "booking"  # 挂号
    MEDICAL_KNOWLEDGE = "medical_knowledge"  # 科普
    COMPLETED = "completed"  # 完成
    RED_FLAG = "red_flag"  # 红线拦截


@dataclass
class StateTransition:
    """Represents a state transition."""

    from_state: State
    to_state: State
    trigger: str  # What triggered this transition


@dataclass
class PatientState:
    """Accumulated patient information during dialog."""

    symptoms: list = field(default_factory=list)
    department: Optional[str] = None
    doctor: Optional[str] = None
    schedule_id: Optional[str] = None
    medical_record: Optional[Dict[str, Any]] = None
    extracted_entities: Optional[Dict[str, Any]] = None
    message_history: list = field(default_factory=list)

    def add_symptom(self, symptom: str):
        """Add a symptom to the list."""
        if symptom not in self.symptoms:
            self.symptoms.append(symptom)

    def is_complete(self) -> bool:
        """Check if enough information has been collected."""
        return bool(self.department and self.symptoms)


class StateManager:
    """Manages dialog state transitions.

    State flow:
    GREETING -> SYMPTOM_COLLECTION -> DEPARTMENT_RECOMMENDATION
                                           -> CASE_CONFIRMATION -> BOOKING -> COMPLETED
              -> MEDICAL_KNOWLEDGE -> ... -> SYMPTOM_COLLECTION
              -> RED_FLAG (from any state)
    """

    # Valid state transitions
    TRANSITIONS: Dict[State, list] = {
        State.GREETING: [
            StateTransition(State.GREETING, State.SYMPTOM_COLLECTION, "symptom_start"),
            StateTransition(State.GREETING, State.MEDICAL_KNOWLEDGE, "knowledge_query"),
        ],
        State.SYMPTOM_COLLECTION: [
            StateTransition(State.SYMPTOM_COLLECTION, State.SYMPTOM_COLLECTION, "more_symptoms"),
            StateTransition(State.SYMPTOM_COLLECTION, State.DEPARTMENT_RECOMMENDATION, "symptoms_complete"),
            StateTransition(State.SYMPTOM_COLLECTION, State.MEDICAL_KNOWLEDGE, "knowledge_query"),
            StateTransition(State.SYMPTOM_COLLECTION, State.RED_FLAG, "emergency_detected"),
        ],
        State.DEPARTMENT_RECOMMENDATION: [
            StateTransition(State.DEPARTMENT_RECOMMENDATION, State.DEPARTMENT_RECOMMENDATION, "dept_change"),
            StateTransition(State.DEPARTMENT_RECOMMENDATION, State.CASE_CONFIRMATION, "dept_confirmed"),
            StateTransition(State.DEPARTMENT_RECOMMENDATION, State.MEDICAL_KNOWLEDGE, "knowledge_query"),
        ],
        State.CASE_CONFIRMATION: [
            StateTransition(State.CASE_CONFIRMATION, State.BOOKING, "case_confirmed"),
            StateTransition(State.CASE_CONFIRMATION, State.SYMPTOM_COLLECTION, "case_incomplete"),
            StateTransition(State.CASE_CONFIRMATION, State.MEDICAL_KNOWLEDGE, "knowledge_query"),
        ],
        State.BOOKING: [
            StateTransition(State.BOOKING, State.COMPLETED, "booking_success"),
            StateTransition(State.BOOKING, State.BOOKING, "booking_retry"),
            StateTransition(State.BOOKING, State.COMPLETED, "booking_skip"),
        ],
        State.MEDICAL_KNOWLEDGE: [
            StateTransition(State.MEDICAL_KNOWLEDGE, State.SYMPTOM_COLLECTION, "back_to_consultation"),
            StateTransition(State.MEDICAL_KNOWLEDGE, State.GREETING, "restart"),
        ],
        State.RED_FLAG: [
            # Red flag is terminal for this session
        ],
        State.COMPLETED: [
            StateTransition(State.COMPLETED, State.GREETING, "new_session"),
        ],
    }

    def __init__(self):
        """Initialize the state manager."""
        self.current_state = State.GREETING
        self.patient_state = PatientState()
        self.transition_history = []

    def transition(self, intent: Intent, context: Optional[Dict[str, Any]] = None) -> State:
        """Determine next state based on current state and intent.

        Args:
            intent: Classified user intent.
            context: Optional context dict with additional info.

        Returns:
            Next state.
        """
        context = context or {}

        # Red flag is terminal - stay in red flag state
        if intent == Intent.RED_FLAG:
            self.current_state = State.RED_FLAG
            return self.current_state

        # Find valid transition
        valid_next_states = self.TRANSITIONS.get(self.current_state, [])

        for transition in valid_next_states:
            if self._matches_intent(intent, transition.trigger, context):
                self._record_transition(transition)
                self.current_state = transition.to_state
                return self.current_state

        # No matching transition - stay in current state
        return self.current_state

    def _matches_intent(self, intent: Intent, trigger: str, context: Dict[str, Any]) -> bool:
        """Check if intent matches trigger."""
        trigger_mapping = {
            "symptom_start": Intent.MEDICAL_CONSULTATION,
            "more_symptoms": Intent.MEDICAL_CONSULTATION,
            "symptoms_complete": Intent.CONFIRM,
            "knowledge_query": Intent.MEDICAL_KNOWLEDGE,
            "dept_change": Intent.MEDICAL_CONSULTATION,
            "dept_confirmed": Intent.CONFIRM,
            "case_confirmed": Intent.CONFIRM,
            "case_incomplete": Intent.MEDICAL_CONSULTATION,
            "booking_success": Intent.APPOINTMENT_BOOKING,
            "booking_retry": Intent.APPOINTMENT_BOOKING,
            "booking_skip": Intent.CONFIRM,
            "back_to_consultation": Intent.MEDICAL_CONSULTATION,
            "restart": Intent.GREETING,
            "new_session": Intent.GREETING,
            "emergency_detected": Intent.RED_FLAG,
        }

        return trigger_mapping.get(trigger) == intent

    def _record_transition(self, transition: StateTransition):
        """Record transition in history."""
        self.transition_history.append(transition)

    def reset(self):
        """Reset to initial state."""
        self.current_state = State.GREETING
        self.patient_state = PatientState()
        self.transition_history = []

    def get_state(self) -> State:
        """Get current state."""
        return self.current_state

    def get_next_possible_states(self) -> list:
        """Get list of possible next states."""
        transitions = self.TRANSITIONS.get(self.current_state, [])
        return list(set(t.to_state for t in transitions))

    def is_terminal_state(self) -> bool:
        """Check if current state is terminal."""
        return self.current_state in [State.RED_FLAG, State.COMPLETED]
