# Team name reconciliation between API-Football naming conventions and canonical names.
# Populated empirically by comparing API team list against the 48 canonical teams in constants.py.

from __future__ import annotations

# API name -> canonical name.
# Only entries where the names differ are listed; everything else passes through unchanged.
API_TO_CANONICAL: dict[str, str] = {
    # Common API variations observed for the 2026 World Cup squads
    "USA":                       "United States",
    "United States of America":  "United States",
    "Korea Republic":            "South Korea",
    "Republic of Korea":         "South Korea",
    "Turkey":                    "Türkiye",
    "Turkiye":                   "Türkiye",   # ASCII variant sometimes returned by the API
    "Curacao":                   "Curaçao",
    "DR Congo":                  "DR Congo",
    "Congo DR":                  "DR Congo",
    "Democratic Republic of the Congo": "DR Congo",
    "Bosnia & Herzegovina":      "Bosnia and Herzegovina",
    "Bosnia-Herzegovina":        "Bosnia and Herzegovina",
    "Ivory Coast":               "Ivory Coast",
    "Côte d'Ivoire":             "Ivory Coast",
    "Cote d'Ivoire":             "Ivory Coast",
    "Cape Verde Islands":        "Cape Verde",
    "Cabo Verde":                "Cape Verde",
    "Czech Republic":            "Czech Republic",
    "Czechia":                   "Czech Republic",
    "New Zealand":               "New Zealand",
    "Panama":                    "Panama",
    "Jordan":                    "Jordan",
    "Haiti":                     "Haiti",
    "Scotland":                  "Scotland",
    "Norway":                    "Norway",
    "Sweden":                    "Sweden",
    "Austria":                   "Austria",
    "Algeria":                   "Algeria",
    "Uzbekistan":                "Uzbekistan",
    "Colombia":                  "Colombia",
    "Ecuador":                   "Ecuador",
    "Tunisia":                   "Tunisia",
    "Saudi Arabia":              "Saudi Arabia",
    "South Africa":              "South Africa",
}

# Reverse map used for API key construction (canonical -> most likely API name)
_CANONICAL_TO_API: dict[str, str] = {v: k for k, v in API_TO_CANONICAL.items()}


def canonicalise(api_name: str) -> str:
    # Convert an API team name to the canonical name used throughout this app.
    # Returns the input unchanged if no mapping exists.
    return API_TO_CANONICAL.get(api_name, api_name)


def to_api_name(canonical: str) -> str:
    # Convert a canonical team name to the most likely API name.
    # Used when constructing API query parameters.
    return _CANONICAL_TO_API.get(canonical, canonical)
