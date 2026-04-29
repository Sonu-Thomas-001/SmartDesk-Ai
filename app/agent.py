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
4. Identify the correct assignment group
5. Provide a confidence score between 0.0 and 1.0

Base your decision on:
- Keywords in the description
- Context clues (department, caller, category)
- Similar historical incidents provided below (if any)

Always return output in **strict JSON** with these exact keys:
{{
  "category": "<string>",
  "subcategory": "<string>",
  "severity": "<Low|Medium|High|Critical>",
  "assigned_team": "<string>",
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

    def generate_incident(self) -> dict:
        """Use LLM to auto-generate a unique realistic dummy IT incident."""
        gen_prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "You are an IT incident generator for testing purposes. "
                "Generate a realistic, unique IT support incident that would be filed in ServiceNow. "
                "Each call must produce a DIFFERENT scenario — vary the department, issue type, and context. "
                "Pick from diverse categories: network, hardware, software, security, access, email, printing, database, cloud, etc. "
                "Return strict JSON with these keys:\n"
                '{{\n'
                '  "short_description": "<concise title, max 160 chars>",\n'
                '  "description": "<detailed 2-3 sentence description with specifics>",\n'
                '  "category": "<IT category>",\n'
                '  "urgency": "<1|2|3>",\n'
                '  "impact": "<1|2|3>"\n'
                '}}\n'
                "Urgency/Impact: 1=High, 2=Medium, 3=Low.\n"
                "Do NOT include any text outside the JSON object."
            )),
            ("human", "Generate a unique IT incident now."),
        ])
        chain = gen_prompt | self._llm | self._parser
        result = chain.invoke({})
        logger.info("incident_generated", short_desc=result.get("short_description"))
        return result
