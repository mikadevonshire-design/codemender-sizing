#!/usr/bin/env python3
"""CodeMender Fleet Sizing Calculator.

Converts repository or organization-wide language byte counts (from GitHub
Linguist or REST APIs) into estimated Lines of Code (LOC), filters by
CodeMender-supported languages, classifies language volumes into Small
(<50k LOC), Medium (50k-250k LOC), and Large (>250k LOC) tiers, and estimates
repository counts and monthly Fleet Drift Scans using industry-standard
enterprise repository distributions.
"""

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

DEFAULT_BYTES_PER_LOC = 40  # Industry standard average (~40 bytes per line of code)

# CodeMender Default Supported Core Application Languages
# Languages: C/C++, Java, Python, TypeScript/JavaScript, Go, Rust, and Ruby
CORE_SUPPORTED_LANGUAGES = {
    "C",
    "C++",
    "Java",
    "Python",
    "TypeScript",
    "JavaScript",
    "Go",
    "Rust",
    "Ruby",
}

# CodeMender Supported Enterprise Framework / Web / Markup Languages
# Frameworks: HTML/CSS, Django, Flask, React, Spring Boot, and Express
FRAMEWORK_WEB_LANGUAGES = {
    "HTML",
    "CSS",
}

# Non-application / Data / Markup / Notebook formats excluded in the "Core Source Code" view
MARKUP_AND_DATA_FORMATS = {
    "HTML",
    "CSS",
    "SCSS",
    "Less",
    "Jupyter Notebook",
    "Rich Text Format",
    "XSLT",
    "MDX",
    "TeX",
    "PostScript",
    "Roff",
}


def resolve_safe_path(base_dir: Path, user_path: str) -> Path:
    """Resolves a path safely within base_dir to prevent path traversal."""
    base_resolved = base_dir.resolve()
    candidate = (base_resolved / Path(user_path).name).resolve()
    if not str(candidate).startswith(str(base_resolved) + "/"):
        raise ValueError(f"Path must reside within {base_resolved}")
    return candidate


def classify_tier(loc: float) -> str:
    """Classifies LOC into Small (<50k), Medium (50k-250k), or Large (>250k)."""
    if loc < 50_000:
        return "Small (<50k LOC)"
    if loc <= 250_000:
        return "Medium (50k–250k LOC)"
    return "Large (>250k LOC)"


def estimate_enterprise_repos(
    total_loc: float,
    full_scans_per_month: int = 1,
    diff_scans_per_month: int = 30,
) -> dict[str, Any]:
    """Estimates Small, Medium, and Large repo counts from aggregate LOC.

    Industry best guidance for enterprise codebases (Pareto distribution):
    - Small Repos (<50k LOC): ~20% of total LOC, avg repo size = 15,000 LOC
      (~68% of total repository count)
    - Medium Repos (50k-250k LOC): ~35% of total LOC, avg repo size = 100,000 LOC
      (~23% of total repository count)
    - Large Repos (>250k LOC): ~45% of total LOC, avg repo size = 500,000 LOC
      (~9% of total repository count)
    """
    small_loc = total_loc * 0.20
    medium_loc = total_loc * 0.35
    large_loc = total_loc * 0.45

    small_repos = math.ceil(small_loc / 15_000) if total_loc > 0 else 0
    medium_repos = math.ceil(medium_loc / 100_000) if total_loc > 0 else 0
    large_repos = math.ceil(large_loc / 500_000) if total_loc > 0 else 0

    combined_scans = full_scans_per_month + diff_scans_per_month

    return {
        "small": {
            "loc_share": round(small_loc),
            "avg_repo_loc": 15_000,
            "repos": small_repos,
            "full_scans_mo": small_repos * full_scans_per_month,
            "daily_diff_scans_mo": small_repos * diff_scans_per_month,
            "total_scans_mo": small_repos * combined_scans,
        },
        "medium": {
            "loc_share": round(medium_loc),
            "avg_repo_loc": 100_000,
            "repos": medium_repos,
            "full_scans_mo": medium_repos * full_scans_per_month,
            "daily_diff_scans_mo": medium_repos * diff_scans_per_month,
            "total_scans_mo": medium_repos * combined_scans,
        },
        "large": {
            "loc_share": round(large_loc),
            "avg_repo_loc": 500_000,
            "repos": large_repos,
            "full_scans_mo": large_repos * full_scans_per_month,
            "daily_diff_scans_mo": large_repos * diff_scans_per_month,
            "total_scans_mo": large_repos * combined_scans,
        },
        "total_repos": small_repos + medium_repos + large_repos,
    }


