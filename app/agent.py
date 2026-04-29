import json
import warnings
import structlog

warnings.filterwarnings("ignore", message=".*ChatVertexAI.*deprecated.*")

from langchain_google_vertexai import ChatVertexAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from app.config import settings
from app.models import ClassificationResult, Incident, SimilarIncident

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are an IT Service Management AI assistant.

Your job is to:
1. Understand the incident description
2. Classify the issue into category and subcategory
3. Determine severity level (Low, Medium, High, Critical)
4. Identify the correct assignment group from the AVAILABLE TEAMS below
5. Provide a confidence score between 0.0 and 1.0

=== AVAILABLE ASSIGNMENT TEAMS ===
- Network Team          (network, VPN, firewall, DNS, connectivity issues)
- Application Support   (software bugs, app crashes, email, ERP, CRM)
- IAM Team              (access requests, password resets, permissions, SSO)
- Security Team         (security incidents, malware, data breaches, suspicious activity)
- Hardware Support      (laptops, monitors, printers, peripherals, hardware failures)
- Database Team         (database errors, performance, backups, SQL, data issues)
- Cloud Infrastructure  (cloud VMs, storage, AWS/Azure/GCP, Kubernetes, DevOps)
- Service Desk          (general queries, fallback for unclear issues)

You MUST pick "assigned_team" from the exact team names listed above.

Base your decision on:
- Keywords in the description
- Context clues (department, caller, category)
- Similar historical incidents provided below (if any)

Always return output in **strict JSON** with these exact keys:
{{
  "category": "<string>",
  "subcategory": "<string>",
  "severity": "<Low|Medium|High|Critical>",
  "assigned_team": "<one of the team names above>",
  "confidence_score": <float 0-1>,
  "summary": "<one-line summary>"
}}

Do NOT include any text outside the JSON object.
"""

HUMAN_PROMPT = """\
=== INCIDENT ===
Number: {number}
Short Description: {short_description}
Description: {description}
Category (if any): {category}
Caller / Department: {caller} / {department}

=== SIMILAR HISTORICAL INCIDENTS ===
{similar_incidents}

