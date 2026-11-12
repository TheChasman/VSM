import pytest

from vsm_py.ingest import IngestError, holyrood

C_HEAD = (
    "Constituency",
    "Total No of Candidates",
    "Electorate",
    "Total Votes",
    "Party A",
    "Party B ",
    "Independent Candidates",
    "Rejected Papers",
    "Majority",
    "Turnout ",
    "Rejected Papers",
)
S_HEAD = ("Constituency", "Total No of Candidates", "Party A", "Party B ", "Independent Candidates")


def constituencies(n=73, b_votes=40):
    votes = [("EMB", None), C_HEAD]
    seats = [("EMB", None), S_HEAD]
    for i in range(n):
        votes.append((f"Seat {i}  ", 3, 1000, 100 + b_votes + 10 + 5, 100, b_votes, 10, 5, 60, 0.5, 0.01))
        seats.append((f"Seat {i} ", 3, "ü", None, None))
    votes.append(("Total",))
    seats.append(("Total",))
    return votes, seats


def test_constituency_votes_winner_and_valid():
    cons = holyrood.parse_constituencies(*constituencies())
    c = cons[0]
    assert (c.name, c.electorate, c.valid, c.rejected) == ("Seat 0", 1000, 150, 5)
    assert c.votes == {"Party A": 100, "Party B": 40, "Independent Candidates": 10}
    assert c.winner == "Party A"


def test_constituency_votes_must_sum_to_valid():
    votes, seats = constituencies()
    votes[2] = votes[2][:5] + (41,) + votes[2][6:]
    with pytest.raises(IngestError, match="Seat 0: candidate votes sum to 151, valid 150"):
        holyrood.parse_constituencies(votes, seats)


def test_constituency_count_is_checked():
    with pytest.raises(IngestError, match="expected 73 constituencies"):
        holyrood.parse_constituencies(*constituencies(n=72))


R_HEAD = ("Region", "North", "South", "Total", "Share of Votes Cast")


def regions(south_seats_a=4):
    votes = [
        R_HEAD,
        ("Registered Parties",) + (None,) * 4,
        ("PARTY A", 600, 500, 1100, 0.5),
        ("PARTY B", 300, 400, 700, 0.3),
        ("Individual Candidates",) + (None,) * 4,
        ("SMITH, Jo", 0, 100, 100, 0.1),
        ("Rejected Papers", 2, 3, 5, 0.0),
        ("Total", 902, 1003, 1905, 1),
        (None,) * 5,
        ("Electorate", 2000, 2100, 4100, None),
    ]
    seats = [
        R_HEAD[:4],
        ("Registered Parties", None, None, None),
        ("PARTY A", 5, south_seats_a, 9),
        ("PARTY B", 2, 7 - south_seats_a, 9 - south_seats_a),
        ("Individual Candidates", None, None, None),
        ("SMITH, Jo", None, None, 0),
        ("Total", 7, 7, 14),
    ]
    return votes, seats


def test_regions_read_votes_seats_and_individuals():
    north, south = holyrood.parse_regions(*regions())
    assert (south.name, south.electorate, south.valid, south.rejected) == ("South", 2100, 1000, 3)
    assert south.votes == {"PARTY A": 500, "PARTY B": 400, "SMITH, Jo": 100}
    assert south.individuals == {"SMITH, Jo"}
    assert north.seats == {"PARTY A": 5, "PARTY B": 2}


def test_regions_need_seven_seats_each():
    votes, seats = regions()
    seats[3] = ("PARTY B", 2, 2, 4)
    with pytest.raises(IngestError, match="South: expected 7 list seats, got 6"):
        holyrood.parse_regions(votes, seats)


def test_emb_names_match_ons_names():
    assert holyrood.norm("South of Scotland") == "south scotland"
    assert holyrood.norm("Orkney") == holyrood.norm("Orkney Islands")
    assert holyrood.norm("Aberdeen South and North Kincardine  ") == "aberdeen south and north kincardine"
