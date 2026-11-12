import sqlite3

from vsm_py.ingest.digest import digest


def _db(path, rows, retrieved="2026-11-12T10:00:00"):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE source (source_id TEXT PRIMARY KEY, retrieved TEXT)")
    conn.execute("CREATE TABLE t (a INTEGER, b TEXT)")
    conn.execute("INSERT INTO source VALUES ('s', ?)", (retrieved,))
    conn.executemany("INSERT INTO t VALUES (?, ?)", rows)
    conn.commit()
    conn.close()
    return path


def test_ignores_row_order_and_retrieval_time(tmp_path):
    a = _db(tmp_path / "a.sqlite", [(1, "x"), (2, "y")])
    b = _db(tmp_path / "b.sqlite", [(2, "y"), (1, "x")], retrieved="2027-01-01T00:00:00")
    assert digest(a) == digest(b)


def test_detects_content_change(tmp_path):
    a = _db(tmp_path / "a.sqlite", [(1, "x")])
    b = _db(tmp_path / "b.sqlite", [(1, "z")])
    assert digest(a) != digest(b)
