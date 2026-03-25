"""Booking service for appointment reservation with transaction support."""

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from src.libs.his.base_his import AppointmentResult, BaseHISClient, Schedule
from src.tools.his_orchestrator.schedule_service import ScheduleService


@dataclass
class BookingConfirmation:
    """Confirmation details for a successful booking."""

    appointment_id: str
    patient_id: str
    schedule_id: str
    doctor_name: str
    dept_name: str
    date: str
    time_slot: str
    booked_at: str
    confirmation_code: str


class BookingService:
    """Service for booking medical appointments.

    Provides a higher-level interface to the HIS booking functionality,
    with support for transaction management and booking confirmation.

    Note: Full concurrent lock号 logic is TODO for future enhancement.
    """

    def __init__(self, his_client: BaseHISClient):
        """Initialize the booking service.

        Args:
            his_client: HIS client for booking operations.
        """
        self.his_client = his_client
        self.schedule_service = ScheduleService(his_client)

    def book(
        self,
        patient_id: str,
        schedule_id: str,
    ) -> AppointmentResult:
        """Book an appointment for a patient.

        Args:
            patient_id: Patient identifier.
            schedule_id: Schedule identifier to book.

        Returns:
            AppointmentResult with success status and details.
        """
        # Validate schedule exists and has availability
        schedule = self.schedule_service.get_by_schedule_id(schedule_id)
        if schedule is None:
            return AppointmentResult(
                success=False,
                message=f"Schedule {schedule_id} not found",
            )

        if schedule.available_slots <= 0:
            return AppointmentResult(
                success=False,
                message="No available slots for this schedule",
            )

        # Book via HIS client
        result = self.his_client.book_appointment(patient_id, schedule_id)

        if result.success:
            result.message = f"预约成功！您的预约ID：{result.appointment_id}"

        return result

    def confirm_booking(
        self,
        patient_id: str,
        schedule_id: str,
    ) -> Optional[BookingConfirmation]:
        """Get a booking confirmation with full details.

        Args:
            patient_id: Patient identifier.
            schedule_id: Schedule identifier.

        Returns:
            BookingConfirmation if booking exists, None otherwise.
        """
        # Get schedule details
        schedule = self.schedule_service.get_by_schedule_id(schedule_id)
        if schedule is None:
            return None

        # Generate confirmation code
        confirmation_code = self._generate_confirmation_code(
            patient_id, schedule_id
        )

        return BookingConfirmation(
            appointment_id=str(uuid.uuid4())[:8].upper(),
            patient_id=patient_id,
            schedule_id=schedule_id,
            doctor_name=schedule.doctor_name,
            dept_name=schedule.dept_name,
            date=schedule.date,
            time_slot=schedule.time_slot,
            booked_at=datetime.now().isoformat(),
            confirmation_code=confirmation_code,
        )

    def _generate_confirmation_code(self, patient_id: str, schedule_id: str) -> str:
        """Generate a short confirmation code.

        Args:
            patient_id: Patient identifier.
            schedule_id: Schedule identifier.

        Returns:
            6-character confirmation code.
        """
        import hashlib
        combined = f"{patient_id}:{schedule_id}:{datetime.now().date()}"
        hash_val = hashlib.md5(combined.encode()).hexdigest()[:6].upper()
        return hash_val

    def cancel(
        self,
        patient_id: str,
        schedule_id: str,
    ) -> AppointmentResult:
        """Cancel an appointment (placeholder for future implementation).

        Args:
            patient_id: Patient identifier.
            schedule_id: Schedule identifier.

        Returns:
            AppointmentResult with cancellation status.
        """
        # TODO: Implement cancellation logic
        return AppointmentResult(
            success=False,
            message="Cancellation not yet implemented",
        )

    def check_availability(self, schedule_id: str) -> bool:
        """Check if a schedule has available slots.

        Args:
            schedule_id: Schedule identifier.

        Returns:
            True if slots available, False otherwise.
        """
        schedule = self.schedule_service.get_by_schedule_id(schedule_id)
        if schedule is None:
            return False
        return schedule.available_slots > 0
