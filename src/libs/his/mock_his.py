"""Mock HIS Client implementation using SQLite."""

import sqlite3
import threading
import uuid
from pathlib import Path
from typing import List, Optional

from src.libs.his.base_his import (
    AppointmentResult,
    BaseHISClient,
    Department,
    Schedule,
)


class MockHISClient(BaseHISClient):
    """Mock HIS Client using SQLite for testing and local development."""

    def __init__(self, db_path: str = "./data/db/his_mock.db", use_wal: bool = True):
        """Initialize Mock HIS Client.

        Args:
            db_path: Path to the SQLite database file.
            use_wal: Whether to use WAL mode for better concurrency.
        """
        self.db_path = db_path
        self.use_wal = use_wal
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        """Initialize the database schema and seed data."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            if self.use_wal:
                conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")

            # Create tables
            conn.execute("""
                CREATE TABLE IF NOT EXISTS departments (
                    dept_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schedules (
                    schedule_id TEXT PRIMARY KEY,
                    doctor_name TEXT NOT NULL,
                    dept_name TEXT NOT NULL,
                    date TEXT NOT NULL,
                    time_slot TEXT NOT NULL,
                    available_slots INTEGER DEFAULT 10
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS appointments (
                    appointment_id TEXT PRIMARY KEY,
                    patient_id TEXT NOT NULL,
                    schedule_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(patient_id, schedule_id)
                )
            """)

            # Seed departments if empty
            cursor = conn.execute("SELECT COUNT(*) FROM departments")
            if cursor.fetchone()[0] == 0:
                self._seed_data(conn)

            conn.commit()
            conn.close()

    def _seed_data(self, conn):
        """Seed initial test data."""
        # Departments
        departments = [
            ("D001", "内科", "内科门诊"),
            ("D002", "外科", "外科门诊"),
            ("D003", "儿科", "儿科门诊"),
            ("D004", "妇产科", "妇产科门诊"),
            ("D005", "骨科", "骨科门诊"),
            ("D006", "皮肤科", "皮肤科门诊"),
            ("D007", "眼科", "眼科门诊"),
            ("D008", "耳鼻喉科", "耳鼻喉科门诊"),
        ]
        conn.executemany(
            "INSERT INTO departments (dept_id, name, description) VALUES (?, ?, ?)",
            departments,
        )

        # Schedules
        import datetime

        today = datetime.date.today()
        schedules = []
        for i, (dept_id, dept_name, _) in enumerate(departments):
            for day_offset in range(7):
                date = (today + datetime.timedelta(days=day_offset)).isoformat()
                for slot in ["上午 08:00-12:00", "下午 14:00-18:00"]:
                    schedule_id = f"S{dept_id}{day_offset}{slot[:2]}"
                    schedules.append(
                        (schedule_id, f"医生{i+1}", dept_name, date, slot, 10)
                    )
        conn.executemany(
            "INSERT INTO schedules (schedule_id, doctor_name, dept_name, date, time_slot, available_slots) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            schedules,
        )

    def query_departments(self, keyword: str = "") -> List[Department]:
        """Query departments by keyword."""
        with self._lock:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            if keyword:
                cursor = conn.execute(
                    "SELECT dept_id, name, description FROM departments WHERE name LIKE ?",
                    (f"%{keyword}%",),
                )
            else:
                cursor = conn.execute(
                    "SELECT dept_id, name, description FROM departments"
                )
            rows = cursor.fetchall()
            conn.close()
            return [
                Department(dept_id=row[0], name=row[1], description=row[2])
                for row in rows
            ]

    def query_doctor_schedule(
        self, dept_name: str = "", date: Optional[str] = None
    ) -> List[Schedule]:
        """Query doctor schedules for a department.

        Args:
            dept_name: Department name filter (empty string returns all).
            date: Optional date filter.
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            if dept_name and date:
                cursor = conn.execute(
                    """SELECT schedule_id, doctor_name, dept_name, date, time_slot, available_slots
                       FROM schedules WHERE dept_name = ? AND date = ?""",
                    (dept_name, date),
                )
            elif dept_name:
                cursor = conn.execute(
                    """SELECT schedule_id, doctor_name, dept_name, date, time_slot, available_slots
                       FROM schedules WHERE dept_name = ?""",
                    (dept_name,),
                )
            elif date:
                cursor = conn.execute(
                    """SELECT schedule_id, doctor_name, dept_name, date, time_slot, available_slots
                       FROM schedules WHERE date = ?""",
                    (date,),
                )
            else:
                cursor = conn.execute(
                    """SELECT schedule_id, doctor_name, dept_name, date, time_slot, available_slots
                       FROM schedules"""
                )
            rows = cursor.fetchall()
            conn.close()
            return [
                Schedule(
                    schedule_id=row[0],
                    doctor_name=row[1],
                    dept_name=row[2],
                    date=row[3],
                    time_slot=row[4],
                    available_slots=row[5],
                )
                for row in rows
            ]

    def get_schedule_by_id(self, schedule_id: str) -> Optional[Schedule]:
        """Get a schedule by its ID.

        Args:
            schedule_id: Schedule identifier.

        Returns:
            Schedule if found, None otherwise.
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            cursor = conn.execute(
                """SELECT schedule_id, doctor_name, dept_name, date, time_slot, available_slots
                   FROM schedules WHERE schedule_id = ?""",
                (schedule_id,),
            )
            row = cursor.fetchone()
            conn.close()
            if row:
                return Schedule(
                    schedule_id=row[0],
                    doctor_name=row[1],
                    dept_name=row[2],
                    date=row[3],
                    time_slot=row[4],
                    available_slots=row[5],
                )
            return None

    def book_appointment(
        self, patient_id: str, schedule_id: str
    ) -> AppointmentResult:
        """Book an appointment with atomic transaction support.

        Uses BEGIN IMMEDIATE to acquire a write lock at the start of the
        transaction, preventing race conditions in concurrent booking.
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path, check_same_thread=False, isolation_level=None)
            if self.use_wal:
                conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=10000")

            try:
                # BEGIN IMMEDIATE acquires write lock immediately
                conn.execute("BEGIN IMMEDIATE")

                # Check if schedule exists and has availability
                cursor = conn.execute(
                    "SELECT available_slots FROM schedules WHERE schedule_id = ?",
                    (schedule_id,),
                )
                row = cursor.fetchone()
                if not row:
                    conn.execute("ROLLBACK")
                    conn.close()
                    return AppointmentResult(success=False, message="Schedule not found")
                if row[0] <= 0:
                    conn.execute("ROLLBACK")
                    conn.close()
                    return AppointmentResult(success=False, message="No available slots")

                # Book the appointment
                appointment_id = str(uuid.uuid4())
                conn.execute(
                    "INSERT INTO appointments (appointment_id, patient_id, schedule_id) VALUES (?, ?, ?)",
                    (appointment_id, patient_id, schedule_id),
                )

                # Decrement available slots
                conn.execute(
                    "UPDATE schedules SET available_slots = available_slots - 1 WHERE schedule_id = ?",
                    (schedule_id,),
                )

                conn.execute("COMMIT")
                conn.close()
                return AppointmentResult(
                    success=True,
                    appointment_id=appointment_id,
                    message="Appointment booked successfully",
                )
            except sqlite3.IntegrityError:
                conn.execute("ROLLBACK")
                conn.close()
                return AppointmentResult(success=False, message="Already booked")
            except sqlite3.OperationalError as e:
                conn.execute("ROLLBACK")
                conn.close()
                return AppointmentResult(success=False, message=f"Booking failed: {str(e)}")
            except Exception as e:
                conn.execute("ROLLBACK")
                conn.close()
                return AppointmentResult(success=False, message=str(e))
