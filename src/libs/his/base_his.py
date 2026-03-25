"""Base HIS Client interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class Department:
    """Department information."""

    dept_id: str
    name: str
    description: Optional[str] = None


@dataclass
class Schedule:
    """Doctor schedule information."""

    schedule_id: str
    doctor_name: str
    dept_name: str
    date: str
    time_slot: str
    available_slots: int


@dataclass
class AppointmentResult:
    """Appointment booking result."""

    success: bool
    appointment_id: Optional[str] = None
    message: Optional[str] = None


class BaseHISClient(ABC):
    """Abstract base class for HIS (Hospital Information System) clients."""

    @abstractmethod
    def query_departments(self, keyword: str = "") -> List[Department]:
        """Query departments by keyword.

        Args:
            keyword: Search keyword (empty returns all).

        Returns:
            List of departments.
        """
        pass

    @abstractmethod
    def query_doctor_schedule(
        self, dept_name: str, date: Optional[str] = None
    ) -> List[Schedule]:
        """Query doctor schedules for a department.

        Args:
            dept_name: Department name.
            date: Optional date filter (YYYY-MM-DD).

        Returns:
            List of schedules.
        """
        pass

    @abstractmethod
    def book_appointment(
        self, patient_id: str, schedule_id: str
    ) -> AppointmentResult:
        """Book an appointment.

        Args:
            patient_id: Patient identifier.
            schedule_id: Schedule identifier.

        Returns:
            Appointment booking result.
        """
        pass
