import csv
import json

import pytest

from hrd_scar import calculate_metrics, main, process_batch


def test_sum_of_precomputed_counts():
    result = calculate_metrics(loh=12, tai=4, lst=9)
    assert result["score"] == 25
    assert result["loh"] == 12
    assert result["tai"] == 4
    assert result["lst"] == 9
    assert result["classification"].startswith("Not interpreted")
    assert "not a validated" in result["clinical_recommendation"]


def test_historical_aliases_and_unrelated_numeric_columns():
    result = calculate_metrics(Patient_ID="PT-1", v1="10", v2="4", v3="9", age="72", severity=1000)
    assert result["score"] == 23
    assert result["inputs_evaluated"] == 3


@pytest.mark.parametrize("kwargs", [
    {}, {"loh": 4, "tai": 2}, {"loh": -1, "tai": 2, "lst": 3},
    {"loh": 0.5, "tai": 2, "lst": 3},
    {"loh": "nan", "tai": 2, "lst": 3},
    {"loh": "inf", "tai": 2, "lst": 3},
    {"loh": True, "tai": 2, "lst": 3},
    {"loh": "bad", "tai": 2, "lst": 3},
    {"loh": 1, "v1": 2, "tai": 2, "lst": 3},
])
def test_invalid_or_ambiguous_data_rejected(kwargs):
    with pytest.raises(ValueError):
        calculate_metrics(**kwargs)


def test_zero_counts_are_valid():
    assert calculate_metrics(loh=0, tai=0, lst=0)["score"] == 0


def test_batch_creates_output_and_preserves_metadata(tmp_path):
    source = tmp_path / "input.csv"
    target = tmp_path / "subdir" / "output.csv"
    source.write_text("Patient_ID,loh,tai,lst,age\nPT-A,10,5,2,90\nPT-B,1,2,3,35\n", encoding="utf-8")
    process_batch(str(source), str(target))
    with target.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert [row["score"] for row in rows] == ["17", "6"]
    assert [row["Patient_ID"] for row in rows] == ["PT-A", "PT-B"]
    assert rows[0]["age"] == "90"


def test_batch_empty_header_only(tmp_path):
    source, target = tmp_path / "input.csv", tmp_path / "output.csv"
    source.write_text("v1,v2,v3\n", encoding="utf-8")
    process_batch(str(source), str(target))
    assert "score" in target.read_text()


def test_batch_rejects_invalid_rows_without_writing(tmp_path):
    source, target = tmp_path / "input.csv", tmp_path / "output.csv"
    source.write_text("loh,tai,lst\n1,2,3\n4,,6\n", encoding="utf-8")
    with pytest.raises(ValueError, match="row 3"):
        process_batch(str(source), str(target))
    assert not target.exists()


def test_batch_rejects_extra_columns(tmp_path):
    source, target = tmp_path / "input.csv", tmp_path / "output.csv"
    source.write_text("loh,tai,lst\n1,2,3,4\n", encoding="utf-8")
    with pytest.raises(ValueError, match="column count"):
        process_batch(str(source), str(target))
    assert not target.exists()


def test_batch_disallows_source_overwrite(tmp_path):
    source = tmp_path / "input.csv"
    original = "loh,tai,lst\n1,2,3\n"
    source.write_text(original)
    with pytest.raises(ValueError, match="different"):
        process_batch(str(source), str(source))
    assert source.read_text() == original


def test_single_cli_and_aliases(capsys):
    main(["single", "--v1", "10", "--v2", "4", "--v3", "9"])
    result = json.loads(capsys.readouterr().out)
    assert result["score"] == 23


def test_single_default_values(capsys):
    main(["single"])
    assert json.loads(capsys.readouterr().out)["score"] == 17


def test_batch_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        process_batch(str(tmp_path / "missing.csv"), str(tmp_path / "output.csv"))
