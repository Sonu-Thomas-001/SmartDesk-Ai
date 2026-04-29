import json
import warnings
import structlog

warnings.filterwarnings("ignore", message=".*ChatVertexAI.*deprecated.*")

from langchain_google_vertexai import ChatVertexAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from app.config import settings
from app.embedding_engine import EmbeddingEngine
from app.models import SimilarIncident

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

RESOLVER_SYSTEM_PROMPT = """\
You are an IT Incident Resolution AI assistant.

Your job is to generate a **clear, actionable resolution guide** that will help \
the assigned engineer resolve the incident as quickly as possible.

You will be given:
1. The incident details (description, category, severity, assigned team)
2. Relevant Knowledge Base (KB) articles retrieved from the vector database

Using that context, produce a resolution guide in **strict JSON** with these keys:
{{
  "resolution_title": "<short title for the resolution guide>",
  "estimated_resolution_time": "<e.g. 15 minutes, 1 hour, etc.>",
  "steps": [
    {{
      "step_number": <int>,
      "action": "<what to do>",
      "details": "<specific instructions, commands, or paths>"
    }}
  ],
  "warnings": ["<any cautions or things to watch out for>"],
  "escalation_note": "<when/how to escalate if steps don't resolve the issue>",
  "kb_articles_used": ["<list of KB article IDs referenced>"]
}}

Guidelines:
- Steps MUST be specific and actionable — include exact commands, paths, or UI navigation where relevant.
- Tailor the steps to the specific incident, don't just copy KB articles verbatim.
- Order steps from simplest/quickest to more complex.
- Include 4-10 steps depending on complexity.
- The escalation_note should mention the next team or person to contact.

Do NOT include any text outside the JSON object.
"""

RESOLVER_HUMAN_PROMPT = """\
=== INCIDENT ===
Number: {incident_number}
Short Description: {short_description}
Description: {description}
Category: {category}
Severity: {severity}
Assigned Team: {assigned_team}
Assigned To: {assigned_to}

=== RELEVANT KB ARTICLES ===
{kb_articles}

Generate a resolution guide for the assigned engineer.
"""


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class IncidentResolverAgent:
    """LLM agent that generates step-by-step resolution guides using KB articles."""

    def __init__(self, embedding_engine: EmbeddingEngine) -> None:
        self._llm = ChatVertexAI(
            model_name=settings.gemini_model,
            project=settings.google_cloud_project,
            location=settings.google_cloud_location,
            temperature=0.2,
        )
        self._prompt = ChatPromptTemplate.from_messages(
            [
                ("system", RESOLVER_SYSTEM_PROMPT),
                ("human", RESOLVER_HUMAN_PROMPT),
            ]
        )
        self._parser = JsonOutputParser()
        self._chain = self._prompt | self._llm | self._parser
        self._embedding_engine = embedding_engine

    def resolve(
        self,
        incident_number: str,
        short_description: str,
        description: str,
        category: str,
        severity: str,
        assigned_team: str,
        assigned_to: str,
    ) -> dict:
        """Search KB articles and generate a resolution guide."""
        # 1. Find relevant KB articles from ChromaDB
        query = f"{short_description} {description}"
        similar: list[SimilarIncident] = self._embedding_engine.search_similar(
            query, top_k=5
        )

        # 2. Build KB context for the prompt
        if similar:
            kb_parts: list[str] = []
            for si in similar:
                kb_parts.append(
                    f"--- KB Article: {si.id} (similarity: {si.similarity_score:.0%}) ---\n"
                    f"Description: {si.description}\n"
                    f"Team: {si.assigned_team}\n"
                    f"Resolution Steps:\n{si.resolution_notes}\n"
                )
            kb_text = "\n".join(kb_parts)
        else:
            kb_text = "No relevant KB articles found. Generate best-practice resolution steps."

        # 3. Run the LLM chain
        raw = self._chain.invoke(
            {
                "incident_number": incident_number,
                "short_description": short_description,
                "description": description,
                "category": category,
                "severity": severity,
                "assigned_team": assigned_team,
                "assigned_to": assigned_to or "Unassigned",
                "kb_articles": kb_text,
            }
        )

        logger.info(
            "resolution_generated",
            incident=incident_number,
            steps=len(raw.get("steps", [])),
            kb_used=raw.get("kb_articles_used", []),
        )
        return raw

    def format_as_worknote(self, resolution: dict) -> str:
        """Format the resolution guide into a ServiceNow work note string."""
        lines = [
            f"=== AI Resolution Guide: {resolution.get('resolution_title', 'N/A')} ===",
            f"Estimated Time: {resolution.get('estimated_resolution_time', 'N/A')}",
            "",
            "--- Steps ---",
        ]
        for step in resolution.get("steps", []):
            lines.append(
                f"Step {step['step_number']}: {step['action']}\n"
                f"   Details: {step['details']}"
            )

        warnings = resolution.get("warnings", [])
        if warnings:
            lines.append("")
            lines.append("--- Warnings ---")
            for w in warnings:
                lines.append(f"⚠ {w}")

        esc_note = resolution.get("escalation_note", "")
        if esc_note:
            lines.append("")
            lines.append(f"--- Escalation ---\n{esc_note}")

        kb_used = resolution.get("kb_articles_used", [])
        if kb_used:
            lines.append("")
            lines.append(f"KB Articles Referenced: {', '.join(kb_used)}")

        return "\n".join(lines)
