"""Tests for BookingService."""

from unittest.mock import MagicMock

from src.libs.his.base_his import AppointmentResult, Schedule
from src.tools.his_orchestrator.booking_service import BookingService


class TestBookingService:
    """Test BookingService functionality."""

    def test_book_success(self):
        """Test successful booking."""
        mock_client = MagicMock()
        mock_client.book_appointment.return_value = AppointmentResult(
            success=True,
            appointment_id="APT001",
            message="预约成功",
        )

        # Setup schedule service mock
        mock_client.query_doctor_schedule.return_value = [
            Schedule("s1", "张医生", "内科", "2026-03-25", "上午", 5),
        ]

        service = BookingService(mock_client)
        result = service.book("patient1", "s1")

        assert result.success == True
        assert result.appointment_id == "APT001"

    def test_book_no_schedule(self):
        """Test booking when schedule not found."""
        mock_client = MagicMock()
        mock_client.query_doctor_schedule.return_value = []

        service = BookingService(mock_client)
        result = service.book("patient1", "nonexistent")

        assert result.success == False
        assert "not found" in result.message

    def test_book_no_slots(self):
        """Test booking when no slots available."""
        mock_client = MagicMock()
        mock_client.query_doctor_schedule.return_value = [
            Schedule("s1", "张医生", "内科", "2026-03-25", "上午", 0),
        ]

        service = BookingService(mock_client)
        result = service.book("patient1", "s1")

        assert result.success == False
        assert "No available slots" in result.message

    def test_confirm_booking(self):
        """Test getting booking confirmation."""
        mock_client = MagicMock()
        mock_client.query_doctor_schedule.return_value = [
            Schedule("s1", "张医生", "内科", "2026-03-25", "上午", 5),
        ]

        service = BookingService(mock_client)
        confirmation = service.confirm_booking("patient1", "s1")

        assert confirmation is not None
        assert confirmation.patient_id == "patient1"
        assert confirmation.schedule_id == "s1"
        assert confirmation.doctor_name == "张医生"
        assert confirmation.dept_name == "内科"
        assert confirmation.confirmation_code is not None

    def test_confirm_booking_not_found(self):
        """Test confirmation when schedule not found."""
        mock_client = MagicMock()
        mock_client.query_doctor_schedule.return_value = []

        service = BookingService(mock_client)
        confirmation = service.confirm_booking("patient1", "nonexistent")

        assert confirmation is None

    def test_check_availability_true(self):
        """Test checking availability when slots available."""
        mock_client = MagicMock()
        mock_client.query_doctor_schedule.return_value = [
            Schedule("s1", "张医生", "内科", "2026-03-25", "上午", 5),
        ]

        service = BookingService(mock_client)
        available = service.check_availability("s1")

        assert available == True

    def test_check_availability_false(self):
        """Test checking availability when no slots."""
        mock_client = MagicMock()
        mock_client.query_doctor_schedule.return_value = [
            Schedule("s1", "张医生", "内科", "2026-03-25", "上午", 0),
        ]

        service = BookingService(mock_client)
        available = service.check_availability("s1")

        assert available == False

    def test_check_availability_not_found(self):
        """Test checking availability for nonexistent schedule."""
        mock_client = MagicMock()
        mock_client.query_doctor_schedule.return_value = []

        service = BookingService(mock_client)
        available = service.check_availability("nonexistent")

        assert available == False

    def test_generate_confirmation_code(self):
        """Test confirmation code generation."""
        mock_client = MagicMock()
        service = BookingService(mock_client)

        code1 = service._generate_confirmation_code("patient1", "s1")
        code2 = service._generate_confirmation_code("patient1", "s1")

        # Same inputs should produce same code
        assert code1 == code2
        # Code should be 6 chars alphanumeric
        assert len(code1) == 6
        assert code1.isalnum()

    def test_cancel_not_implemented(self):
        """Test that cancel is not yet implemented."""
        mock_client = MagicMock()
        service = BookingService(mock_client)

        result = service.cancel("patient1", "s1")

        assert result.success == False
        assert "not yet implemented" in result.message
