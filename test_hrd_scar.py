import pytest
import os
from hrd_scar import calculate_metrics, process_batch, process_single, main


class TestCalculateMetrics:
    """Tests for the core calculate_metrics function."""

    def test_basic_scoring(self):
        res = calculate_metrics(v1=12.0, v2=4.0)
        assert "score" in res
        assert "classification" in res
        assert "clinical_recommendation" in res
        assert res["score"] > 0
        assert res["tool"] == "hrd-genomic-scar-score"

    def test_low_tier_classification(self):
        res = calculate_metrics(v1=5.0, v2=2.0)
        assert res["classification"] == "Low / Standard"
        assert res["score"] < 10.0

    def test_moderate_tier_classification(self):
        res = calculate_metrics(v1=15.0, v2=5.0)
        assert res["classification"] == "Moderate / Intermediate"
        assert 10.0 <= res["score"] < 25.0

    def test_high_tier_classification(self):
        res = calculate_metrics(v1=30.0, v2=10.0)
        assert res["classification"] == "High / Severe"
        assert res["score"] >= 25.0

    def test_empty_input_defaults(self):
        res = calculate_metrics()
        assert res["score"] == 1.0
        assert res["inputs_evaluated"] == 0

    def test_none_values_ignored(self):
        res = calculate_metrics(v1=10.0, v2=None, v3=5.0)
        assert res["inputs_evaluated"] == 2

    def test_string_values_converted(self):
        res = calculate_metrics(v1="15.5", v2="3.2")
        assert res["score"] > 0
        assert res["inputs_evaluated"] == 2

    def test_mixed_types(self):
        res = calculate_metrics(v1=10.0, v2="abc", v3=5.0)
        assert res["inputs_evaluated"] == 3
        assert res["score"] > 0

    def test_score_calculation_formula(self):
        # score = v1 + v2/2 + v3/3
        res = calculate_metrics(v1=10.0, v2=4.0, v3=9.0)
        expected = round(10.0 + 4.0/2 + 9.0/3, 2)
        assert res["score"] == expected

    def test_output_fields(self):
        res = calculate_metrics(v1=10.0)
        assert "tool" in res
        assert "score" in res
        assert "classification" in res
        assert "clinical_recommendation" in res
        assert "inputs_evaluated" in res


class TestProcessBatch:
    """Tests for batch CSV processing."""

    def test_batch_creates_output(self, tmp_path):
        csv_in = tmp_path / "in.csv"
        csv_out = tmp_path / "out.csv"
        csv_in.write_text("Patient,v1,v2\nPat_001,15.0,3.0\nPat_002,5.0,1.0\n", encoding="utf-8")

        process_batch(str(csv_in), str(csv_out))
        assert csv_out.exists()

    def test_batch_output_content(self, tmp_path):
        csv_in = tmp_path / "in.csv"
        csv_out = tmp_path / "out.csv"
        csv_in.write_text("Patient,v1,v2\nPat_001,15.0,3.0\nPat_002,5.0,1.0\n", encoding="utf-8")

        process_batch(str(csv_in), str(csv_out))
        content = csv_out.read_text(encoding="utf-8")
        assert "Pat_001" in content
        assert "Pat_002" in content
        assert "score" in content
        assert "classification" in content
        assert "clinical_recommendation" in content

    def test_batch_missing_file_raises(self, tmp_path):
        csv_in = tmp_path / "nonexistent.csv"
        csv_out = tmp_path / "out.csv"
        with pytest.raises(FileNotFoundError):
            process_batch(str(csv_in), str(csv_out))

    def test_batch_creates_output_directory(self, tmp_path):
        csv_in = tmp_path / "in.csv"
        csv_out = tmp_path / "subdir" / "out.csv"
        csv_in.write_text("Patient,v1\nPat_001,10.0\n", encoding="utf-8")

        process_batch(str(csv_in), str(csv_out))
        assert csv_out.exists()

    def test_batch_empty_csv(self, tmp_path):
        csv_in = tmp_path / "in.csv"
        csv_out = tmp_path / "out.csv"
        csv_in.write_text("Patient,v1,v2\n", encoding="utf-8")

        process_batch(str(csv_in), str(csv_out))
        assert csv_out.exists()
        content = csv_out.read_text(encoding="utf-8")
        assert "score" in content


class TestMainCLI:
    """Tests for the main CLI entry point."""

    def test_single_command(self, capsys):
        main(["single", "--v1", "10.0", "--v2", "5.0"])
        captured = capsys.readouterr()
        assert "hrd-genomic-scar-score" in captured.out
        assert "score" in captured.out

    def test_single_default_values(self, capsys):
        main(["single"])
        captured = capsys.readouterr()
        assert "score" in captured.out

    def test_batch_command(self, tmp_path):
        csv_in = tmp_path / "in.csv"
        csv_out = tmp_path / "out.csv"
        csv_in.write_text("v1,v2\n10.0,5.0\n", encoding="utf-8")

        main(["batch", "-i", str(csv_in), "-o", str(csv_out)])
        assert csv_out.exists()
