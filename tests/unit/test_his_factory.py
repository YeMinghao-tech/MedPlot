"""Tests for HIS Factory."""

import tempfile

import pytest

from src.core.settings import Settings
from src.libs.his.base_his import (
    AppointmentResult,
    BaseHISClient,
)
from src.libs.his.his_factory import HISFactory
from src.libs.his.mock_his import MockHISClient


class TestHISFactory:
    """Test HISFactory.create method."""

    def test_create_mock_his_client(self):
        """Test creating a Mock HIS client."""
        settings = Settings()
        settings.his.backend = "mock"
        settings.his.mock_db_path = "./data/test_his.db"
        settings.his.use_wal = True

        client = HISFactory.create(settings)
        assert isinstance(client, MockHISClient)
        assert isinstance(client, BaseHISClient)

    def test_create_unsupported_backend_raises_error(self):
        """Test that unsupported backend raises ValueError."""
        settings = Settings()
        settings.his.backend = "unsupported"
        settings.his.mock_db_path = "./data/test.db"

        with pytest.raises(ValueError) as exc_info:
            HISFactory.create(settings)
        assert "Unsupported HIS backend" in str(exc_info.value)


class TestMockHISClient:
    """Test MockHISClient functionality."""

    def test_query_departments_all(self):
        """Test querying all departments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = f"{tmpdir}/test_his.db"
            client = MockHISClient(db_path=db_path, use_wal=True)

            depts = client.query_departments()
            assert len(depts) > 0
            assert all(hasattr(d, "dept_id") for d in depts)
            assert all(hasattr(d, "name") for d in depts)

    def test_query_departments_by_keyword(self):
        """Test querying departments by keyword."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = f"{tmpdir}/test_his.db"
            client = MockHISClient(db_path=db_path, use_wal=True)

            depts = client.query_departments("内科")
            assert len(depts) > 0
            assert all("内科" in d.name for d in depts)

    def test_query_doctor_schedule(self):
        """Test querying doctor schedules."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = f"{tmpdir}/test_his.db"
            client = MockHISClient(db_path=db_path, use_wal=True)

            schedules = client.query_doctor_schedule("内科")
            assert len(schedules) > 0
            assert all(s.dept_name == "内科" for s in schedules)

    def test_book_appointment_success(self):
        """Test successful appointment booking."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = f"{tmpdir}/test_his.db"
            client = MockHISClient(db_path=db_path, use_wal=True)

            # Get a schedule
            schedules = client.query_doctor_schedule("内科")
            assert len(schedules) > 0
            schedule_id = schedules[0].schedule_id

            # Book
            result = client.book_appointment("patient1", schedule_id)
            assert result.success is True
            assert result.appointment_id is not None

    def test_book_appointment_no_slots(self):
        """Test booking when no slots available."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = f"{tmpdir}/test_his.db"
            client = MockHISClient(db_path=db_path, use_wal=True)

            # Get a schedule and book it multiple times until no slots
            schedules = client.query_doctor_schedule("内科")
            schedule_id = schedules[0].schedule_id

            # Book all slots
            for _ in range(15):  # Default is 10 slots
                result = client.book_appointment(f"patient_{_}", schedule_id)
                if not result.success:
                    break

            # Try to book again when full
            result = client.book_appointment("patient_last", schedule_id)
            assert result.success is False
            assert "No available slots" in result.message


class TestBaseHISClientInterface:
    """Test that HIS implementations conform to BaseHISClient interface."""

    def test_mock_his_client_conforms_to_interface(self):
        """Test MockHISClient conforms to BaseHISClient."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = f"{tmpdir}/test_his.db"
            client = MockHISClient(db_path=db_path, use_wal=True)

            assert isinstance(client, BaseHISClient)
            assert hasattr(client, "query_departments")
            assert hasattr(client, "query_doctor_schedule")
            assert hasattr(client, "book_appointment")
