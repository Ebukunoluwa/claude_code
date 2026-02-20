from __future__ import annotations

import re
from dataclasses import dataclass, field


def _normalise_nhs(nhs_input: str) -> str:
    """Strip all non-digit characters and return a 10-digit string."""
    return re.sub(r"\D", "", nhs_input)


def _names_match(expected: str, provided: str) -> bool:
    """Case-insensitive partial name match (covers first/last name variants)."""
    expected_parts = set(expected.lower().split())
    provided_parts = set(provided.lower().split())
    return bool(expected_parts & provided_parts)


@dataclass
class IdentityState:
    expected_name: str
    expected_nhs_number: str  # stored normalised (digits only)
    attempts: int = 0
    max_attempts: int = 2
    name_confirmed: bool = False
    nhs_confirmed: bool = False

    def __post_init__(self) -> None:
        self.expected_nhs_number = _normalise_nhs(self.expected_nhs_number)

    @property
    def verified(self) -> bool:
        return self.name_confirmed and self.nhs_confirmed

    @property
    def exhausted(self) -> bool:
        return self.attempts >= self.max_attempts and not self.verified

    def verify_name(self, provided_name: str) -> bool:
        result = _names_match(self.expected_name, provided_name)
        if result:
            self.name_confirmed = True
        return result

    def verify_nhs(self, provided_nhs: str) -> bool:
        normalised = _normalise_nhs(provided_nhs)
        result = normalised == self.expected_nhs_number
        if result:
            self.nhs_confirmed = True
        return result

    def increment_attempt(self) -> None:
        self.attempts += 1
