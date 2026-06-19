from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from statistics import mean, pstdev
from typing import Any


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_PATTERN = re.compile(r"^\+?[\d\s().-]{7,}$")
DATE_HINTS = ("date", "dob", "created", "updated", "closed", "started", "ended")
EMAIL_HINTS = ("email", "e-mail")
PHONE_HINTS = ("phone", "mobile", "cell")
CATEGORY_HINTS = ("status", "category", "segment", "region", "priority", "type")


@dataclass
class ColumnProfile:
    name: str
    total: int = 0
    missing: int = 0
    unique: int = 0
    invalid_dates: int = 0
    invalid_emails: int = 0
    invalid_phones: int = 0
    outliers: int = 0
    examples: list[str] = field(default_factory=list)


@dataclass
class InspectionResult:
    source: str
    row_count: int
    column_count: int
    duplicate_rows: int
    issue_count: int
    quality_score: int
    column_profiles: list[ColumnProfile]
    category_warnings: dict[str, list[str]]
    cleaned_rows: list[dict[str, str]]
    summary: list[str]


def normalize_value(value: str | None) -> str:
    return "" if value is None else value.strip()


def normalized_key(row: dict[str, str], headers: list[str]) -> tuple[str, ...]:
    return tuple(normalize_value(row.get(header)).lower() for header in headers)


def can_float(value: str) -> bool:
    if not value:
        return False
    try:
        float(value.replace(",", ""))
        return True
    except ValueError:
        return False


def parse_float(value: str) -> float:
    return float(value.replace(",", ""))


def looks_like_date_column(name: str) -> bool:
    lowered = name.lower()
    return any(hint in lowered for hint in DATE_HINTS)


def looks_like_email_column(name: str) -> bool:
    lowered = name.lower()
    return any(hint in lowered for hint in EMAIL_HINTS)


def looks_like_phone_column(name: str) -> bool:
    lowered = name.lower()
    return any(hint in lowered for hint in PHONE_HINTS)


def looks_like_category_column(name: str) -> bool:
    lowered = name.lower()
    return any(hint in lowered for hint in CATEGORY_HINTS)


def is_valid_date(value: str) -> bool:
    formats = ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%Y/%m/%d")
    return any(_try_date(value, fmt) for fmt in formats)


def _try_date(value: str, fmt: str) -> bool:
    try:
        datetime.strptime(value, fmt)
        return True
    except ValueError:
        return False


def clean_rows(rows: list[dict[str, str]], headers: list[str]) -> list[dict[str, str]]:
    cleaned: list[dict[str, str]] = []
    seen: set[tuple[str, ...]] = set()

    for row in rows:
        cleaned_row = {header: normalize_value(row.get(header)) for header in headers}
        key = normalized_key(cleaned_row, headers)
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(cleaned_row)

    return cleaned


def inspect_csv(path: str | Path) -> InspectionResult:
    source = Path(path)
    with source.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        headers = reader.fieldnames or []
        rows = list(reader)

    cleaned = clean_rows(rows, headers)
    duplicate_rows = len(rows) - len(cleaned)
    profiles: list[ColumnProfile] = []
    category_warnings: dict[str, list[str]] = {}

    for header in headers:
        values = [normalize_value(row.get(header)) for row in rows]
        non_empty = [value for value in values if value]
        profile = ColumnProfile(
            name=header,
            total=len(values),
            missing=len(values) - len(non_empty),
            unique=len(set(value.lower() for value in non_empty)),
            examples=non_empty[:3],
        )

        if looks_like_date_column(header):
            profile.invalid_dates = sum(1 for value in non_empty if not is_valid_date(value))

        if looks_like_email_column(header):
            profile.invalid_emails = sum(1 for value in non_empty if not EMAIL_PATTERN.match(value))

        if looks_like_phone_column(header):
            profile.invalid_phones = sum(1 for value in non_empty if not PHONE_PATTERN.match(value))

        numeric_values = [parse_float(value) for value in non_empty if can_float(value)]
        if len(numeric_values) >= 4:
            avg = mean(numeric_values)
            deviation = pstdev(numeric_values)
            if deviation:
                profile.outliers = sum(1 for value in numeric_values if abs(value - avg) > deviation * 2)

        if looks_like_category_column(header):
            category_warnings[header] = find_category_warnings(non_empty)

        profiles.append(profile)

    issue_count = duplicate_rows + sum(
        profile.missing
        + profile.invalid_dates
        + profile.invalid_emails
        + profile.invalid_phones
        + profile.outliers
        for profile in profiles
    ) + sum(len(items) for items in category_warnings.values())
    quality_score = max(0, round(100 - ((issue_count / max(1, len(rows) * max(1, len(headers)))) * 100)))
    summary = build_summary(rows, headers, duplicate_rows, issue_count, quality_score, profiles)

    return InspectionResult(
        source=str(source),
        row_count=len(rows),
        column_count=len(headers),
        duplicate_rows=duplicate_rows,
        issue_count=issue_count,
        quality_score=quality_score,
        column_profiles=profiles,
        category_warnings=category_warnings,
        cleaned_rows=cleaned,
        summary=summary,
    )


def find_category_warnings(values: list[str]) -> list[str]:
    warnings: list[str] = []
    lowered_groups: dict[str, set[str]] = defaultdict(set)
    for value in values:
        lowered_groups[value.lower()].add(value)

    for variants in lowered_groups.values():
        if len(variants) > 1:
            warnings.append(f"Inconsistent casing/spacing: {', '.join(sorted(variants))}")

    counts = Counter(value.lower() for value in values)
    rare_values = [value for value, count in counts.items() if count == 1 and len(counts) > 4]
    for value in rare_values[:4]:
        warnings.append(f"Rare category value: {value}")

    return warnings


def build_summary(
    rows: list[dict[str, str]],
    headers: list[str],
    duplicate_rows: int,
    issue_count: int,
    quality_score: int,
    profiles: list[ColumnProfile],
) -> list[str]:
    worst_missing = sorted(profiles, key=lambda profile: profile.missing, reverse=True)[:3]
    summary = [
        f"Scanned {len(rows)} rows across {len(headers)} columns.",
        f"Found {issue_count} total data quality signals.",
        f"Calculated a quality score of {quality_score}/100.",
    ]
    if duplicate_rows:
        summary.append(f"Removed {duplicate_rows} duplicate row(s) in the cleaned export.")
    if worst_missing and worst_missing[0].missing:
        columns = ", ".join(f"{profile.name} ({profile.missing})" for profile in worst_missing if profile.missing)
        summary.append(f"Highest missing-value columns: {columns}.")
    return summary


def write_cleaned_csv(result: InspectionResult, output_path: str | Path) -> None:
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not result.cleaned_rows:
        destination.write_text("", encoding="utf-8")
        return

    headers = list(result.cleaned_rows[0].keys())
    with destination.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=headers)
        writer.writeheader()
        writer.writerows(result.cleaned_rows)


def result_to_dict(result: InspectionResult) -> dict[str, Any]:
    return {
        "source": result.source,
        "row_count": result.row_count,
        "column_count": result.column_count,
        "duplicate_rows": result.duplicate_rows,
        "issue_count": result.issue_count,
        "quality_score": result.quality_score,
        "summary": result.summary,
        "category_warnings": result.category_warnings,
        "columns": [profile.__dict__ for profile in result.column_profiles],
    }
