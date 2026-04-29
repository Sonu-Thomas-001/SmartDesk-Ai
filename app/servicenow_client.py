import structlog
from typing import Any

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.models import Incident

logger = structlog.get_logger(__name__)


class ServiceNowClient:
    """Client for interacting with the ServiceNow REST API."""

    def __init__(self) -> None:
        self._base_url = settings.servicenow_instance_url.rstrip("/")
        self._auth = (settings.servicenow_username, settings.servicenow_password)
        self._headers = {"Content-Type": "application/json", "Accept": "application/json"}
        self._session = requests.Session()
        self._session.auth = self._auth
        self._session.headers.update(self._headers)

    # ------------------------------------------------------------------
    # Fetch incidents
    # ------------------------------------------------------------------

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def get_new_incidents(self, last_check: str | None = None) -> list[Incident]:
        """Fetch incidents with state=New. Optionally filter by creation time."""
        params: dict[str, Any] = {
            "sysparm_query": "state=1",  # 1 = New
            "sysparm_fields": (
                "sys_id,number,short_description,description,"
                "category,caller_id,department,state,priority,sys_created_on"
            ),
            "sysparm_limit": 50,
        }
        if last_check:
            params["sysparm_query"] += f"^sys_created_on>{last_check}"

        resp = self._session.get(
            f"{self._base_url}/api/now/table/incident", params=params, timeout=30
        )
        resp.raise_for_status()
        data = resp.json().get("result", [])
        logger.info("fetched_new_incidents", count=len(data))
        return [Incident(**item) for item in data]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def get_incident(self, sys_id: str) -> Incident:
        """Fetch a single incident by sys_id."""
        resp = self._session.get(
            f"{self._base_url}/api/now/table/incident/{sys_id}", timeout=30
        )
        resp.raise_for_status()
        return Incident(**resp.json()["result"])

    # ------------------------------------------------------------------
    # Update incident (assignment)
    # ------------------------------------------------------------------

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def update_incident(self, sys_id: str, payload: dict[str, Any]) -> dict:
        """PATCH an incident with the supplied fields."""
        resp = self._session.patch(
            f"{self._base_url}/api/now/table/incident/{sys_id}",
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        logger.info("updated_incident", sys_id=sys_id, fields=list(payload.keys()))
        return resp.json().get("result", {})

    def assign_incident(
        self,
        sys_id: str,
        assignment_group: str,
        assigned_to: str | None = None,
        priority: str | None = None,
    ) -> dict:
        """Assign an incident to a group / individual and set priority."""
        payload: dict[str, Any] = {"assignment_group": assignment_group}
        if assigned_to:
            payload["assigned_to"] = assigned_to
        if priority:
            payload["priority"] = priority
        return self.update_incident(sys_id, payload)

    # ------------------------------------------------------------------
    # Work notes
    # ------------------------------------------------------------------

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def add_worklog(self, sys_id: str, note: str) -> dict:
        """Append a work note to the incident."""
        payload = {"work_notes": note}
        return self.update_incident(sys_id, payload)

    # ------------------------------------------------------------------
    # Create incident
    # ------------------------------------------------------------------

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def create_incident(self, payload: dict[str, Any]) -> dict:
        """Create a new incident in ServiceNow."""
        resp = self._session.post(
            f"{self._base_url}/api/now/table/incident",
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json().get("result", {})
        logger.info("created_incident", sys_id=result.get("sys_id"), number=result.get("number"))
        return result

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        self._session.close()
