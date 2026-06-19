from __future__ import annotations

import argparse
import json
from pathlib import Path

from .inspector import inspect_csv, result_to_dict, write_cleaned_csv
from .report import render_html_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cleansight",
        description="Inspect a CSV file for common data quality issues and generate a report.",
    )
    parser.add_argument("source", help="Path to the source CSV file.")
    parser.add_argument("--report", default="reports/cleansight-report.html", help="HTML report output path.")
    parser.add_argument("--cleaned", default="reports/cleaned-data.csv", help="Cleaned CSV output path.")
    parser.add_argument("--json", default="reports/cleansight-summary.json", help="JSON summary output path.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = inspect_csv(args.source)

    render_html_report(result, args.report)
    write_cleaned_csv(result, args.cleaned)

    json_path = Path(args.json)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result_to_dict(result), indent=2), encoding="utf-8")

    print(f"CleanSight scanned {result.row_count} rows and found {result.issue_count} quality signals.")
    print(f"Quality score: {result.quality_score}/100")
    print(f"Report: {args.report}")
    print(f"Cleaned CSV: {args.cleaned}")


if __name__ == "__main__":
    main()
