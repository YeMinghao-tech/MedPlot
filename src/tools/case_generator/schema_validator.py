"""Schema validator for medical records."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from src.tools.case_generator.record_builder import MedicalRecord


@dataclass
class ValidationError:
    """A single validation error."""

    field: str
    message: str
    severity: str = "error"  # "error" or "warning"


@dataclass
class ValidationResult:
    """Result of schema validation."""

    is_valid: bool
    errors: List[ValidationError] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []

    @property
    def error_messages(self) -> List[str]:
        """Get list of error messages."""
        return [f"[{e.severity}] {e.field}: {e.message}" for e in self.errors]

    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return any(e.severity == "warning" for e in self.errors)


class SchemaValidator:
    """Validates medical records against required schema.

    Checks:
    - Required fields are present and non-empty
    - Field lengths are within acceptable ranges
    - Chief complaint is meaningful (not just placeholder)
    """

    # Required fields that must be non-empty
    REQUIRED_FIELDS = ["chief_complaint"]

    # Minimum length for chief complaint
    MIN_CHIEF_COMPLAINT_LENGTH = 2

    # Maximum length for any field
    MAX_FIELD_LENGTH = 5000

    def __init__(self):
        """Initialize the schema validator."""
        pass

    def validate(self, record: MedicalRecord) -> ValidationResult:
        """Validate a medical record.

        Args:
            record: The medical record to validate.

        Returns:
            ValidationResult with is_valid flag and any errors.
        """
        errors: List[ValidationError] = []

        # Check required fields
        for field_name in self.REQUIRED_FIELDS:
            value = getattr(record, field_name, None)
            if not value or (isinstance(value, str) and not value.strip()):
                errors.append(ValidationError(
                    field=field_name,
                    message=f"{field_name} is required and cannot be empty",
                    severity="error",
                ))

        # Validate chief complaint
        if record.chief_complaint:
            cc = record.chief_complaint.strip()
            if len(cc) < self.MIN_CHIEF_COMPLAINT_LENGTH:
                errors.append(ValidationError(
                    field="chief_complaint",
                    message=f"Chief complaint too short (min {self.MIN_CHIEF_COMPLAINT_LENGTH} chars)",
                    severity="error",
                ))
            if cc in ["待补充", "无", "暂无", "未提供"]:
                errors.append(ValidationError(
                    field="chief_complaint",
                    message="Chief complaint is a placeholder",
                    severity="warning",
                ))
            if len(cc) > self.MAX_FIELD_LENGTH:
                errors.append(ValidationError(
                    field="chief_complaint",
                    message=f"Chief complaint too long (max {self.MAX_FIELD_LENGTH} chars)",
                    severity="error",
                ))

        # Validate other text fields
        for field_name in ["history_of_present_illness", "past_medical_history",
                           "personal_history", "family_history", "allergy_history"]:
            value = getattr(record, field_name, None)
            if value and len(value) > self.MAX_FIELD_LENGTH:
                errors.append(ValidationError(
                    field=field_name,
                    message=f"{field_name} too long (max {self.MAX_FIELD_LENGTH} chars)",
                    severity="error",
                ))

        # Validate patient_id format if provided
        patient_id = getattr(record, "patient_id", None)
        if patient_id:
            if len(patient_id) > 100:
                errors.append(ValidationError(
                    field="patient_id",
                    message="Patient ID too long",
                    severity="error",
                ))

        is_valid = all(e.severity != "error" for e in errors)

        return ValidationResult(is_valid=is_valid, errors=errors)

    def validate_dict(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate a dictionary representation of a record.

        Args:
            data: Dictionary with medical record fields.

        Returns:
            ValidationResult with is_valid flag and any errors.
        """
        # Create a minimal object to validate
        class _RecordProxy:
            def __init__(self, d):
                for k, v in d.items():
                    setattr(self, k, v)

        record = _RecordProxy(data)
        return self.validate(record)
