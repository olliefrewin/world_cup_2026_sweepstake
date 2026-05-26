# Tests for the team name reconciliation module.

from __future__ import annotations

import pytest

from sweepstake.data.team_names import canonicalise, API_TO_CANONICAL
from sweepstake.constants import ALL_TEAMS


def test_canonical_names_pass_through_unchanged():
    # Every canonical team name should survive canonicalise() unmodified.
    for team in ALL_TEAMS:
        assert canonicalise(team) == team, f"canonical name '{team}' was altered"


def test_known_api_quirks_mapped_correctly():
    assert canonicalise("USA") == "United States"
    assert canonicalise("Korea Republic") == "South Korea"
    assert canonicalise("Bosnia & Herzegovina") == "Bosnia and Herzegovina"
    assert canonicalise("Curacao") == "Curaçao"
    assert canonicalise("Côte d'Ivoire") == "Ivory Coast"
    assert canonicalise("Cape Verde Islands") == "Cape Verde"
    assert canonicalise("Czechia") == "Czech Republic"


def test_unknown_name_passes_through():
    assert canonicalise("Narnia FC") == "Narnia FC"


def test_all_mapped_values_are_canonical():
    # Every value in the mapping must be a recognised canonical team name.
    non_canonical = [v for v in API_TO_CANONICAL.values() if v not in ALL_TEAMS]
    assert non_canonical == [], f"Non-canonical values in API_TO_CANONICAL: {non_canonical}"
