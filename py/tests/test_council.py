import pytest

from vsm_py.ingest import IngestError, council

DAT = """4 Stirling North
2 3 3 9
Ann ALPHA, SNP
Bob BETA, Lab
Cara GAMMA, Con
5 1 2 0
3 0 1 2
1 3 2 1
"""


def test_ballot_file_header_candidates_and_rankings():
    w = council.parse_ballot_dat(DAT, "Stirling/4_Stirling_North.dat")
    assert (w.number, w.name, w.seats, w.valid) == (4, "Stirling North", 2, 9)
    assert w.candidates == ["Ann ALPHA", "Bob BETA", "Cara GAMMA"]
    # Ranks per candidate column become an ordered list of candidate indices.
    assert w.ballots == [(5, (0, 1)), (3, (1, 2)), (1, (2, 1, 0))]


def test_ballot_weights_must_sum_to_valid():
    with pytest.raises(IngestError, match="ballots sum to 9, header says 10"):
        council.parse_ballot_dat(DAT.replace("2 3 3 9", "2 3 3 10"), "x.dat")


def test_ballot_ranks_must_run_from_one_without_gaps():
    bad = DAT.replace("5 1 2 0", "5 1 3 0")
    with pytest.raises(IngestError, match="ranks"):
        council.parse_ballot_dat(bad, "x.dat")


def test_ballot_line_count_is_checked():
    with pytest.raises(IngestError, match="expected 4 ballot lines"):
        council.parse_ballot_dat(DAT.replace("2 3 3 9", "2 3 4 9"), "x.dat")


def test_uncontested_ward_has_no_ballots():
    w = council.parse_ballot_dat("3 Buckie\n3 3 0 0\nA X, Con\nB Y, SLD\nC Z, SNP\n", "x.dat")
    assert (w.seats, w.valid, w.ballots) == (3, 0, [])


def emb_row(council_name, ward, included, name, elected, stage, party, fp, electorate=1000, rejected=5):
    row = [None] * 20
    row[0], row[1], row[2], row[3], row[4] = "Report", council_name, ward, electorate, included
    row[10], row[11] = rejected, included + rejected
    row[12], row[13], row[14], row[16], row[17] = name, elected, stage, party, fp
    return tuple(row)


def test_emb_rows_group_by_ward_and_check_first_preferences():
    rows = [
        emb_row(
            "Stirling Council", "Stirling North Ward", 9, "Ann ALPHA", "Yes", 1, "Scottish National Party", 6
        ),
        emb_row(
            "Stirling Council", "Stirling North Ward", 9, "Bob BETA", "Yes", 3, "Scottish Labour Party", 2
        ),
        emb_row("Stirling Council", "Stirling North Ward", 9, "Cara GAMMA", "No", None, "Independent", 1),
    ]
    wards = council.parse_emb_rows(rows)
    w = wards[("Stirling Council", "Stirling North Ward")]
    assert (w.electorate, w.valid, w.rejected) == (1000, 9, 5)
    assert [(c.name, c.votes, c.stage_elected) for c in w.candidates] == [
        ("Ann ALPHA", 6, 1),
        ("Bob BETA", 2, 3),
        ("Cara GAMMA", 1, None),
    ]


def test_emb_first_preferences_must_sum_to_ballots_counted():
    rows = [
        emb_row("C", "W", 9, "A", "Yes", 1, "P", 6),
        emb_row("C", "W", 9, "B", "No", None, "P", 2),
    ]
    with pytest.raises(IngestError, match="C / W: first preferences sum to 8, ballots counted 9"):
        council.parse_emb_rows(rows)


def test_emb_elected_needs_a_stage():
    rows = [emb_row("C", "W", 6, "A", "Yes", None, "P", 6)]
    with pytest.raises(IngestError, match="C / W: A elected without a stage"):
        council.parse_emb_rows(rows)


