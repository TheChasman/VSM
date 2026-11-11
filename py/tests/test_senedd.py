import pytest

from vsm_py.ingest import IngestError, senedd

PAGE = """Senedd election 2026: Research Briefing


Testshire Môn


 Electorate:                          1,000
 Valid votes cast:                    700
 Total rejected ballot papers:        3
 Turnout:                             70.30%


  Political Party / Individual           Votes         Vote       Members         Candidates
            Candidate                     won         Share         elected

 Plaid Cymru                             300       42.86%            3                8
 Reform UK                               200       28.57%            2                6
 Welsh Labour                            100       14.29%            1                6
 Official Monster Raving                  60        8.57%            0                1
 Loony Party
 Welsh Christian Party                    40        5.71%            0         Individual


Elected Members
 Position              Member of the Senedd                            Political Party
      1                    A                                           Plaid Cymru
      2                    B                                           Reform UK
      3                    C                                           Plaid Cymru
      4                    D                                           Welsh Labour
      5                    E                                           Reform UK
      6                    F                                           Plaid Cymru

                                                24
"""


def test_parse_page_reads_fields_rows_and_order():
    c = senedd.parse_page(PAGE)
    assert (c.name, c.electorate, c.valid, c.rejected) == ("Testshire Môn", 1000, 700, 3)
    assert [r.name for r in c.lists][3] == "Official Monster Raving Loony Party"
    christian = c.lists[4]
    assert christian.individual and christian.candidates == 1
    assert c.order == ["Plaid Cymru", "Reform UK", "Plaid Cymru", "Welsh Labour", "Reform UK", "Plaid Cymru"]


def test_pages_without_results_are_skipped():
    assert senedd.parse_page("Senedd election 2026: Research Briefing\n\nIntroduction\n") is None


def test_order_must_agree_with_seats(tmp_path, monkeypatch):
    bad = PAGE.replace(
        "      4                    D                                           Welsh Labour",
        "      4                    D                                           Reform UK",
    )
    monkeypatch.setattr(senedd, "PdfReader", lambda _: type("R", (), {"pages": [_Page(bad)]})())
    with pytest.raises(IngestError, match="Reform UK won 2 but 3 in the order"):
        senedd.parse(tmp_path / "x.pdf")


def test_names_match_ignoring_case_and_spacing():
    assert senedd.norm("Pen-y-Bont  Bro Morgannwg") == senedd.norm("Pen-y-bont Bro Morgannwg")


class _Page:
    def __init__(self, text):
        self.text = text

    def extract_text(self, extraction_mode="plain"):
        return self.text
