"""Schedule service for querying doctor schedules and availability."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

from src.libs.his.base_his import BaseHISClient, Schedule


@dataclass
class ScheduleInfo:
    """Enhanced schedule information with computed fields."""

    schedule_id: str
    doctor_name: str
    dept_name: str
    date: str
    time_slot: str
    available_slots: int
    # Computed fields
    is_today: bool = False
    is_tomorrow: bool = False
    day_of_week: Optional[str] = None


class ScheduleService:
    """Service for querying doctor schedules.

    Provides a higher-level interface to schedule data with support for
    filtering by date, department, and doctor.
    """

    # Day of week names in Chinese
    DAY_OF_WEEK = {
        0: "周一",
        1: "周二",
        2: "周三",
        3: "周四",
        4: "周五",
        5: "周六",
        6: "周日",
    }

    def __init__(self, his_client: BaseHISClient):
        """Initialize the schedule service.

        Args:
            his_client: HIS client for data access.
        """
        self.his_client = his_client

    def query(
        self,
        dept_name: Optional[str] = None,
        date: Optional[str] = None,
        doctor_name: Optional[str] = None,
    ) -> List[Schedule]:
        """Query schedules with optional filters.

        Args:
            dept_name: Department name filter.
            date: Date filter in YYYY-MM-DD format.
            doctor_name: Doctor name filter (partial match).

        Returns:
            List of matching schedules.
        """
        # Get all schedules for the department
        schedules = self.his_client.query_doctor_schedule(dept_name or "")

        # Apply filters
        filtered = []
        for schedule in schedules:
            # Department filter (case-insensitive partial match)
            if dept_name:
                if dept_name.lower() not in schedule.dept_name.lower():
                    continue

            # Date filter
            if date and schedule.date != date:
                continue

            # Doctor name filter (case-insensitive partial match)
            if doctor_name:
                if doctor_name.lower() not in schedule.doctor_name.lower():
                    continue

            filtered.append(schedule)

        return filtered

    def get_available(
        self,
        dept_name: Optional[str] = None,
        date: Optional[str] = None,
    ) -> List[Schedule]:
        """Get only schedules with available slots.

        Args:
            dept_name: Department name filter.
            date: Date filter in YYYY-MM-DD format.

        Returns:
            List of schedules with available_slots > 0.
        """
        schedules = self.query(dept_name=dept_name, date=date)
        return [s for s in schedules if s.available_slots > 0]

    def get_by_schedule_id(self, schedule_id: str) -> Optional[Schedule]:
        """Get a schedule by its ID.

        Args:
            schedule_id: Schedule identifier.

        Returns:
            Schedule if found, None otherwise.
        """
        return self.his_client.get_schedule_by_id(schedule_id)

    def enrich_schedule(self, schedule: Schedule) -> ScheduleInfo:
        """Enrich a schedule with computed fields.

        Args:
            schedule: Base schedule.

        Returns:
            ScheduleInfo with computed fields.
        """
        today = datetime.now().strftime("%Y-%m-%d")
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

        try:
            date_obj = datetime.strptime(schedule.date, "%Y-%m-%d")
            day_of_week = self.DAY_OF_WEEK.get(date_obj.weekday())
        except (ValueError, TypeError):
            day_of_week = None

        return ScheduleInfo(
            schedule_id=schedule.schedule_id,
            doctor_name=schedule.doctor_name,
            dept_name=schedule.dept_name,
            date=schedule.date,
            time_slot=schedule.time_slot,
            available_slots=schedule.available_slots,
            is_today=schedule.date == today,
            is_tomorrow=schedule.date == tomorrow,
            day_of_week=day_of_week,
        )

    def get_upcoming(
        self,
        dept_name: Optional[str] = None,
        days: int = 7,
    ) -> List[ScheduleInfo]:
        """Get upcoming schedules for the next N days.

        Args:
            dept_name: Department name filter.
            days: Number of days to look ahead.

        Returns:
            List of upcoming schedules with computed fields.
        """
        today = datetime.now()
        upcoming_dates = [
            (today + timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(days)
        ]

        schedules = self.query(dept_name=dept_name)
        upcoming = [
            s for s in schedules
            if s.date in upcoming_dates and s.available_slots > 0
        ]

        return [self.enrich_schedule(s) for s in upcoming]
