from __future__ import annotations

import re
import unicodedata
from collections import Counter
from typing import Iterable, List, Sequence, Set


STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "of",
    "on",
    "or",
    "paper",
    "results",
    "system",
    "that",
    "the",
    "their",
    "these",
    "this",
    "to",
    "using",
    "with",
}


def normalize_text(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"\s+", " ", ascii_text).strip()


def tokenize(text: str) -> List[str]:
    tokens = re.findall(r"[a-z][a-z0-9\-]{2,}", normalize_text(text))
    return [token for token in tokens if token not in STOP_WORDS]


def token_set(text: str) -> Set[str]:
    return set(tokenize(text))


def token_counter(text: str) -> Counter[str]:
    return Counter(tokenize(text))


def jaccard_similarity(left: Iterable[str], right: Iterable[str]) -> float:
    left_set = set(left)
    right_set = set(right)
    if not left_set and not right_set:
        return 0.0
    union = left_set | right_set
    if not union:
        return 0.0
    return len(left_set & right_set) / len(union)


def ngrams(tokens: Sequence[str], size: int = 3) -> Set[str]:
    if len(tokens) < size:
        return set()
    return {" ".join(tokens[index : index + size]) for index in range(len(tokens) - size + 1)}


def text_similarity(title_a: str, abstract_a: str, title_b: str, abstract_b: str) -> dict:
    title_tokens_a = tokenize(title_a)
    title_tokens_b = tokenize(title_b)
    body_tokens_a = tokenize(f"{title_a} {abstract_a}")
    body_tokens_b = tokenize(f"{title_b} {abstract_b}")
    title_overlap = jaccard_similarity(title_tokens_a, title_tokens_b)
    token_overlap = jaccard_similarity(body_tokens_a, body_tokens_b)
    trigram_overlap = jaccard_similarity(ngrams(body_tokens_a), ngrams(body_tokens_b))
    return {
        "title_overlap": round(title_overlap, 4),
        "token_overlap": round(token_overlap, 4),
        "trigram_overlap": round(trigram_overlap, 4),
        "overall": round(max(title_overlap * 0.45 + token_overlap * 0.35 + trigram_overlap * 0.2, 0.0), 4),
    }
