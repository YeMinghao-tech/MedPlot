"""Department service for querying hospital departments."""

from dataclasses import dataclass
from typing import List, Optional

from src.libs.his.base_his import BaseHISClient, Department


@dataclass
class DepartmentInfo:
    """Enhanced department information with additional context."""

    dept_id: str
    name: str
    description: Optional[str] = None
    # Additional fields that might come from a more complete HIS
    location: Optional[str] = None
    phone: Optional[str] = None
    special_clinics: Optional[List[str]] = None


class DepartmentService:
    """Service for querying and filtering hospital departments.

    Provides a higher-level interface to the HIS department data,
    with support for keyword-based search and filtering.
    """

    def __init__(self, his_client: BaseHISClient):
        """Initialize the department service.

        Args:
            his_client: HIS client for data access.
        """
        self.his_client = his_client

    def query(self, keyword: str = "") -> List[Department]:
        """Query departments by keyword.

        Performs a case-insensitive keyword search across department
        names and descriptions.

        Args:
            keyword: Search keyword. Empty string returns all departments.

        Returns:
            List of matching departments.
        """
        departments = self.his_client.query_departments(keyword)

        if not keyword:
            return departments

        # Additional filtering if HIS client returns all departments
        # (Some implementations may do this for simplicity)
        keyword_lower = keyword.lower()
        filtered = [
            dept for dept in departments
            if (keyword_lower in dept.name.lower() or
                (dept.description and keyword_lower in dept.description.lower()))
        ]

        return filtered

    def get_by_id(self, dept_id: str) -> Optional[Department]:
        """Get a department by its ID.

        Args:
            dept_id: Department identifier.

        Returns:
            Department if found, None otherwise.
        """
        departments = self.his_client.query_departments("")
        for dept in departments:
            if dept.dept_id == dept_id:
                return dept
        return None

    def get_all(self) -> List[Department]:
        """Get all departments.

        Returns:
            List of all departments.
        """
        return self.his_client.query_departments("")
