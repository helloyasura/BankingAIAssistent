import re
from collections import Counter

from app.domain.ports.python_analysis_port import PythonAnalysisPort

_TOKEN = re.compile(r"[a-z]{3,}")


def _tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


def _count_by_field(chunks: list[dict], field: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for chunk in chunks:
        value = chunk.get("metadata", {}).get(field) or chunk.get(field, "")
        if not value:
            match = re.search(rf"{field.replace('_', ' ')}:\s*([^\n.]+)", chunk.get("content", ""), re.I)
            value = match.group(1).strip() if match else "unknown"
        counts[str(value)] += 1
    return dict(counts.most_common())


def _extract_root_cause_themes(chunks: list[dict]) -> dict[str, int]:
    themes: Counter[str] = Counter()
    pattern = re.compile(r"root cause[:\s-]+([^\n.]+)", re.IGNORECASE)
    for chunk in chunks:
        content = chunk.get("content", "")
        match = pattern.search(content)
        if match:
            themes[match.group(1).strip().lower()] += 1
        elif theme := chunk.get("metadata", {}).get("root_cause"):
            themes[str(theme).lower()] += 1
    return dict(themes.most_common())


def _recurring_keywords(chunks: list[dict], top_n: int = 10) -> list[dict]:
    stop = {
        "the", "and", "for", "with", "from", "this", "that", "were", "was",
        "are", "has", "have", "into", "under", "incident", "summary",
    }
    counts: Counter[str] = Counter()
    for chunk in chunks:
        for token in _tokenize(chunk.get("content", "")):
            if token not in stop:
                counts[token] += 1
    return [{"keyword": word, "count": count} for word, count in counts.most_common(top_n)]


def _summarize_metadata(chunks: list[dict]) -> dict:
    departments = _count_by_field(chunks, "department")
    document_types = _count_by_field(chunks, "document_type")
    return {
        "chunk_count": len(chunks),
        "departments": departments,
        "document_types": document_types,
        "titles": [chunk.get("title", "") for chunk in chunks[:5]],
    }


class PythonAnalysisAdapter(PythonAnalysisPort):
    def analyze_chunks(self, chunks: list[dict], analysis_type: str) -> dict:
        analysis_type = analysis_type.lower()
        if analysis_type == "root_cause":
            return {
                "analysis_type": analysis_type,
                "root_cause_counts": _extract_root_cause_themes(chunks),
            }
        if analysis_type == "keywords":
            return {
                "analysis_type": analysis_type,
                "recurring_keywords": _recurring_keywords(chunks),
            }
        if analysis_type == "metadata":
            return {
                "analysis_type": analysis_type,
                "summary": _summarize_metadata(chunks),
            }
        return {
            "analysis_type": "general",
            "root_cause_counts": _extract_root_cause_themes(chunks),
            "recurring_keywords": _recurring_keywords(chunks),
            "summary": _summarize_metadata(chunks),
        }
