"""Fetch, verify and normalise source data into reference.sqlite. No modelling or imputation."""


class IngestError(Exception):
    """A stop condition from docs/05_COMPONENTS.md (ingest failure modes)."""
