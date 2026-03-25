"""Medical record builder from extracted entities."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.tools.case_generator.entity_extractor import ExtractedEntities


@dataclass
class MedicalRecord:
    """Structured medical record.

    Contains the standard sections of a medical case:
    - Chief complaint (主诉)
    - History of present illness (现病史)
    - Past medical history (既往史)
    - Personal history (个人史)
    - Family history (家族史)
    - Allergies (过敏史)
    """

    # Required fields
    chief_complaint: str
    patient_id: Optional[str] = None

    # History sections
    history_of_present_illness: str = ""
    past_medical_history: str = ""
    personal_history: str = ""
    family_history: str = ""
    allergy_history: str = ""

    # Extracted raw data
    raw_entities: Optional[Dict[str, Any]] = None

    # Metadata
    created_at: Optional[str] = None
    source_session: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "patient_id": self.patient_id,
            "chief_complaint": self.chief_complaint,
            "history_of_present_illness": self.history_of_present_illness,
            "past_medical_history": self.past_medical_history,
            "personal_history": self.personal_history,
            "family_history": self.family_history,
            "allergy_history": self.allergy_history,
            "raw_entities": self.raw_entities,
            "created_at": self.created_at,
            "source_session": self.source_session,
        }

    def to_structured_text(self) -> str:
        """Convert to human-readable structured text."""
        sections = []

        sections.append("【主诉】")
        sections.append(f"  {self.chief_complaint}")

        if self.history_of_present_illness:
            sections.append("\n【现病史】")
            sections.append(f"  {self.history_of_present_illness}")

        if self.allergy_history:
            sections.append("\n【过敏史】")
            sections.append(f"  {self.allergy_history}")

        if self.past_medical_history:
            sections.append("\n【既往史】")
            sections.append(f"  {self.past_medical_history}")

        if self.personal_history:
            sections.append("\n【个人史】")
            sections.append(f"  {self.personal_history}")

        if self.family_history:
            sections.append("\n【家族史】")
            sections.append(f"  {self.family_history}")

        return "\n".join(sections)


class RecordBuilder:
    """Builds structured medical records from extracted entities.

    Takes the raw ExtractedEntities and transforms them into a
    properly formatted MedicalRecord with human-readable narratives.
    """

    def __init__(self):
        """Initialize the record builder."""
        pass

    def build(
        self,
        entities: ExtractedEntities,
        patient_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> MedicalRecord:
        """Build a structured medical record from entities.

        Args:
            entities: Extracted entities from conversation.
            patient_id: Optional patient identifier.
            session_id: Optional session identifier.

        Returns:
            MedicalRecord with structured content.
        """
        from datetime import datetime

        # Build chief complaint
        chief_complaint = self._build_chief_complaint(entities)

        # Build HPI (History of Present Illness)
        hpi = self._build_hpi(entities)

        # Build allergy history
        allergies = self._build_allergy_history(entities)

        # Build past medical history
        past = self._build_past_history(entities)

        # Build personal history
        personal = self._build_personal_history(entities)

        # Build family history
        family = self._build_family_history(entities)

        return MedicalRecord(
            chief_complaint=chief_complaint,
            patient_id=patient_id,
            history_of_present_illness=hpi,
            past_medical_history=past,
            personal_history=personal,
            family_history=family,
            allergy_history=allergies,
            raw_entities=entities.to_dict(),
            created_at=datetime.now().isoformat(),
            source_session=session_id,
        )

    def _build_chief_complaint(self, entities: ExtractedEntities) -> str:
        """Build chief complaint string."""
        if entities.chief_complaint:
            return entities.chief_complaint

        parts = []
        if entities.symptoms:
            unique_symptoms = list(dict.fromkeys(entities.symptoms))
            parts.append("、".join(unique_symptoms[:5]))

        if entities.symptom_duration:
            parts.append(f"持续{entities.symptom_duration}")

        if entities.severity:
            parts.append(f"程度{entities.severity}")

        return "，".join(parts) if parts else "待补充"

    def _build_hpi(self, entities: ExtractedEntities) -> str:
        """Build History of Present Illness."""
        parts = []

        # Symptoms
        if entities.symptoms:
            unique_symptoms = list(dict.fromkeys(entities.symptoms))
            symptoms_text = "、".join(unique_symptoms)
            parts.append(f"患者主要表现为{symptoms_text}")

        # Duration
        if entities.symptom_duration:
            parts.append(f"持续{entities.symptom_duration}")

        # Severity
        if entities.severity:
            parts.append(f"程度{entities.severity}")

        # Location
        if entities.location:
            parts.append(f"部位为{entities.location}")

        # Triggers
        if entities.triggers:
            triggers = "、".join(entities.triggers)
            parts.append(f"诱因包括{triggers}")

        # Relievers
        if entities.relievers:
            relievers = "、".join(entities.relievers)
            parts.append(f"缓解因素有{relievers}")

        return "，".join(parts) if parts else "现病史待补充"

    def _build_allergy_history(self, entities: ExtractedEntities) -> str:
        """Build allergy history."""
        if entities.allergies:
            return "、".join(entities.allergies)
        return "无"

    def _build_past_history(self, entities: ExtractedEntities) -> str:
        """Build past medical history."""
        if entities.past_conditions:
            return "、".join(entities.past_conditions)
        return "无特殊"

    def _build_personal_history(self, entities: ExtractedEntities) -> str:
        """Build personal history."""
        parts = []

        if entities.medications:
            meds = "、".join(entities.medications)
            parts.append(f"正在服用：{meds}")

        return "；".join(parts) if parts else "无特殊"

    def _build_family_history(self, entities: ExtractedEntities) -> str:
        """Build family history."""
        if entities.family_history:
            return "、".join(entities.family_history)
        return "无特殊家族史"
