"""Identifier ports for governed dataset publications."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4


class PublicationIdGenerator(Protocol):
    """Generate identifiers for immutable public revisions."""

    def new_publication_id(self) -> str:
        """Return a new public publication identifier."""
        ...


class PublicationCandidateIdGenerator(Protocol):
    """Generate identifiers for publication candidates."""

    def new_publication_candidate_id(self) -> str:
        """Return a new publication candidate identifier."""
        ...


@dataclass(frozen=True)
class UuidPublicationIdGenerator:
    """Generate random UUID4 publication identifiers."""

    def new_publication_id(self) -> str:
        return f"publication_{uuid4().hex}"


@dataclass(frozen=True)
class UuidPublicationCandidateIdGenerator:
    """Generate random UUID4 publication candidate identifiers."""

    def new_publication_candidate_id(self) -> str:
        return f"publication_candidate_{uuid4().hex}"
