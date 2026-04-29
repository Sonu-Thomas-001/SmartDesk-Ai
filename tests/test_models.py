"""Unit tests for models."""

import pytest
from pydantic import ValidationError

from app.models import ClassificationResult, Incident, Severity


class TestIncident:
    def test_minimal_incident(self):
        inc = Incident(sys_id="abc", number="INC001", short_description="Test")
        assert inc.sys_id == "abc"
        assert inc.description == ""

    def test_full_incident(self):
        inc = Incident(
            sys_id="abc",
            number="INC001",
            short_description="Test",
            description="Full description",
            category="Network",
            caller_id="user1",
            department="IT",
            state="1",
            priority="2",
        )
        assert inc.category == "Network"


class TestClassificationResult:
    def test_valid_classification(self):
        c = ClassificationResult(
            category="Network",
            subcategory="VPN",
            severity=Severity.HIGH,
            assigned_team="Network Team",
            confidence_score=0.85,
            summary="VPN issue",
        )
        assert c.severity == Severity.HIGH

    def test_confidence_bounds(self):
        with pytest.raises(ValidationError):
            ClassificationResult(
                category="Network",
                subcategory="VPN",
                severity=Severity.HIGH,
                assigned_team="Network Team",
                confidence_score=1.5,
                summary="VPN issue",
            )

    def test_confidence_lower_bound(self):
        with pytest.raises(ValidationError):
            ClassificationResult(
                category="Network",
                subcategory="VPN",
                severity=Severity.HIGH,
                assigned_team="Network Team",
                confidence_score=-0.1,
                summary="VPN issue",
            )