def load_language_records(
    raw_data: dict[str, Any], bytes_per_loc: int
) -> list[dict[str, Any]]:
    """Normalizes language byte data into structured sizing records.

    Supports both:
    1. Detailed format: {"Java": {"bytes": 100000, "percentage": 50.0}}
    2. GitHub API format: {"Java": 100000}
    """
    total_bytes = 0
    parsed_items: list[tuple[str, int, float | None]] = []

    for lang, info in raw_data.items():
        if isinstance(info, dict):
            b = int(info.get("bytes", 0))
            pct = float(info["percentage"]) if "percentage" in info else None
        elif isinstance(info, (int, float)):
            b = int(info)
            pct = None
        else:
            continue
        total_bytes += b
        parsed_items.append((lang, b, pct))

    records: list[dict[str, Any]] = []
    for lang, b, pct in parsed_items:
        computed_pct = (
            pct
            if pct is not None
            else (round((b / total_bytes) * 100, 2) if total_bytes > 0 else 0.0)
        )
        loc = round(b / bytes_per_loc)
        tier = classify_tier(loc)
        is_core = lang in CORE_SUPPORTED_LANGUAGES
        is_framework = lang in FRAMEWORK_WEB_LANGUAGES
        is_cm_all = is_core or is_framework
        is_markup_data = lang in MARKUP_AND_DATA_FORMATS

        records.append({
            "language": lang,
            "bytes": b,
            "percentage": computed_pct,
            "est_loc": loc,
            "tier": tier,
            "is_cm_core": is_core,
            "is_cm_framework": is_framework,
            "is_cm_supported": is_cm_all,
            "is_core_source_code": not is_markup_data,
        })

    records.sort(key=lambda r: r["bytes"], reverse=True)
    return records


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="CodeMender Fleet Sizing Calculator (LOC & Repository Drift Scans)"
    )
    parser.add_argument(
        "-i",
        "--input",
        default="sample_languages.json",
        help="Input JSON file filename in working directory (default: sample_languages.json)",
    )
    parser.add_argument(
        "-o",
        "--output-csv",
        default="sizing_breakdown.csv",
        help="Output CSV filename in working directory (default: sizing_breakdown.csv)",
    )
    parser.add_argument(
        "--bytes-per-loc",
        type=int,
        default=DEFAULT_BYTES_PER_LOC,
        help=f"Bytes per Line of Code conversion factor (default: {DEFAULT_BYTES_PER_LOC})",
    )
    parser.add_argument(
        "--full-scans",
        type=int,
        default=1,
        help="Full repository scans per month (default: 1)",
    )
    parser.add_argument(
        "--diff-scans",
        type=int,
        default=30,
        help="Daily diff scans per month (default: 30)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.bytes_per_loc <= 0:
        raise ValueError("--bytes-per-loc must be a positive integer.")

    base_dir = Path(__file__).resolve().parent
    data_path = resolve_safe_path(base_dir, args.input)
    csv_path = resolve_safe_path(base_dir, args.output_csv)

    with data_path.open("r", encoding="utf-8") as f:
        raw_data = json.load(f)

    records = load_language_records(raw_data, args.bytes_per_loc)

    total_bytes = sum(r["bytes"] for r in records)
    total_loc = sum(r["est_loc"] for r in records)

    cm_core_records = [r for r in records if r["is_cm_core"]]
    cm_full_records = [r for r in records if r["is_cm_supported"]]
    all_source_records = [r for r in records if r["is_core_source_code"]]

    cm_core_loc = sum(r["est_loc"] for r in cm_core_records)
    cm_full_loc = sum(r["est_loc"] for r in cm_full_records)
    all_source_loc = sum(r["est_loc"] for r in all_source_records)

    print(f"Input file: {data_path.name} ({len(records)} languages)")
    print(f"Conversion rate: {args.bytes_per_loc} bytes/LOC")
    print(
        f"Scan cadence: {args.full_scans} Full Scan(s)/mo + "
        f"{args.diff_scans} Diff Scan(s)/mo "
        f"({args.full_scans + args.diff_scans} total scans/mo)\n"
    )
    print(f"Total Unfiltered Fleet ({len(records)} langs): {total_bytes:,} bytes | {total_loc:,} LOC")
    print(
        f"All Core Source Code (excl. Markup/Data/Notebooks, {len(all_source_records)} langs): "
        f"{sum(r['bytes'] for r in all_source_records):,} bytes | {all_source_loc:,} LOC"
    )
    print(
        f"CodeMender Core Supported Languages ({len(cm_core_records)} langs): "
        f"{sum(r['bytes'] for r in cm_core_records):,} bytes | {cm_core_loc:,} LOC"
    )
    print(
        f"CodeMender Core + Web Frameworks ({len(cm_full_records)} langs): "
        f"{sum(r['bytes'] for r in cm_full_records):,} bytes | {cm_full_loc:,} LOC"
    )

    combined_scans = args.full_scans + args.diff_scans
    for label, loc_val in [
        ("Option A: CodeMender Core Application Languages (Excl. HTML/CSS)", cm_core_loc),
        ("Option B: CodeMender Core + Enterprise Web Frameworks (Incl. HTML/CSS)", cm_full_loc),
        ("Option C: All Core Source Code Languages (Non-markup languages)", all_source_loc),
        ("Option D: Entire Unfiltered Fleet (All entries)", total_loc),
    ]:
        est = estimate_enterprise_repos(loc_val, args.full_scans, args.diff_scans)
        print(f"\n=== {label} ({loc_val:,} LOC) ===")
        for sz in ["small", "medium", "large"]:
            s = est[sz]
            print(
                f"  {sz.upper():6s}: {s['repos']:4d} repos (LOC share: {s['loc_share']:11,d}) | "
                f"Full Scans/mo ({args.full_scans}x) = {s['full_scans_mo']:5,d} | "
                f"Diff Scans/mo ({args.diff_scans}x) = {s['daily_diff_scans_mo']:6,d} | "
                f"Total Scans/mo ({combined_scans}x) = {s['total_scans_mo']:6,d}"
            )
        print(f"  TOTAL REPOS: {est['total_repos']:,}")

    with csv_path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "Rank",
            "Language",
            "Bytes",
            "Percentage (%)",
            f"Estimated LOC (@{args.bytes_per_loc}B/LOC)",
            "Language Size Tier",
            "CodeMender Core Supported",
            "CodeMender Web/Framework Supported",
            "Core Source Code (Excl. Markup/Data)",
        ])
        for idx, r in enumerate(records, start=1):
            writer.writerow([
                idx,
                r["language"],
                r["bytes"],
                r["percentage"],
                r["est_loc"],
                r["tier"],
                "Yes" if r["is_cm_core"] else "No",
                "Yes" if r["is_cm_supported"] else "No",
                "Yes" if r["is_core_source_code"] else "No",
            ])

    print(f"\nExported CSV breakdown to {csv_path.name}")


if __name__ == "__main__":
    main()
