from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as element_tree
from datetime import timedelta
from typing import Any, Dict, List, Optional

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

from rf_standalone.flow_common import (
    canonical_paper_id,
    now_utc,
    term_hits,
    utc_timestamp,
)

ARXIV_NS = {
    "atom": "http://www.w3.org/2005/Atom",
}


def _request(
    url: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int,
    retry_limit: int,
    expect_json: bool,
    as_bytes: bool = False,
) -> Any:
    final_headers = dict(headers or {})
    query = urllib.parse.urlencode(params or {})
    final_url = url if not query else f"{url}?{query}"
    last_error: Optional[Exception] = None
    for attempt in range(retry_limit):
        try:
            if requests is not None:
                response = requests.get(final_url, headers=final_headers, timeout=timeout)
                response.raise_for_status()
                if expect_json:
                    return response.json()
                return response.content if as_bytes else response.text
            request = urllib.request.Request(final_url, headers=final_headers)
            with urllib.request.urlopen(request, timeout=timeout) as handle:
                raw = handle.read()
            if expect_json:
                return json.loads(raw.decode("utf-8"))
            return raw if as_bytes else raw.decode("utf-8")
        except Exception as error:  # pragma: no cover - network dependent
            last_error = error
            if attempt + 1 < retry_limit:
                time.sleep(2 ** attempt)
    if last_error is None:
        raise RuntimeError(f"request failed without error for {final_url}")
    raise RuntimeError(f"request failed for {final_url}: {last_error}")


def fetch_arxiv_candidates(workflow: Dict[str, Any], profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    arxiv_config = workflow.get("sources", {}).get("arxiv", {})
    if not arxiv_config.get("enabled", False):
        return []

    categories = arxiv_config.get("categories", [])
    lookback_days = int(arxiv_config.get("lookback_days", 30))
    max_results = int(min(arxiv_config.get("max_results", 100), profile.get("max_candidates", 100)))
    if not categories:
        return []

    end_date = now_utc()
    start_date = end_date - timedelta(days=lookback_days)
    category_query = " OR ".join(f"cat:{category}" for category in categories)
    date_query = "submittedDate:[{}0000 TO {}2359]".format(
        start_date.strftime("%Y%m%d"),
        end_date.strftime("%Y%m%d"),
    )
    search_query = f"({category_query}) AND {date_query}"
    payload = _request(
        "https://export.arxiv.org/api/query",
        params={
            "search_query": search_query,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "max_results": max_results,
        },
        timeout=int(workflow.get("runtime", {}).get("request_timeout_seconds", 20)),
        retry_limit=int(workflow.get("runtime", {}).get("retry_limit", 3)),
        expect_json=False,
    )

    root = element_tree.fromstring(payload)
    entries: List[Dict[str, Any]] = []
    fetched_at = utc_timestamp()
    include_terms = profile.get("include_terms", [])
    for entry in root.findall("atom:entry", ARXIV_NS):
        title = (entry.findtext("atom:title", default="", namespaces=ARXIV_NS) or "").strip()
        abstract = (entry.findtext("atom:summary", default="", namespaces=ARXIV_NS) or "").strip()
        source_url = (entry.findtext("atom:id", default="", namespaces=ARXIV_NS) or "").strip()
        authors = [
            author.findtext("atom:name", default="", namespaces=ARXIV_NS)
            for author in entry.findall("atom:author", ARXIV_NS)
        ]
        categories_found = [node.attrib.get("term", "") for node in entry.findall("atom:category", ARXIV_NS)]
        pdf_url = ""
        for node in entry.findall("atom:link", ARXIV_NS):
            if node.attrib.get("title") == "pdf":
                pdf_url = node.attrib.get("href", "")
                break
        paper_id = canonical_paper_id(source_url or title, "arxiv")
        combined_text = f"{title}\n{abstract}"
        entries.append(
            {
                "run_id": "",
                "profile_id": profile["profile_id"],
                "paper_id": paper_id,
                "source": "arxiv",
                "source_record_id": source_url,
                "title": title,
                "abstract": abstract,
                "authors": [author for author in authors if author],
                "published_at": entry.findtext("atom:published", default="", namespaces=ARXIV_NS),
                "updated_at": entry.findtext("atom:updated", default="", namespaces=ARXIV_NS),
                "categories": [value for value in categories_found if value],
                "source_url": source_url,
                "pdf_url": pdf_url,
                "citation_count": 0,
                "influential_citation_count": 0,
                "profile_hits": term_hits(combined_text, include_terms),
                "state": "discovered",
                "fetched_at": fetched_at,
            }
        )
    return entries


def fetch_semantic_scholar_candidates(
    workflow: Dict[str, Any],
    profile: Dict[str, Any],
) -> List[Dict[str, Any]]:
    source_config = workflow.get("sources", {}).get("semantic_scholar", {})
    if not source_config.get("enabled", False):
        return []

    include_terms = profile.get("include_terms", [])
    if not include_terms:
        return []

    query = " ".join(include_terms[:6])
    api_key_env = source_config.get("api_key_env", "")
    headers = {"User-Agent": "ResearchFoundry/1.0"}
    if api_key_env:
        from os import environ

        api_key = environ.get(api_key_env)
        if api_key:
            headers["x-api-key"] = api_key

    payload = _request(
        "https://api.semanticscholar.org/graph/v1/paper/search",
        params={
            "query": query,
            "limit": min(int(source_config.get("max_results", 40)), int(profile.get("max_candidates", 40))),
            "fields": ",".join(
                [
                    "title",
                    "abstract",
                    "publicationDate",
                    "citationCount",
                    "influentialCitationCount",
                    "authors",
                    "url",
                    "externalIds",
                    "fieldsOfStudy",
                ]
            ),
        },
        headers=headers,
        timeout=int(workflow.get("runtime", {}).get("request_timeout_seconds", 20)),
        retry_limit=int(workflow.get("runtime", {}).get("retry_limit", 3)),
        expect_json=True,
    )

    fetched_at = utc_timestamp()
    records: List[Dict[str, Any]] = []
    for item in payload.get("data", []):
        title = item.get("title") or ""
        abstract = item.get("abstract") or ""
        if not title or not abstract:
            continue
        external_ids = item.get("externalIds") or {}
        source_record_id = external_ids.get("ArXiv") or item.get("url") or title
        paper_id = canonical_paper_id(source_record_id, "semantic-scholar")
        records.append(
            {
                "run_id": "",
                "profile_id": profile["profile_id"],
                "paper_id": paper_id,
                "source": "semantic_scholar",
                "source_record_id": source_record_id,
                "title": title,
                "abstract": abstract,
                "authors": [author.get("name") for author in item.get("authors", []) if author.get("name")],
                "published_at": item.get("publicationDate") or "",
                "updated_at": item.get("publicationDate") or "",
                "categories": item.get("fieldsOfStudy") or [],
                "source_url": item.get("url") or "",
                "pdf_url": "",
                "citation_count": int(item.get("citationCount") or 0),
                "influential_citation_count": int(item.get("influentialCitationCount") or 0),
                "profile_hits": term_hits(f"{title}\n{abstract}", include_terms),
                "state": "discovered",
                "fetched_at": fetched_at,
            }
        )
    return records
