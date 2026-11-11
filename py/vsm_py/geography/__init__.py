"""Constituency areas and the contiguity graph from the ONS July 2024 boundaries.

Areas are computed in British National Grid (EPSG:27700); Northern Ireland seats are
reprojected to Irish Grid (EPSG:29902) first (docs/05_COMPONENTS.md, geography).
"""


class GeographyError(Exception):
    """A stop condition from docs/05_COMPONENTS.md (geography failure modes)."""
