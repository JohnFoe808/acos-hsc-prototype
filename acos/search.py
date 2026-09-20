"""Opt-in, bounded trusted-source search.

The default provider is deterministic and local. Network access is never performed
unless a caller explicitly sets ``network=True`` and supplies an allowlisted domain.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

TRUSTED_SUFFIXES = (".gov", ".edu", ".org")
TRUSTED_HOSTS = {"docs.python.org", "developer.mozilla.org", "fastapi.tiangolo.com"}


def is_trusted_domain(domain: str) -> bool:
    host = domain.lower().strip().rstrip(".")
    return host in TRUSTED_HOSTS or host.endswith(TRUSTED_SUFFIXES)


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str


def local_search(query: str) -> list[dict[str, str]]:
    """Return safe, citation-ready results without making a network request."""
    return [
        {
            "title": "ACOS local search boundary",
            "url": "local://trusted-search",
            "snippet": f'No network request was made. Search terms received: "{query}".',
            "source": "deterministic-local-fallback",
        }
    ]


def validate_source_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or not is_trusted_domain(parsed.hostname):
        raise ValueError(
            "Only HTTPS URLs on allowlisted .gov, .edu, .org, or public-doc domains are allowed."
        )
    return url
