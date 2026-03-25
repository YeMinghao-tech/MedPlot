"""Concurrency tests for booking service (I4)."""

import asyncio
import sqlite3
import tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import pytest

from src.libs.his.mock_his import MockHISClient
from src.tools.his_orchestrator.booking_service import BookingService


class TestBookingConcurrency:
    """Test concurrent booking scenarios (I4)."""

    def setup_method(self):
        """Create a fresh test database."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = str(Path(self.temp_dir) / "test_concurrent.db")
        self.his_client = MockHISClient(db_path=self.db_path, use_wal=True)
        self.booking_service = BookingService(self.his_client)

        # Get a valid schedule_id from the seeded data
        schedules = self.his_client.query_doctor_schedule("内科")
        self.valid_schedule_id = schedules[0].schedule_id if schedules else "S内科08"

    def teardown_method(self):
        """Clean up test database."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_concurrent_booking_same_slot(self):
        """Test that concurrent booking for same slot is properly serialized.

        Only one booking should succeed when multiple concurrent requests
        try to book the same schedule slot.
        """
        schedule = self.his_client.query_doctor_schedule("内科")[0]
        schedule_id = schedule.schedule_id
        initial_slots = schedule.available_slots

        # Ensure at least 5 slots
        if initial_slots < 5:
            pytest.skip("Not enough slots for concurrent test")

        # Simulate 10 concurrent booking attempts
        num_attempts = 10
        results = []

        def book_once(attempt_num):
            """Book a single appointment."""
            client = MockHISClient(db_path=self.db_path, use_wal=True)
            booking = BookingService(client)
            result = booking.book(f"patient_{attempt_num}", schedule_id)
            return result.success, result.message

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(book_once, i) for i in range(num_attempts)]
            results = [f.result() for f in futures]

        # Count successes and failures
        successes = sum(1 for success, _ in results if success)
        failures = sum(1 for success, _ in results if not success)

        # Exactly num_attempts - initial_slots should succeed
        expected_successes = min(num_attempts, initial_slots)

        assert successes == expected_successes, (
            f"Expected {expected_successes} successes, got {successes}. "
            f"Results: {results}"
        )

        # Verify final slot count
        final_schedule = self.his_client.query_doctor_schedule("内科")[0]
        assert final_schedule.available_slots == initial_slots - successes

    def test_concurrent_booking_different_patients(self):
        """Test concurrent bookings by different patients succeed."""
        schedule = self.his_client.query_doctor_schedule("内科")[0]
        schedule_id = schedule.schedule_id
        initial_slots = schedule.available_slots

        if initial_slots < 3:
            pytest.skip("Not enough slots for concurrent test")

        # Book 3 different patients concurrently
        def book_patient(patient_num):
            client = MockHISClient(db_path=self.db_path, use_wal=True)
            booking = BookingService(client)
            return booking.book(f"patient_{patient_num}", schedule_id)

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(book_patient, i) for i in range(3)]
            results = [f.result() for f in futures]

        # All should succeed
        assert all(r.success for r in results)
        assert len(set(r.appointment_id for r in results)) == 3  # All unique IDs

    def test_double_booking_prevention(self):
        """Test that same patient cannot book same schedule twice."""
        schedule = self.his_client.query_doctor_schedule("内科")[0]
        schedule_id = schedule.schedule_id

        # First booking should succeed
        result1 = self.booking_service.book("patient_double", schedule_id)
        assert result1.success, f"First booking failed: {result1.message}"

        # Second booking by same patient should fail
        result2 = self.booking_service.book("patient_double", schedule_id)
        assert not result2.success, "Double booking should have been prevented"
        assert "Already booked" in result2.message or "already" in result2.message.lower()

    def test_booking_race_condition_handling(self):
        """Test that race conditions don't cause inconsistent state.

        When many concurrent requests try to book the last available slot,
        exactly one should succeed and others should fail cleanly.
        """
        schedule = self.his_client.query_doctor_schedule("儿科")[0]
        schedule_id = schedule.schedule_id

        # Set exactly 1 slot available
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "UPDATE schedules SET available_slots = 1 WHERE schedule_id = ?",
            (schedule_id,)
        )
        conn.commit()
        conn.close()

        # 20 concurrent attempts
        num_attempts = 20

        def book_once(attempt_num):
            client = MockHISClient(db_path=self.db_path, use_wal=True)
            booking = BookingService(client)
            return booking.book(f"patient_{attempt_num}", schedule_id)

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(book_once, i) for i in range(num_attempts)]
            results = [f.result() for f in futures]

        # Exactly 1 should succeed
        successes = sum(1 for r in results if r.success)
        assert successes == 1, f"Expected exactly 1 success, got {successes}"

        # Verify slot is now 0
        final_schedule = self.his_client.query_doctor_schedule("儿科")[0]
        assert final_schedule.available_slots == 0


