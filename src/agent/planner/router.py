"""Router for dispatching tools based on intent and state."""

from dataclasses import dataclass
from typing import Optional, Dict, Any

from src.agent.planner.intent_classifier import Intent, IntentClassifier
from src.agent.planner.state_manager import State, StateManager


@dataclass
class ToolCall:
    """Represents a tool call request."""

    tool_name: str
    parameters: Dict[str, Any]
    reasoning: str


class Router:
    """Routes user requests to appropriate tools.

    Dispatches to:
    - RAG Engine for medical knowledge queries
    - HIS services for department/schedule queries
    - Case Generator for medical record generation
    - BookingService for appointment booking
    """

    def __init__(
        self,
        rag_engine=None,
        department_service=None,
        schedule_service=None,
        case_generator=None,
        booking_service=None,
        llm_client=None,
    ):
        """Initialize the router.

        Args:
            rag_engine: RAG engine for knowledge queries.
            department_service: Department query service.
            schedule_service: Schedule query service.
            case_generator: Medical record generator.
            booking_service: Appointment booking service.
            llm_client: LLM client for responses.
        """
        self.rag_engine = rag_engine
        self.department_service = department_service
        self.schedule_service = schedule_service
        self.case_generator = case_generator
        self.booking_service = booking_service
        self.llm = llm_client

        # Initialize classifier and state manager
        self.classifier = IntentClassifier(llm_client=llm_client)
        self.state_manager = StateManager()

    def route(self, user_input: str, patient_id: Optional[str] = None) -> Dict[str, Any]:
        """Route user input to appropriate tool and execute.

        Args:
            user_input: User's input text.
            patient_id: Optional patient identifier.

        Returns:
            Dict with response and tool call info.
        """
        # Step 1: Classify intent
        intent_result = self.classifier.classify(user_input)
        intent = intent_result.intent

        # Step 2: Get context for state transition
        context = {
            "patient_id": patient_id,
            "patient_state": self.state_manager.patient_state,
        }

        # Step 3: Transition state
        new_state = self.state_manager.transition(intent, context)
        current_state = self.state_manager.get_state()

        # Step 4: Generate response based on intent + state
        response = self._generate_response(intent, new_state, user_input, context)

        return {
            "intent": intent.value,
            "intent_confidence": intent_result.confidence,
            "state": new_state.value,
            "response": response,
            "patient_state": self.state_manager.patient_state,
        }

    def _generate_response(
        self,
        intent: Intent,
        state: State,
        user_input: str,
        context: Dict[str, Any],
    ) -> str:
        """Generate response based on intent and state."""
        patient_state = context.get("patient_state")
        patient_id = context.get("patient_id")

        # RED_FLAG: Return emergency guidance
        if intent == Intent.RED_FLAG:
            return self._handle_red_flag(user_input)

        # GREETING
        if intent == Intent.GREETING:
            return "您好！我是医疗导诊助手。请描述您的症状，我来帮您分诊。"

        # MEDICAL_KNOWLEDGE: Query RAG
        if intent == Intent.MEDICAL_KNOWLEDGE:
            return self._handle_knowledge_query(user_input)

        # APPOINTMENT_BOOKING
        if intent == Intent.APPOINTMENT_BOOKING:
            return self._handle_booking(user_input, patient_id)

        # CONFIRM: Handle confirmations
        if intent == Intent.CONFIRM:
            return self._handle_confirmation(state, patient_state)

        # MEDICAL_CONSULTATION: Default handling
        return self._handle_consultation(user_input, patient_state)

    def _handle_red_flag(self, user_input: str) -> str:
        """Handle red flag emergency."""
        return (
            "【紧急提示】检测到可能危及生命的症状。\n\n"
            "请立即：\n"
            "1. 拨打120急救电话\n"
            "2. 联系就近医院急诊\n"
            "3. 如有冠心病药物可在医生指导下服用\n\n"
            "您的生命安全是第一位的，请立即就医！"
        )

    def _handle_knowledge_query(self, query: str) -> str:
        """Handle medical knowledge query via RAG."""
        if not self.rag_engine:
            return "抱歉，医学知识库暂不可用。建议您直接咨询医生获取准确信息。"

        try:
            results = self.rag_engine.query(query, top_k=3)
            if not results:
                return "抱歉，我在医学知识库中没有找到相关信息，建议您咨询医生。"

            # Format response
            response_parts = ["根据医学资料：\n"]
            for i, r in enumerate(results[:3], 1):
                response_parts.append(f"{i}. {r.text[:200]}...")
            return "\n".join(response_parts)
        except Exception as e:
            return f"查询医学知识时出现错误：{str(e)}"

    def _handle_booking(self, query: str, patient_id: Optional[str]) -> str:
        """Handle appointment booking request."""
        if not patient_id:
            return "请先提供您的患者ID才能进行挂号。"

        if not self.schedule_service:
            return "抱歉，挂号服务暂不可用。"

        try:
            # Extract any department preference from query
            dept = self._extract_department(query)

            # Query available schedules
            schedules = self.schedule_service.get_available(dept_name=dept)
            if not schedules:
                return f"抱歉，{dept or '内科'}目前没有可预约的号源。"

            # Format response
            response_parts = ["可预约的医生：\n"]
            for s in schedules[:5]:
                response_parts.append(
                    f"- {s.doctor_name}（{s.dept_name}）"
                    f" {s.date} {s.time_slot} "
                    f"剩余{s.available_slots}个号"
                )
            return "\n".join(response_parts)
        except Exception as e:
            return f"查询号源时出现错误：{str(e)}"

    def _handle_confirmation(self, state: State, patient_state) -> str:
        """Handle confirmation intents."""
        if state == State.DEPARTMENT_RECOMMENDATION:
            return "好的，您想挂哪个科室？"
        elif state == State.CASE_CONFIRMATION:
            return "好的，请确认您的病历信息是否正确。"
        elif state == State.BOOKING:
            return "好的，正在为您处理挂号..."
        return "好的，我明白了。"

    def _handle_consultation(self, query: str, patient_state) -> str:
        """Handle medical consultation."""
        # Update patient state with new symptoms
        if patient_state:
            patient_state.add_symptom(query)

        return (
            f"了解了。{len(patient_state.symptoms)}个症状已记录。\n"
            "请继续描述：\n"
            "- 症状持续多长时间了？\n"
            "- 严重程度如何（轻微/中等/严重）？\n"
            "- 还有其他不舒服的地方吗？"
        )

    def _extract_department(self, query: str) -> Optional[str]:
        """Extract department name from query."""
        dept_keywords = ["内科", "外科", "儿科", "妇产科", "骨科", "皮肤科", "眼科", "耳鼻喉科"]
        for dept in dept_keywords:
            if dept in query:
                return dept
        return None
