from __future__ import annotations

import re
from dataclasses import dataclass, field


def _normalise_nhs(nhs_input: str) -> str:
    """Strip all non-digit characters and return a 10-digit string."""
    return re.sub(r"\D", "", nhs_input)


def _normalise_postcode(pc: str) -> str:
    """Uppercase, strip all spaces."""
    return re.sub(r"\s+", "", pc.upper())


def _names_match(expected: str, provided: str) -> bool:
    """Case-insensitive partial name match (covers first/last name variants)."""
    expected_parts = set(expected.lower().split())
    provided_parts = set(provided.lower().split())
    return bool(expected_parts & provided_parts)


@dataclass
class IdentityState:
    expected_name: str
    expected_nhs_number: str       # stored normalised (digits only)
    expected_dob: str = ""         # YYYY-MM-DD or similar — PRIMARY verification
    expected_postcode: str = ""    # UK postcode — FALLBACK if DOB fails
    attempts: int = 0
    max_attempts: int = 2
    name_confirmed: bool = False
    dob_confirmed: bool = False
    postcode_confirmed: bool = False
    dob_failed: bool = False       # True once DOB has been tried and failed
    # DOB repeat-back flow
    awaiting_dob_confirm: bool = False   # agent repeated DOB, waiting for patient yes/no
    agent_dob_repeat: str = ""           # what the agent said when repeating the DOB

    def __post_init__(self) -> None:
        self.expected_nhs_number = _normalise_nhs(self.expected_nhs_number)
        self.expected_postcode = _normalise_postcode(self.expected_postcode)

    @property
    def verified(self) -> bool:
        return self.name_confirmed and (self.dob_confirmed or self.postcode_confirmed)

    @property
    def awaiting_postcode(self) -> bool:
        """True after DOB fails — now collecting postcode."""
        return self.dob_failed and not self.postcode_confirmed and not self.dob_confirmed

    def verify_name(self, provided_name: str) -> bool:
        result = _names_match(self.expected_name, provided_name)
        if result:
            self.name_confirmed = True
        return result

    def verify_dob(self, provided_dob: str) -> bool:
        """
        Compare provided DOB against expected.
        The agent extracts DDMMYYYY; the DB stores YYYY-MM-DD (→ YYYYMMDD when stripped).
        Normalise both to DDMMYYYY before comparing.
        Only marks dob_failed if we actually have an expected DOB to compare against.
        """
        provided_digits = re.sub(r"\D", "", provided_dob)
        expected_digits = re.sub(r"\D", "", self.expected_dob)

        # If expected_dob is not set, skip — don't poison the state
        if not expected_digits:
            return False

        # If expected is 8 digits in YYYYMMDD form (starts with 19xx or 20xx),
        # reorder to DDMMYYYY so it matches what the agent extracts.
        if len(expected_digits) == 8 and expected_digits[:2] in ("19", "20"):
            expected_digits = expected_digits[6:8] + expected_digits[4:6] + expected_digits[0:4]

        result = provided_digits == expected_digits
        if result:
            self.dob_confirmed = True
        else:
            self.dob_failed = True
        return result

    def verify_postcode(self, provided_postcode: str) -> bool:
        """Compare provided postcode (normalised) against expected."""
        provided_norm = _normalise_postcode(provided_postcode)
        result = bool(self.expected_postcode) and (provided_norm == self.expected_postcode)
        if result:
            self.postcode_confirmed = True
        return result

    # Keep verify_nhs for backward compatibility (inbound agent still uses it)
    def verify_nhs(self, provided_nhs: str) -> bool:
        normalised = _normalise_nhs(provided_nhs)
        return normalised == self.expected_nhs_number

    def increment_attempt(self) -> None:
        self.attempts += 1
