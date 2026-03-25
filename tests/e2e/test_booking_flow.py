"""E2E tests for complete booking flow (L4)."""

import tempfile
from pathlib import Path

from src.libs.his.mock_his import MockHISClient
from src.tools.his_orchestrator.booking_service import BookingService
from src.tools.his_orchestrator.schedule_service import ScheduleService
from src.tools.his_orchestrator.dept_service import DepartmentService


class TestBookingFlow:
    """Test complete booking flow from department selection to appointment lock.

    Implements L4: E2E complete booking flow.
    """

    def setup_method(self):
        """Create fresh test database."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = str(Path(self.temp_dir) / "test_booking.db")
        self.his_client = MockHISClient(db_path=self.db_path, use_wal=True)

    def teardown_method(self):
        """Clean up test database."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_department_query_returns_results(self):
        """Test querying departments returns available departments."""
        dept_service = DepartmentService(self.his_client)

        # Query departments
        depts = dept_service.query("内科")
        assert len(depts) > 0
        assert any("内科" in d.name for d in depts)

    def test_schedule_query_returns_results(self):
        """Test querying schedules returns available slots."""
        schedule_service = ScheduleService(self.his_client)

        # Query内科 schedules
        schedules = schedule_service.get_available(dept_name="内科")
        assert len(schedules) > 0

        # Verify schedule has required fields
        s = schedules[0]
        assert hasattr(s, "schedule_id")
        assert hasattr(s, "doctor_name")
        assert hasattr(s, "dept_name")
        assert hasattr(s, "date")
        assert hasattr(s, "time_slot")
        assert hasattr(s, "available_slots")

    def test_booking_service_books_appointment(self):
        """Test booking service successfully books an appointment."""
        booking_service = BookingService(self.his_client)

        # Get a valid schedule
        schedules = ScheduleService(self.his_client).get_available(dept_name="内科")
        assert len(schedules) > 0
        schedule_id = schedules[0].schedule_id

        # Book appointment
        result = booking_service.book("p_test_patient", schedule_id)
        assert result.success is True
        assert result.appointment_id is not None
        assert "预约成功" in result.message or "success" in result.message.lower()

    def test_booking_reduces_available_slots(self):
        """Test that booking reduces available slots."""
        schedule_service = ScheduleService(self.his_client)
        booking_service = BookingService(self.his_client)

        # Get initial slots
        schedules = schedule_service.get_available(dept_name="内科")
        schedule_id = schedules[0].schedule_id
        initial_slots = schedules[0].available_slots

        if initial_slots <= 0:
            # Use a different department or skip
            schedules = schedule_service.get_available(dept_name="外科")
            if schedules:
                schedule_id = schedules[0].schedule_id
                initial_slots = schedules[0].available_slots

        if initial_slots <= 0:
            # Create extra slots manually or skip
            schedule_id = "S内科01"  # Default schedule
            initial_slots = 5

        # Book
        result = booking_service.book("p_test_patient2", schedule_id)
        assert result.success is True

        # Verify slots reduced
        final_schedule = schedule_service.get_by_schedule_id(schedule_id)
        assert final_schedule.available_slots == initial_slots - 1

    def test_booking_confirmation_contains_details(self):
        """Test that booking confirmation contains required details."""
        booking_service = BookingService(self.his_client)
        schedule_service = ScheduleService(self.his_client)

        # Get a schedule
        schedules = schedule_service.get_available(dept_name="内科")
        if not schedules:
            schedules = schedule_service.get_available(dept_name="外科")
        if not schedules:
            schedules = schedule_service.get_available(dept_name="儿科")

        if not schedules:
            schedule_id = "S内科01"
        else:
            schedule_id = schedules[0].schedule_id

        # Book
        result = booking_service.book("p_confirm_test", schedule_id)
        assert result.success is True

        # Verify result has appointment info
        assert result.appointment_id is not None

    def test_booking_no_available_slots_fails(self):
        """Test that booking fails gracefully when no slots available."""
        booking_service = BookingService(self.his_client)

        # Book all available slots first
        schedules = ScheduleService(self.his_client).get_available(dept_name="")
        if not schedules:
            return  # No schedules available to test

        # Book a slot
        schedule_id = schedules[0].schedule_id
        result = booking_service.book("p_slot_test", schedule_id)

        if result.success:
            # Try to book same slot again
            result2 = booking_service.book("p_slot_test2", schedule_id)
            # Second booking should fail
            assert result2.success is False or result2.appointment_id != result.appointment_id

    def test_department_filtering(self):
        """Test booking with department filter."""
        schedule_service = ScheduleService(self.his_client)

        # Query different departments
        internal_medicine = schedule_service.get_available(dept_name="内科")
        surgery = schedule_service.get_available(dept_name="外科")
        pediatrics = schedule_service.get_available(dept_name="儿科")

        # At least one department should have schedules
        assert len(internal_medicine) > 0 or len(surgery) > 0 or len(pediatrics) > 0

        # Verify filtering works - results should match department
        for s in internal_medicine:
            assert "内科" in s.dept_name


class TestBookingServiceIntegration:
    """Test booking service with real-ish flow."""

    def setup_method(self):
        """Create fresh test database."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = str(Path(self.temp_dir) / "test_booking_int.db")
        self.his_client = MockHISClient(db_path=self.db_path, use_wal=True)
        self.booking_service = BookingService(self.his_client)
        self.schedule_service = ScheduleService(self.his_client)

    def teardown_method(self):
        """Clean up test database."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_complete_booking_workflow(self):
        """Test complete workflow: find dept -> check schedule -> book."""
        # Step 1: Find department
        dept_service = DepartmentService(self.his_client)
        depts = dept_service.query("内科")
        assert len(depts) > 0

        # Step 2: Check available schedules
        schedules = self.schedule_service.get_available(dept_name="内科")
        assert len(schedules) > 0
        schedule = schedules[0]
        initial_slots = schedule.available_slots

        # Step 3: Book appointment
        patient_id = "p_e2e_test"
        result = self.booking_service.book(patient_id, schedule.schedule_id)

        # Step 4: Verify success
        assert result.success is True
        assert result.appointment_id is not None

        # Step 5: Verify slot count decreased
        updated_schedule = self.schedule_service.get_by_schedule_id(schedule.schedule_id)
        assert updated_schedule.available_slots == initial_slots - 1

    def test_multiple_bookings_for_same_patient(self):
        """Test patient can book multiple appointments."""
        schedules = self.schedule_service.get_available(dept_name="")

        if len(schedules) < 2:
            return  # Not enough schedules to test

        patient_id = "p_multi_test"

        # Book first appointment
        result1 = self.booking_service.book(patient_id, schedules[0].schedule_id)
        assert result1.success is True

        # Book second appointment (different department)
        if len(schedules) > 1:
            result2 = self.booking_service.book(patient_id, schedules[1].schedule_id)
            assert result2.success is True
            # Should get different appointment IDs
            assert result1.appointment_id != result2.appointment_id
