"""reference.sqlite schema (docs/03_DATA_MODEL.md). Python stages are its only writers."""

from __future__ import annotations

import sqlite3

SCHEMA_VERSION = 5

DDL = """
CREATE TABLE IF NOT EXISTS meta (
  schema_version INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS source (
  source_id TEXT PRIMARY KEY,
  url TEXT NOT NULL,
  licence TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  retrieved TEXT NOT NULL,
  redistributable INTEGER NOT NULL CHECK (redistributable IN (0, 1))
);
CREATE TABLE IF NOT EXISTS geography_layer (
  layer_id TEXT PRIMARY KEY,
  description TEXT NOT NULL,
  gss_prefixes TEXT NOT NULL,
  drawn_by TEXT NOT NULL,
  valid_from TEXT NOT NULL,
  valid_to TEXT,
  source_id TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS geography_link (
  from_layer TEXT NOT NULL REFERENCES geography_layer(layer_id),
  from_code TEXT NOT NULL,
  to_layer TEXT NOT NULL REFERENCES geography_layer(layer_id),
  to_code TEXT NOT NULL,
  relation TEXT NOT NULL
    CHECK (relation IN ('exact', 'best_fit_population', 'area_weighted', 'partial')),
  share REAL CHECK ((relation = 'partial') = (share IS NULL)
                    AND (share IS NULL OR (share > 0 AND share <= 1))),
  derived INTEGER NOT NULL CHECK (derived IN (0, 1)),
  PRIMARY KEY (from_layer, from_code, to_layer, to_code)
);
CREATE TABLE IF NOT EXISTS area (
  layer_id TEXT NOT NULL REFERENCES geography_layer(layer_id),
  gss_code TEXT NOT NULL,
  name TEXT NOT NULL,
  PRIMARY KEY (layer_id, gss_code)
);
CREATE TABLE IF NOT EXISTS list_result (
  election_id TEXT NOT NULL,
  gss_code TEXT NOT NULL,
  list_seq INTEGER NOT NULL,
  party_code TEXT NOT NULL REFERENCES party(party_code),
  individual_name TEXT,  -- set for an individual (non-party) candidate, whose list size is 1
  votes INTEGER NOT NULL,
  seats INTEGER NOT NULL,
  candidates INTEGER CHECK (candidates IS NULL OR candidates >= seats),  -- NULL: list size not published
  PRIMARY KEY (election_id, gss_code, list_seq),
  FOREIGN KEY (election_id, gss_code) REFERENCES contest(election_id, gss_code)
);
CREATE TABLE IF NOT EXISTS seat_order (
  election_id TEXT NOT NULL,
  gss_code TEXT NOT NULL,
  position INTEGER NOT NULL,
  list_seq INTEGER NOT NULL,
  PRIMARY KEY (election_id, gss_code, position),
  FOREIGN KEY (election_id, gss_code, list_seq) REFERENCES list_result(election_id, gss_code, list_seq)
);
CREATE TABLE IF NOT EXISTS election (
  election_id TEXT PRIMARY KEY,
  office TEXT NOT NULL CHECK (office IN ('commons', 'devolved', 'council', 'executive')),
  polling_date TEXT NOT NULL,
  boundary_set TEXT NOT NULL,
  source_id TEXT NOT NULL REFERENCES source(source_id)
);
CREATE TABLE IF NOT EXISTS constituency (
  gss_code TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  nation TEXT NOT NULL CHECK (nation IN ('E', 'S', 'W', 'N')),
  region TEXT,
  county TEXT,
  electorate INTEGER NOT NULL,
  area_km2 REAL,  -- filled by geography; NULL until then
  protected INTEGER NOT NULL CHECK (protected IN (0, 1))
);
CREATE TABLE IF NOT EXISTS party (
  party_code TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  aliases TEXT
);
CREATE TABLE IF NOT EXISTS contest (
  election_id TEXT NOT NULL REFERENCES election(election_id),
  gss_code TEXT NOT NULL,
  electorate INTEGER NOT NULL,
  valid_votes INTEGER NOT NULL,
  invalid_votes INTEGER,
  declared_at TEXT,
  PRIMARY KEY (election_id, gss_code)
);
CREATE TABLE IF NOT EXISTS candidate_result (
  election_id TEXT NOT NULL,
  gss_code TEXT NOT NULL,
  candidate_seq INTEGER NOT NULL,
  party_code TEXT NOT NULL REFERENCES party(party_code),
  votes INTEGER NOT NULL,
  elected INTEGER NOT NULL CHECK (elected IN (0, 1)),
  PRIMARY KEY (election_id, gss_code, candidate_seq),
  FOREIGN KEY (election_id, gss_code) REFERENCES contest(election_id, gss_code)
);
"""


def connect(path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(DDL)
    row = conn.execute("SELECT schema_version FROM meta").fetchone()
    if row is None:
        conn.execute("INSERT INTO meta (schema_version) VALUES (?)", (SCHEMA_VERSION,))
        conn.commit()
    elif row[0] != SCHEMA_VERSION:
        raise RuntimeError(f"reference.sqlite schema {row[0]}, expected {SCHEMA_VERSION}: rebuild it")
    return conn
