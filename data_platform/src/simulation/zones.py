"""Italian market zones and how each provider names them.

Each source spells the same zone differently; mapping them to one code is a silver-layer step. The
simulation reproduces each provider's own naming.
"""

# Canonical bidding-zone codes (GME naming), north to south.
ZONES = ["NORD", "CNOR", "CSUD", "SUD", "CALA", "SICI", "SARD"]

# Terna Total Load API, `bidding_zone` values (documented list; "Italy" is the national total).
TERNA_LOAD = {
    "NORD": "North",
    "CNOR": "Centre-North",
    "CSUD": "Centre-South",
    "SUD": "South",
    "CALA": "Calabria",
    "SICI": "Sicily",
    "SARD": "Sardinia",
}
TERNA_NATIONAL = "Italy"

# GME ME_ZonalPrices `Zone` values: the zone codes plus the national single price.
GME_PUN = "PUN"


def meteologica_area(zone: str) -> str:
    """Area label used in Meteologica content names, e.g. "Italy CNOR" (assumed from one observed name)."""
    return f"Italy {zone}"
