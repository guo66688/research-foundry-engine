from __future__ import annotations

from typing import Any, Dict, List, Optional

from scripts.shared.flow_common import canonical_paper_id, days_since, term_hits


def _publication_date(item: Dict[str, Any]) -> str:
    raw_date = str(item.get("publicationDate") or "").strip()
    if raw_date:
        return raw_date
    year_value = item.get("year")
    if year_value is None:
        return ""
    try:
        year = int(year_value)
    except (TypeError, ValueError):
        return ""
    if year <= 0:
        return ""
    return f"{year}-01-01"


def _publication_year(item: Dict[str, Any], published_at: str) -> Optional[int]:
    year_value = item.get("year")
    try:
        if year_value is not None:
            parsed_year = int(year_value)
            if parsed_year > 0:
                return parsed_year
    except (TypeError, ValueError):
        pass
    if len(published_at) >= 4 and published_at[:4].isdigit():
        return int(published_at[:4])
    return None


def _recent_citation_velocity(citation_count: int, published_at: str) -> Optional[float]:
    age_days = days_since(published_at)
    if age_days is None:
        return None
    age_years = max(age_days / 365.0, 1.0 / 12.0)
    return round(float(citation_count) / age_years, 4)


def _paper_identifier(item: Dict[str, Any], fallback_title: str) -> str:
    external_ids = item.get("externalIds") or {}
    if not isinstance(external_ids, dict):
        external_ids = {}
    source_record_id = (
        str(external_ids.get("ArXiv") or "").strip()
        or str(external_ids.get("DOI") or "").strip()
        or str(external_ids.get("CorpusId") or "").strip()
        or str(item.get("paperId") or "").strip()
        or str(item.get("url") or "").strip()
        or fallback_title
    )
    return canonical_paper_id(source_record_id, "semantic-scholar")


def _venue_name(item: Dict[str, Any]) -> str:
    venue = str(item.get("venue") or "").strip()
    if venue:
        return venue
    publication_venue = item.get("publicationVenue") or {}
    if not isinstance(publication_venue, dict):
        return ""
    return str(publication_venue.get("name") or "").strip()


def _source_role(citation_count: int, influential_citation_count: int) -> str:
    if influential_citation_count >= 12 or citation_count >= 80:
        return "hot_backfill"
    return "trend_support"


def hotness_score(record: Dict[str, Any]) -> float:
    citation_count = float(record.get("citation_count", 0) or 0)
    influential = float(record.get("influential_citation_count", 0) or 0)
    velocity = float(record.get("recent_citation_velocity", 0.0) or 0.0)
    return round(influential * 2.2 + citation_count * 0.45 + velocity * 0.3, 4)


def within_window(published_at: str, history_window_days: int) -> bool:
    age_days = days_since(published_at)
    if age_days is None:
        return True
    return age_days <= max(int(history_window_days or 0), 1)


def build_record(
    item: Dict[str, Any],
    *,
    profile_id: str,
    include_terms: List[str],
    history_window_days: int,
    fetched_at: str,
) -> Optional[Dict[str, Any]]:
    title = str(item.get("title") or "").strip()
    abstract = str(item.get("abstract") or "").strip()
    if not title or not abstract:
        return None

    published_at = _publication_date(item)
    if published_at and not within_window(published_at, history_window_days):
        return None

    citation_count = int(item.get("citationCount") or 0)
    influential_citation_count = int(item.get("influentialCitationCount") or 0)
    paper_id = _paper_identifier(item, title)
    fields_of_study = [str(name).strip() for name in (item.get("fieldsOfStudy") or []) if str(name).strip()]
    publication_year = _publication_year(item, published_at)
    citation_velocity = _recent_citation_velocity(citation_count, published_at)
    source_role = _source_role(citation_count, influential_citation_count)
    venue = _venue_name(item)
    publication_types = item.get("publicationTypes") or []
    if not isinstance(publication_types, list):
        publication_types = []
    paper_type = str(publication_types[0]).strip() if publication_types else ""

    record: Dict[str, Any] = {
        "run_id": "",
        "profile_id": profile_id,
        "paper_id": paper_id,
        "source": "semantic_scholar",
        "source_role": source_role,
        "source_record_id": str(item.get("paperId") or item.get("url") or title),
        "title": title,
        "abstract": abstract,
        "authors": [str(author.get("name")).strip() for author in (item.get("authors") or []) if str(author.get("name", "")).strip()],
        "published_at": published_at,
        "updated_at": published_at,
        "categories": fields_of_study,
        "fields_of_study": fields_of_study,
        "source_url": str(item.get("url") or "").strip(),
        "pdf_url": str(item.get("openAccessPdf", {}).get("url") or "").strip() if isinstance(item.get("openAccessPdf"), dict) else "",
        "citation_count": citation_count,
        "influential_citation_count": influential_citation_count,
        "recent_citation_velocity": citation_velocity,
        "publication_year": publication_year,
        "venue": venue,
        "paper_type": paper_type,
        "profile_hits": term_hits(f"{title}\n{abstract}", include_terms),
        "state": "discovered",
        "fetched_at": fetched_at,
        "recency_days": days_since(published_at),
    }
    record["hotness_score"] = hotness_score(record)
    return record
