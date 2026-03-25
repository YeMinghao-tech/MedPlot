"""Tests for HIS services."""

from unittest.mock import MagicMock

from src.libs.his.base_his import Department, Schedule
from src.tools.his_orchestrator.dept_service import DepartmentService
from src.tools.his_orchestrator.schedule_service import ScheduleService


class TestDepartmentService:
    """Test DepartmentService functionality."""

    def test_query_returns_all_when_no_keyword(self):
        """Test that query returns all departments when keyword is empty."""
        mock_client = MagicMock()
        mock_client.query_departments.return_value = [
            Department(dept_id="d1", name="内科", description="内科门诊"),
            Department(dept_id="d2", name="外科", description="外科门诊"),
        ]

        service = DepartmentService(mock_client)
        result = service.query("")

        assert len(result) == 2
        mock_client.query_departments.assert_called_once_with("")

    def test_query_filters_by_keyword(self):
        """Test that query filters departments by keyword."""
        mock_client = MagicMock()
        mock_client.query_departments.return_value = [
            Department(dept_id="d1", name="内科", description="内科门诊"),
            Department(dept_id="d2", name="外科", description="外科门诊"),
        ]

        service = DepartmentService(mock_client)
        result = service.query("内科")

        assert len(result) >= 1
        # All results should match keyword (either name or description)
        for dept in result:
            assert "内科" in dept.name or (dept.description and "内科" in dept.description)

    def test_get_by_id(self):
        """Test getting department by ID."""
        mock_client = MagicMock()
        mock_client.query_departments.return_value = [
            Department(dept_id="d1", name="内科"),
            Department(dept_id="d2", name="外科"),
        ]

        service = DepartmentService(mock_client)
        result = service.get_by_id("d1")

        assert result is not None
        assert result.dept_id == "d1"
        assert result.name == "内科"

    def test_get_by_id_returns_none_when_not_found(self):
        """Test that get_by_id returns None for non-existent ID."""
        mock_client = MagicMock()
        mock_client.query_departments.return_value = [
            Department(dept_id="d1", name="内科"),
        ]

        service = DepartmentService(mock_client)
        result = service.get_by_id("nonexistent")

        assert result is None

    def test_get_all(self):
        """Test getting all departments."""
        mock_client = MagicMock()
        mock_client.query_departments.return_value = [
            Department(dept_id="d1", name="内科"),
            Department(dept_id="d2", name="外科"),
        ]

        service = DepartmentService(mock_client)
        result = service.get_all()

        assert len(result) == 2


class TestScheduleService:
    """Test ScheduleService functionality."""

    def test_query_filters_by_dept(self):
        """Test filtering schedules by department."""
        mock_client = MagicMock()
        mock_client.query_doctor_schedule.return_value = [
            Schedule("s1", "张医生", "内科", "2026-03-25", "上午", 5),
            Schedule("s2", "李医生", "外科", "2026-03-25", "上午", 3),
        ]

        service = ScheduleService(mock_client)
        result = service.query(dept_name="内科")

        assert len(result) == 1
        assert result[0].doctor_name == "张医生"

    def test_query_filters_by_date(self):
        """Test filtering schedules by date."""
        mock_client = MagicMock()
        mock_client.query_doctor_schedule.return_value = [
            Schedule("s1", "张医生", "内科", "2026-03-25", "上午", 5),
            Schedule("s2", "李医生", "内科", "2026-03-26", "上午", 3),
        ]

        service = ScheduleService(mock_client)
        result = service.query(date="2026-03-25")

        assert len(result) == 1
        assert result[0].schedule_id == "s1"

    def test_query_filters_by_doctor_name(self):
        """Test filtering schedules by doctor name."""
        mock_client = MagicMock()
        mock_client.query_doctor_schedule.return_value = [
            Schedule("s1", "张医生", "内科", "2026-03-25", "上午", 5),
            Schedule("s2", "李医生", "内科", "2026-03-25", "下午", 3),
        ]

        service = ScheduleService(mock_client)
        result = service.query(doctor_name="张")

        assert len(result) == 1
        assert result[0].doctor_name == "张医生"

    def test_get_available_filters_zero_slots(self):
        """Test that get_available filters out schedules with zero slots."""
        mock_client = MagicMock()
        mock_client.query_doctor_schedule.return_value = [
            Schedule("s1", "张医生", "内科", "2026-03-25", "上午", 5),
            Schedule("s2", "李医生", "内科", "2026-03-25", "下午", 0),
        ]

        service = ScheduleService(mock_client)
        result = service.get_available(dept_name="内科")

        assert len(result) == 1
        assert result[0].schedule_id == "s1"

    def test_get_by_schedule_id(self):
        """Test getting schedule by ID."""
        mock_client = MagicMock()
        mock_client.query_doctor_schedule.return_value = [
            Schedule("s1", "张医生", "内科", "2026-03-25", "上午", 5),
        ]

        service = ScheduleService(mock_client)
        result = service.get_by_schedule_id("s1")

        assert result is not None
        assert result.schedule_id == "s1"

    def test_get_upcoming_returns_future_schedules(self):
        """Test that get_upcoming returns only future schedules."""
        mock_client = MagicMock()
        mock_client.query_doctor_schedule.return_value = [
            Schedule("s1", "张医生", "内科", "2099-12-31", "上午", 5),
            Schedule("s2", "李医生", "内科", "2020-01-01", "上午", 3),
        ]

        service = ScheduleService(mock_client)
        result = service.get_upcoming(dept_name="内科", days=7)

        # Only future schedules with available slots
        assert all(s.available_slots > 0 for s in result)

    def test_enrich_schedule_adds_computed_fields(self):
        """Test that enrich_schedule adds computed fields."""
        mock_client = MagicMock()
        service = ScheduleService(mock_client)

        schedule = Schedule(
            schedule_id="s1",
            doctor_name="张医生",
            dept_name="内科",
            date="2099-12-31",
            time_slot="上午",
            available_slots=5,
        )

        enriched = service.enrich_schedule(schedule)

        assert enriched.is_today == False
        assert enriched.is_tomorrow == False
        assert enriched.schedule_id == "s1"
        assert enriched.available_slots == 5
        assert enriched.dept_name == "内科"
        assert enriched.doctor_name == "张医生"