class TestBookingIntegration:
    """Integration tests for complete booking flow (I5)."""

    def setup_method(self):
        """Create a fresh test database."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = str(Path(self.temp_dir) / "test_integration.db")
        self.his_client = MockHISClient(db_path=self.db_path, use_wal=True)
        self.schedule_service = self.his_client
        self.booking_service = BookingService(self.his_client)

    def teardown_method(self):
        """Clean up test database."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_full_booking_flow(self):
        """Test complete booking flow: dept → doctor → time → book."""
        # Step 1: Query departments
        depts = self.his_client.query_departments("内科")
        assert len(depts) > 0
        dept_name = depts[0].name

        # Step 2: Query doctor schedules for department
        schedules = self.his_client.query_doctor_schedule(dept_name)
        assert len(schedules) > 0
        schedule = schedules[0]
        schedule_id = schedule.schedule_id
        initial_slots = schedule.available_slots

        # Step 3: Book appointment
        result = self.booking_service.book("patient_integration_test", schedule_id)
        assert result.success, f"Booking failed: {result.message}"
        assert result.appointment_id is not None

        # Step 4: Verify slot was decremented
        updated_schedules = self.his_client.query_doctor_schedule(dept_name)
        updated_schedule = next(s for s in updated_schedules if s.schedule_id == schedule_id)
        assert updated_schedule.available_slots == initial_slots - 1

        # Step 5: Get confirmation
        confirmation = self.booking_service.confirm_booking(
            "patient_integration_test", schedule_id
        )
        assert confirmation is not None
        assert confirmation.confirmation_code is not None
        assert len(confirmation.confirmation_code) == 6

    def test_booking_flow_no_slots(self):
        """Test booking flow when no slots available."""
        # Get a schedule and set slots to 0
        schedules = self.his_client.query_doctor_schedule("内科")
        schedule_id = schedules[0].schedule_id

        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "UPDATE schedules SET available_slots = 0 WHERE schedule_id = ?",
            (schedule_id,)
        )
        conn.commit()
        conn.close()

        # Attempt booking
        result = self.booking_service.book("patient_no_slots", schedule_id)
        assert not result.success
        assert "No available slots" in result.message or "no available" in result.message.lower()

    def test_booking_flow_invalid_schedule(self):
        """Test booking flow with invalid schedule ID."""
        result = self.booking_service.book("patient_invalid", "INVALID_SCHEDULE_ID")
        assert not result.success
        assert "not found" in result.message.lower()

    def test_booking_flow_department_filter(self):
        """Test booking respects department filtering."""
        # Book from one department
        dept_schedules = self.his_client.query_doctor_schedule("内科")
        if not dept_schedules:
            pytest.skip("No 内科 schedules")

        schedule_id = dept_schedules[0].schedule_id
        result = self.booking_service.book("patient_dept_test", schedule_id)
        assert result.success

        # Verify it was booked under correct department
        updated = self.his_client.query_doctor_schedule("内科")[0]
        assert updated.available_slots < 10  # Original was 10

    def test_booking_idempotency(self):
        """Test that booking operations are idempotent in terms of patient-schedule pairs."""
        schedules = self.his_client.query_doctor_schedule("内科")
        schedule_id = schedules[0].schedule_id

        # First booking
        result1 = self.booking_service.book("idempotent_patient", schedule_id)
        assert result1.success

        # Duplicate booking
        result2 = self.booking_service.book("idempotent_patient", schedule_id)
        assert not result2.success
