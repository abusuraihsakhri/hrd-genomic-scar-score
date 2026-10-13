#!/usr/bin/env python3
"""Research-only arithmetic for precomputed LOH, TAI and LST scar counts.

The input event counts must originate from a separately validated genomic
pipeline. This module does not call variants, estimate HRD status, or recommend
treatment. No clinical cut-off is applied.
"""
import argparse
import csv
import json
from decimal import Decimal, InvalidOperation
import os
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
    """Sum explicitly named precomputed LOH, TAI and LST event counts.

    The historical v1/v2/v3 aliases remain supported. Unrelated fields
    (including identifiers and other numeric CSV columns) are not scored.
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
    """Score a CSV using LOH/TAI/LST (or v1/v2/v3) columns, preserving metadata.

    Validation is completed before output is written. The source CSV is never
    overwritten, including when the output path refers to the same file.
    """
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
        if any(field.lower() in OUTPUT_COLUMNS for field in fields):
            raise ValueError("CSV contains reserved output column names")
        header_keys = [field.lower() for field in fields]
        if len(set(header_keys)) != len(header_keys):
            raise ValueError("CSV contains case-insensitive duplicate columns")
        for metric, aliases in METRIC_ALIASES.items():
            if sum(alias in header_keys for alias in aliases) != 1:
                raise ValueError(f"CSV requires exactly one {metric.upper()} column")
        output_rows = []
        for line_number, row in enumerate(reader, start=2):
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"Malformed CSV row {line_number}: column count mismatch")
            try:
                result = calculate_metrics(**row)
            except ValueError as exc:
                raise ValueError(f"CSV row {line_number}: {exc}") from exc
            output_rows.append({**row, **{key: result[key] for key in OUTPUT_COLUMNS}})

    directory = os.path.dirname(os.path.abspath(output_csv))
    os.makedirs(directory, exist_ok=True)
    with open(output_csv, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields + list(OUTPUT_COLUMNS))
        writer.writeheader()
        writer.writerows(output_rows)
    print(f"Processed {len(output_rows)} records -> {output_csv}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Research-only HRD genomic-scar component sum")
    commands = parser.add_subparsers(dest="command", required=True)
    single = commands.add_parser("single", help="Sum LOH, TAI and LST event counts")
    single.add_argument("--loh", "--v1", dest="loh", type=float, default=10)
    single.add_argument("--tai", "--v2", dest="tai", type=float, default=5)
    single.add_argument("--lst", "--v3", dest="lst", type=float, default=2)
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
