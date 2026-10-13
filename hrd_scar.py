#!/usr/bin/env python3
"""Research-only arithmetic for precomputed LOH, TAI and LST scar counts.

The input event counts must originate from a separately validated genomic
pipeline. This module does not call variants, estimate HRD status, or recommend
treatment. No clinical cut-off is applied.
"""
import argparse
import csv
import json
import os
from decimal import Decimal, InvalidOperation
from typing import Any

METRIC_ALIASES = {
    "loh": ("loh", "v1"),
    "tai": ("tai", "v2"),
    "lst": ("lst", "v3"),
}
OUTPUT_COLUMNS = ("loh", "tai", "lst", "score", "classification", "clinical_recommendation")
INTERPRETATION = "Not interpreted (assay-specific validation required)"
DISCLAIMER = (
    "Research use only: the sum of supplied event counts is not a validated "
    "HRD result or treatment recommendation."
)


def _event_count(value: Any, metric: str) -> int:
    if isinstance(value, bool) or value is None or str(value).strip() == "":
        raise ValueError(f"{metric} must be a non-negative integer event count")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"{metric} must be a non-negative integer event count") from exc
    if (
        not number.is_finite()
        or number < 0
        or number != number.to_integral_value()
        or number > 9007199254740991
    ):
        raise ValueError(f"{metric} must be a non-negative integer event count (maximum 2^53-1)")
    return int(number)


def calculate_metrics(**kwargs: Any) -> dict[str, Any]:
    """Sum named precomputed LOH, TAI and LST event counts.

    Historical v1/v2/v3 aliases remain supported. Other numeric CSV columns
    are treated as metadata and are never included in the result.
    """
    supplied = {str(key).lower(): value for key, value in kwargs.items()}
    metrics: dict[str, int] = {}
    for metric, aliases in METRIC_ALIASES.items():
        present = [key for key in aliases if key in supplied]
        if len(present) != 1:
            raise ValueError(
                f"Provide exactly one {metric.upper()} field "
                f"({', '.join(aliases)})"
            )
        metrics[metric] = _event_count(supplied[present[0]], metric.upper())

    return {
        "tool": "hrd-genomic-scar-score",
        **metrics,
        "score": sum(metrics.values()),
        "classification": INTERPRETATION,
        "clinical_recommendation": DISCLAIMER,
        "inputs_evaluated": 3,
    }


def process_single(args: argparse.Namespace) -> None:
    result = calculate_metrics(loh=args.loh, tai=args.tai, lst=args.lst)
    print(json.dumps(result, indent=2))


def process_batch(input_csv: str, output_csv: str) -> None:
    """Score CSV rows, preserving unrelated metadata and validating all rows."""
    if not os.path.isfile(input_csv):
        raise FileNotFoundError(f"Input CSV not found: {input_csv}")
    if os.path.abspath(input_csv) == os.path.abspath(output_csv) or (
        os.path.exists(output_csv) and os.path.samefile(input_csv, output_csv)
    ):
        raise ValueError("Input and output CSV paths must be different")

    with open(input_csv, "r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        if not fields or len(set(fields)) != len(fields):
            raise ValueError("CSV must have a nonempty header with unique columns")
        header_keys = [field.lower() for field in fields]
        if len(set(header_keys)) != len(header_keys):
            raise ValueError("CSV contains case-insensitive duplicate columns")
        if any(field in ("score", "classification", "clinical_recommendation") for field in header_keys):
            raise ValueError("CSV contains reserved output column names")
        for metric, aliases in METRIC_ALIASES.items():
            if sum(alias in header_keys for alias in aliases) != 1:
                raise ValueError(f"CSV requires exactly one {metric.upper()} column")

        added_columns = [key for key in OUTPUT_COLUMNS if key not in header_keys]
        output_rows = []
        for line_number, row in enumerate(reader, start=2):
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"Malformed CSV row {line_number}: column count mismatch")
            try:
                result = calculate_metrics(**row)
            except ValueError as exc:
                raise ValueError(f"CSV row {line_number}: {exc}") from exc
            safe_metadata = {}
            for key, value in row.items():
                if value and value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")):
                    safe_metadata[key] = "'" + value
                else:
                    safe_metadata[key] = value
            output_rows.append({**safe_metadata, **{key: result[key] for key in added_columns}})

    directory = os.path.dirname(os.path.abspath(output_csv))
    os.makedirs(directory, exist_ok=True)
    with open(output_csv, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields + added_columns)
        writer.writeheader()
        writer.writerows(output_rows)
    print(f"Processed {len(output_rows)} records -> {output_csv}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Research-only HRD genomic-scar component sum")
    commands = parser.add_subparsers(dest="command", required=True)
    single = commands.add_parser("single", help="Sum LOH, TAI and LST event counts")
    single.add_argument("--loh", "--v1", dest="loh", type=str, default="10")
    single.add_argument("--tai", "--v2", dest="tai", type=str, default="5")
    single.add_argument("--lst", "--v3", dest="lst", type=str, default="2")
    batch = commands.add_parser("batch", help="Process CSV of component event counts")
    batch.add_argument("-i", "--input", required=True)
    batch.add_argument("-o", "--output", default="results.csv")
    args = parser.parse_args(argv)
    try:
        if args.command == "single":
            process_single(args)
        else:
            process_batch(args.input, args.output)
    except (ValueError, OSError, csv.Error) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
