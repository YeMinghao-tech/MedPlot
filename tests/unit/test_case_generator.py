"""Tests for Case Generator components."""

from src.tools.case_generator.entity_extractor import EntityExtractor, ExtractedEntities
from src.tools.case_generator.record_builder import MedicalRecord, RecordBuilder
from src.tools.case_generator.schema_validator import SchemaValidator, ValidationError


class TestEntityExtractor:
    """Test EntityExtractor functionality."""

    def test_extract_symptoms(self):
        """Test symptom extraction."""
        extractor = EntityExtractor()

        entities = extractor.extract("我发烧三天了，还咳嗽，肚子疼")

        assert "发热" in entities.symptoms or "发烧" in entities.symptoms
        assert "咳嗽" in entities.symptoms
        assert "腹痛" in entities.symptoms or "肚子疼" in entities.symptoms

    def test_extract_duration(self):
        """Test duration extraction."""
        extractor = EntityExtractor()

        entities = extractor.extract("头痛已经持续5天了")

        assert entities.symptom_duration is not None
        assert "5天" in entities.symptom_duration

    def test_extract_severity(self):
        """Test severity extraction."""
        extractor = EntityExtractor()

        entities = extractor.extract("我头痛非常严重")

        assert entities.severity == "严重"

    def test_extract_allergies(self):
        """Test allergy extraction."""
        extractor = EntityExtractor()

        entities = extractor.extract("我对青霉素过敏，还对头孢过敏")

        assert len(entities.allergies) >= 1
        assert "青霉素" in entities.allergies

    def test_extract_medications(self):
        """Test medication extraction."""
        extractor = EntityExtractor()

        entities = extractor.extract("我正在服用降压药和阿司匹林")

        assert len(entities.medications) >= 1
        # The medication text is captured (may be combined)
        assert any("降压药" in m or "阿司匹林" in m for m in entities.medications)

    def test_extract_chief_complaint(self):
        """Test chief complaint extraction."""
        extractor = EntityExtractor()

        entities = extractor.extract("主要症状是发热咳嗽")

        assert entities.chief_complaint is not None

    def test_extract_empty_conversation(self):
        """Test extraction from empty conversation."""
        extractor = EntityExtractor()

        entities = extractor.extract("")

        assert entities.symptoms == []
        assert entities.allergies == []
        assert entities.medications == []

    def test_extracted_entities_to_dict(self):
        """Test converting entities to dictionary."""
        entities = ExtractedEntities(
            chief_complaint="头痛",
            symptoms=["头痛", "发热"],
            severity="中等",
        )

        d = entities.to_dict()

        assert d["chief_complaint"] == "头痛"
        assert "头痛" in d["symptoms"]
        assert d["severity"] == "中等"


class TestRecordBuilder:
    """Test RecordBuilder functionality."""

    def test_build_basic_record(self):
        """Test building a basic medical record."""
        entities = ExtractedEntities(
            chief_complaint="头痛发热三天",
            symptoms=["头痛", "发热"],
            symptom_duration="3天",
            severity="中等",
        )

        builder = RecordBuilder()
        record = builder.build(entities)

        assert record.chief_complaint == "头痛发热三天"
        assert "头痛" in record.history_of_present_illness
        assert "发热" in record.history_of_present_illness
        assert record.raw_entities is not None

    def test_build_record_from_symptoms_only(self):
        """Test building record when chief complaint is empty."""
        entities = ExtractedEntities(
            symptoms=["咳嗽", "咳痰"],
            symptom_duration="一周",
        )

        builder = RecordBuilder()
        record = builder.build(entities)

        assert record.chief_complaint is not None
        assert "咳嗽" in record.chief_complaint

    def test_record_to_dict(self):
        """Test converting record to dictionary."""
        entities = ExtractedEntities(chief_complaint="测试主诉")
        builder = RecordBuilder()
        record = builder.build(entities)

        d = record.to_dict()

        assert "chief_complaint" in d
        assert d["chief_complaint"] == "测试主诉"

    def test_record_to_structured_text(self):
        """Test converting record to structured text."""
        entities = ExtractedEntities(
            chief_complaint="头痛",
            symptoms=["头痛"],
        )
        builder = RecordBuilder()
        record = builder.build(entities)

        text = record.to_structured_text()

        assert "【主诉】" in text
        assert "头痛" in text

    def test_allergy_history_no_allergies(self):
        """Test allergy history when no allergies reported."""
        entities = ExtractedEntities(
            chief_complaint="头痛",
            allergies=[],
        )

        builder = RecordBuilder()
        record = builder.build(entities)

        assert record.allergy_history == "无"


class TestSchemaValidator:
    """Test SchemaValidator functionality."""

    def test_validate_valid_record(self):
        """Test validating a valid record."""
        record = MedicalRecord(
            chief_complaint="头痛三天",
            history_of_present_illness="患者三天前开始头痛",
        )

        validator = SchemaValidator()
        result = validator.validate(record)

        assert result.is_valid == True
        assert len(result.errors) == 0

    def test_validate_empty_chief_complaint(self):
        """Test validation fails for empty chief complaint."""
        record = MedicalRecord(
            chief_complaint="",
        )

        validator = SchemaValidator()
        result = validator.validate(record)

        assert result.is_valid == False
        assert any(e.field == "chief_complaint" for e in result.errors)

    def test_validate_placeholder_chief_complaint(self):
        """Test validation warning for placeholder chief complaint."""
        record = MedicalRecord(
            chief_complaint="待补充",
        )

        validator = SchemaValidator()
        result = validator.validate(record)

        # Should have warning but still be valid
        assert any(e.severity == "warning" for e in result.errors)

    def test_validate_short_chief_complaint(self):
        """Test validation fails for too short chief complaint."""
        record = MedicalRecord(
            chief_complaint="头",
        )

        validator = SchemaValidator()
        result = validator.validate(record)

        assert result.is_valid == False

    def test_validate_too_long_field(self):
        """Test validation fails for too long fields."""
        record = MedicalRecord(
            chief_complaint="头痛",  # Short but valid
            history_of_present_illness="x" * 6000,  # Too long
        )

        validator = SchemaValidator()
        result = validator.validate(record)

        assert result.is_valid == False
        assert any("too long" in e.message for e in result.errors)

    def test_validation_result_error_messages(self):
        """Test getting error messages from validation result."""
        record = MedicalRecord(chief_complaint="")
        validator = SchemaValidator()
        result = validator.validate(record)

        assert len(result.error_messages) > 0

    def test_validate_dict(self):
        """Test validating dictionary representation."""
        data = {
            "chief_complaint": "头痛",
            "history_of_present_illness": "三天前开始",
        }

        validator = SchemaValidator()
        result = validator.validate_dict(data)

        assert result.is_valid == True