@pytest.mark.parametrize(
    ("raw", "key"),
    [
        ("Ward 1 - Boness and Blackness", "bonessandblackness"),
        ("Bo'ness and Blackness", "bonessandblackness"),
        ("Airyhall/Broomhill/Garthdee Ward", "airyhallbroomhillgarthdee"),
        ("Ward 6 Sgìr’ Ùige agus Carlabhagh", "sgìrùigeaguscàrlabhagh"),
        ("Leith Walk (Ward 12)", "leithwalk"),
        ("3. Forth & Endrick", "forthandendrick"),
    ],
)
def test_ward_key(raw, key):
    assert council.ward_key(raw) == key


def test_ballot_candidates_match_emb_names_ignoring_case_and_spacing():
    order = council.match_candidates(
        ["Kenneth John MACLEAN", "Ann  ALPHA"], ["Ann Alpha", "Kenneth John MacLean"]
    )
    assert order == [1, 0]


def test_ballot_candidates_must_all_match():
    with pytest.raises(IngestError, match="no EMB candidate for 'Zed ZETA'"):
        council.match_candidates(["Zed ZETA"], ["Ann ALPHA"])


STAGES = """The City of Edinburgh Council
Candidate Votes Per Stage Report
Contest Name Ward 4 - Forth
Total Number of Valid Votes 10,555
Positions to be Filled 4
Quota 2,112
Stage 1
Candidate Name Affiliation Votes Transferred Votes Status
JIM CAMPBELL Scottish Conservative and
Unionist
1,594
Cammy DAY Labour and Co-operative Party 1,995 Elected
Kerry Elizabeth HEATHCOTE Women's Equality Party 130
Non-transferable votes 0
Non-transferable votes due to rounding 0
3,719Total
Report Name: CandidateVotesPerStageReport_V0001.pdf Created: 06-5-2022 11:21:56
The City of Edinburgh Council
Candidate Votes Per Stage Report
Stage 2
Exclusion of Kerry Elizabeth HEATHCOTE 130.00000
Candidate Name Affiliation Votes Transferred Votes Status
JIM CAMPBELL Scottish Conservative and
Unionist
4.00000 1,598.00000
Cammy DAY Labour and Co-operative Party 19.00000 2,014.00000 Elected
Kerry Elizabeth HEATHCOTE Women's Equality Party -130.00000 0.00000
Non-transferable votes 24.00000 24.00000
Non-transferable votes due to rounding 0.12345 0.12345
3,636.12345Total
"""


def test_stage_report_totals_in_fixed_point():
    names = ["JIM CAMPBELL", "Cammy DAY", "Kerry Elizabeth HEATHCOTE"]
    rep = council.parse_stage_text(STAGES, names)
    assert (rep.valid, rep.seats, rep.quota) == (10555, 4, 2112)
    assert rep.stages == [
        [159_400_000, 199_500_000, 13_000_000, 0],
        [159_800_000, 201_400_000, 0, 2_412_345],
    ]


def test_stage_report_needs_every_candidate_each_stage():
    with pytest.raises(IngestError, match="stage 1: no total for 'Nobody HERE'"):
        council.parse_stage_text(STAGES, ["JIM CAMPBELL", "Nobody HERE"])


def test_quoted_candidate_line_keeps_only_the_name():
    dat = DAT.replace("Cara GAMMA, Con", '"Cara GAMMA" "Scottish Greens â€“ Think Global, Act Local", ')
    assert council.parse_ballot_dat(dat, "x.dat").candidates[2] == "Cara GAMMA"


def test_emb_mojibake_is_repaired():
    assert council.repair("Peter Ã“ DONNGHAILE") == "Peter Ó DONNGHAILE"
    assert council.repair("Plain NAME") == "Plain NAME"


def test_listed_candidate_spelling_pairs():
    # Mollison's file drops the accent: "Peter A DONNGHAILE" for "Peter Ó DONNGHAILE".
    assert council.match_candidates(["Peter A DONNGHAILE"], ["Peter Ó Donnghaile"]) == [0]
