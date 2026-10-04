"""FY26 store x article cleaning: header layouts, Reliance stacked tables, broken EANs, one row per store x month x product, totals unchanged."""
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import clean_offtake_fy26_store_article as cl  # noqa: E402

H_A = "Unique,Zone,State,City,Chain Name,Store Type,Site Code,Site Name,Article,EAN,Description as per Fountain,Brand,Category,Sub_category,Range,MRP,Sales Qty,MRP Sales Value,NSV,Month,Year,Source_Tab,Month_Std"
H_B = "Unnamed_1,Zone,State,City,Chain Name,Store Type,Site Code,Site Name,Article,EAN,Description as per Fountain,Brand,Category,Sub_category,Range,MRP,Sales Qty,MRP Sales Value,NSV,Month,Yr,PPT Category,Unnamed_2,Source_Tab,Month_Std"


def w(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


@pytest.fixture
def data(tmp_path):
    ap = tmp_path / "Apr'25"
    # chain A: WEST / West, INDORE / Indore, a truncated store name, two identical lines and one different line for the same store x article, a typo month tag
    w(ap / "Apollo.csv", H_A + "\n" + "\n".join([
        "x,WEST,Madhya Pradesh,INDORE,Apollo,Non Brand Counter,10011,LONG STORE NAME INDORE,A1,8904417300001,Face Wash 100ml,Mamaearth,Face,Face Wash,Ubtan,100,2,200,1.0,Apr,2025,T,Apr'25",
        "x,West,Madhya Pradesh,Indore,Apollo,Non Brand Counter,10011,LONG STORE NAME IND,A1,8904417300001,Face Wash 100 ml,Mamaearth,Face,Face Wash,Ubtan,100,2,200,1.0,Apr,2025,T,Apr'25",
        "x,West,Madhya Pradesh,Indore,Apollo,Non Brand Counter,10011,LONG STORE NAME INDORE,A1,8904417300001,Face Wash 100ml,Mamaearth,Face,Face Wash,Ubtan,100,1,100,0.5,Apr,2025,T,Aug'26"]))
    # chain B: another header layout, Excel scientific-notation EAN whose real EAN appears on another row of the same article code
    w(ap / "B&N.csv", H_B + "\n" + "\n".join([
        ",South-2,Telangana,Hyderabad,BEAUTY & NUTRIE,Non Brand Counter,1001,Kondapur,B1,8.9061E+12,Face Wash 150ml,Mamaearth,Face,Face Wash,Ubtan,200,1,200,1.5,Apr,2025,Face,,T,Apr'25",
        ",South-2,Telangana,Hyderabad,BEAUTY & NUTRIE,Non Brand Counter,1001,Kondapur,B1,8906087770001,Face Wash 150ml,Mamaearth,Face,Face Wash,Ubtan,200,1,200,1.5,Apr,2025,Face,,T,Apr'25"]))
    # Reliance: non counter table, then a Brand Counter block with no leading column and two extra fields
    w(ap / "Reliance.csv", H_B + "\n" + ",East,Bihar,,Reliance ,Pan India Reliance,,,R1,8904417300002,Sun 50g,Aqualogica,Face,Sun Care,Radiance+,449,1,449,3.0,Apr,2025,Aq,,Reliance_Non_Brand_Counter,Apr'25\n"
      + "East,Bihar,Patna,Reliance ,Brand Counter,6212.0,Dargamitta,R1,8904417300002,Sun 50g,Aqualogica,Face,Sun Care,Radiance+,449,1,449,2.0,Apr,2025,Aq,AA+,SMART,,Reliance_Brand_Counter,Apr'25\n")
    return tmp_path


def run(data):
    qc = []
    raw = cl.build([data], None, qc)
    return raw, cl.consolidate(raw), qc


def test_headers_read_by_name_and_reliance_counter_block_is_its_own_chain(data):
    raw, c, qc = run(data)
    assert set(c["chain"]) == {"Apollo", "B&N", "Reliance Retail", "Reliance Brand Counter"}
    bc = c[c["chain"] == "Reliance Brand Counter"].iloc[0]
    assert bc["NSV"] == 2.0 and bc["Site Code"] == "6212" and bc["City"] == "Patna"
    assert any("Brand Counter block re-aligned" in x[1] for x in qc)


def test_one_row_per_store_month_product_and_totals_do_not_change(data):
    raw, c, qc = run(data)
    ap = c[c["chain"] == "Apollo"]
    assert len(ap) == 1 and ap.iloc[0]["NSV"] == pytest.approx(2.5) and ap.iloc[0]["Sales Qty"] == 5 and ap.iloc[0]["MRP"] == pytest.approx(100)
    assert c["NSV"].sum() == pytest.approx(raw["NSV"].sum())
    cl.checks(raw, c, qc)
    assert not [x for x in qc if x[0] == "ERROR"], [x for x in qc if x[0] == "ERROR"]


def test_one_spelling_and_the_full_store_name(data):
    raw, c, qc = run(data)
    ap = c[c["chain"] == "Apollo"].iloc[0]
    assert (ap["Zone"], ap["City"]) == ("West", "Indore") and ap["Site Name"] == "LONG STORE NAME INDORE"
    assert ap["Description as per Fountain"] == "Face Wash 100ml"                     # one description per EAN (most frequent)


def test_excel_scientific_ean_is_repaired_and_month_typo_reported(data):
    raw, c, qc = run(data)
    bn = c[c["chain"] == "B&N"]
    assert list(bn["EAN"]) == ["8906087770001"] and bn.iloc[0]["NSV"] == pytest.approx(3.0)       # both lines are one product after the repair
    assert any("scientific notation" in x[1] and x[2] == 1 for x in qc)
    assert any("Month_Std tag disagrees" in x[1] and x[2] == 1 for x in qc)


def test_identical_lines_with_a_store_identity_are_listed_not_removed(data):
    raw, c, qc = run(data)
    d = cl.duplicate_lines(raw)
    # after the spellings and the repaired EAN, one Apollo line and one B&N line repeat an earlier line
    assert int(d["extra_lines"].sum()) == 2 and float(d["nsv_in_extra_lines"].sum()) == pytest.approx(2.5)
    assert c["NSV"].sum() == pytest.approx(raw["NSV"].sum())
