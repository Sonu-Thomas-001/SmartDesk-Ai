"""Ingest KB articles and sample incidents from data/ into ChromaDB."""

import json
import sys
from pathlib import Path

# Ensure project root is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.embedding_engine import EmbeddingEngine


DATA_DIR = Path(__file__).resolve().parent / "data"


def load_json(filename: str) -> list[dict]:
    filepath = DATA_DIR / filename
    if not filepath.exists():
        print(f"[SKIP] {filepath} not found")
        return []
    with open(filepath, encoding="utf-8") as f:
        return json.load(f)


def ingest_kb_articles(engine: EmbeddingEngine) -> int:
    articles = load_json("kb_articles.json")
    if not articles:
        return 0

    for article in articles:
        # Combine title + description for richer embedding
        doc_text = f"{article['title']}. {article['description']}"
        engine.store_incident(
            incident_id=article["id"],
            description=doc_text,
            assigned_team=article["assigned_team"],
            resolution_notes=article["resolution_notes"],
            metadata={"category": article.get("category", ""), "source": "kb_article"},
        )
    print(f"[OK] Ingested {len(articles)} KB articles")
    return len(articles)


def main() -> None:
    engine = EmbeddingEngine()
    print(f"Collection count before ingestion: {engine.collection_count()}")

    total = 0
    total += ingest_kb_articles(engine)

    print(f"\nTotal documents ingested: {total}")
    print(f"Collection count after ingestion: {engine.collection_count()}")


if __name__ == "__main__":
    main()