Classify this incident and return the JSON.
"""

FEW_SHOT_EXAMPLES = [
    {
        "input": "User cannot access VPN from home",
        "output": {
            "category": "Network Issue",
            "subcategory": "VPN",
            "severity": "High",
            "assigned_team": "Network Team",
            "confidence_score": 0.9,
            "summary": "User unable to connect to VPN, impacting remote work",
        },
    },
    {
        "input": "Need access to SharePoint site for finance team",
        "output": {
            "category": "Access Management",
            "subcategory": "SharePoint Access",
            "severity": "Medium",
            "assigned_team": "IAM Team",
            "confidence_score": 0.88,
            "summary": "Access request for SharePoint site for finance department",
        },
    },
    {
        "input": "Email server is down, no one can send or receive emails",
        "output": {
            "category": "Application Issue",
            "subcategory": "Email Service",
            "severity": "Critical",
            "assigned_team": "Application Support",
            "confidence_score": 0.95,
            "summary": "Email service outage affecting all users",
        },
    },
    {
        "input": "Suspicious login attempts detected on admin account",
        "output": {
            "category": "Security Incident",
            "subcategory": "Unauthorized Access",
            "severity": "Critical",
            "assigned_team": "Security Team",
            "confidence_score": 0.92,
            "summary": "Potential unauthorized access detected on admin account",
        },
    },
]


def _build_few_shot_block() -> str:
    lines: list[str] = []
    for ex in FEW_SHOT_EXAMPLES:
        lines.append(f'Input: "{ex["input"]}"')
        # Escape braces so LangChain doesn't treat them as template variables
        output_json = json.dumps(ex['output'], indent=2).replace("{", "{{").replace("}", "}}")
        lines.append(f"Output: {output_json}")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class ClassificationAgent:
    """LangChain-based agent that classifies ServiceNow incidents."""

    def __init__(self) -> None:
        self._llm = ChatVertexAI(
            model_name=settings.gemini_model,
            project=settings.google_cloud_project,
            location=settings.google_cloud_location,
            temperature=0.1,
        )
        few_shot = _build_few_shot_block()
        system_with_examples = SYSTEM_PROMPT + "\n\n=== FEW-SHOT EXAMPLES ===\n" + few_shot

        self._prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_with_examples),
                ("human", HUMAN_PROMPT),
            ]
        )
        self._parser = JsonOutputParser(pydantic_object=ClassificationResult)
        self._chain = self._prompt | self._llm | self._parser
        self._generated_titles: list[str] = []

    def classify(
        self,
        incident: Incident,
        similar_incidents: list[SimilarIncident] | None = None,
    ) -> ClassificationResult:
        """Run the classification chain and return structured result."""
        similar_text = "None found."
        if similar_incidents:
            parts: list[str] = []
            for si in similar_incidents:
                parts.append(
                    f"- [{si.similarity_score:.0%}] Team: {si.assigned_team} | "
                    f"Desc: {si.description[:200]} | Resolution: {si.resolution_notes[:200]}"
                )
            similar_text = "\n".join(parts)

        raw = self._chain.invoke(
            {
                "number": incident.number,
                "short_description": incident.short_description,
                "description": incident.description,
                "category": incident.category or "N/A",
                "caller": incident.caller_id or "N/A",
                "department": incident.department or "N/A",
                "similar_incidents": similar_text,
            }
        )

        result = ClassificationResult(**raw)
        logger.info(
            "classified",
            incident=incident.number,
            team=result.assigned_team,
            confidence=result.confidence_score,
        )
        return result

    def generate_incidents(self, count: int = 5) -> list[dict]:
        """Use LLM to auto-generate *count* unique realistic dummy IT incidents in one call."""
        avoid_block = ""
        if self._generated_titles:
            recent = self._generated_titles[-50:]
            avoid_block = (
                "IMPORTANT — the following incidents have ALREADY been generated. "
                "Do NOT repeat or closely rephrase any of them:\n"
                + "\n".join(f"- {t}" for t in recent)
                + "\n\n"
            )

        gen_prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "You are an IT incident generator for testing purposes. "
                f"Generate exactly {count} realistic, unique IT support incidents that would be filed in ServiceNow. "
                "Each incident must be a DIFFERENT scenario — vary the department, issue type, caller, and context. "
                "\n\n"
                "CRITICAL: Each incident MUST clearly map to a DIFFERENT assignment team from this list. "
                "Spread incidents evenly across these teams:\n"
                "- Network Team          → generate incidents about VPN failures, DNS issues, firewall blocks, Wi-Fi drops, network outages, slow connectivity\n"
                "- Application Support   → generate incidents about app crashes, email issues, ERP errors, software bugs, slow application performance\n"
                "- IAM Team              → generate incidents about password resets, account lockouts, MFA problems, access requests, SSO failures, permission issues\n"
                "- Security Team         → generate incidents about phishing emails, malware alerts, suspicious logins, data breach concerns, SSL certificate issues\n"
                "- Hardware Support      → generate incidents about broken laptops, monitor failures, keyboard/mouse issues, printer jams, docking station problems\n"
                "- Database Team         → generate incidents about database connection errors, slow queries, backup failures, replication lag, data corruption\n"
                "- Cloud Infrastructure  → generate incidents about VM outages, Kubernetes pod crashes, cloud storage errors, deployment failures, auto-scaling issues\n"
                "- Service Desk          → generate incidents about new employee onboarding, software install requests, general IT questions, equipment requests\n"
                "\n"
                f"Pick {count} DIFFERENT teams from the list above and generate one incident per team. "
                "Make sure the description contains strong keywords that clearly indicate the target team. "
                f"{avoid_block}"
                "Return a strict JSON **array** of " + str(count) + " objects. Each object has these keys:\n"
                '{{\n'
                '  "short_description": "<concise title, max 160 chars>",\n'
                '  "description": "<detailed 2-3 sentence description with specifics>",\n'
                '  "category": "<IT category>",\n'
                '  "urgency": "<1|2|3>",\n'
                '  "impact": "<1|2|3>"\n'
                '}}\n'
                "Urgency/Impact: 1=High, 2=Medium, 3=Low.\n"
                "Do NOT include any text outside the JSON array."
            )),
            ("human", f"Generate {count} unique IT incidents now, each targeting a different team."),
        ])
        chain = gen_prompt | self._llm | self._parser
        results = chain.invoke({})

        # Normalise: parser may return a list or a dict with a key
        if isinstance(results, dict):
            results = list(results.values())[0] if results else []
        if not isinstance(results, list):
            results = [results]

        for r in results:
            title = r.get("short_description", "")
            if title:
                self._generated_titles.append(title)

        logger.info("incidents_generated", count=len(results))
        return results
