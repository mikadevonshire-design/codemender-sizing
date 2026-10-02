# CodeMender Fleet Sizing Calculator

A standalone Python CLI utility that estimates **Lines of Code (LOC)**, **Small / Medium / Large repository distributions**, and **monthly Fleet Drift Scan volumes** from GitHub/GitLab Linguist language byte breakdowns.

---

## Supported Languages & Frameworks

- **Languages:** `C` / `C++`, `Java`, `Python`, `TypeScript` / `JavaScript`, `Go`, `Rust`, and `Ruby`
- **Frameworks:** Broad support for standard libraries within these languages, as well as common enterprise frameworks (`HTML` / `CSS`, Django, Flask, React, Spring Boot, and Express)

---

## Features

- **Bytes-to-LOC Conversion:** Converts raw byte counts per programming language into estimated Lines of Code (defaults to industry-standard `40 bytes/LOC`, configurable via `--bytes-per-loc`).
- **Multi-Tier Language Filtering:**
  1. **CodeMender Core Application Languages:** `C`, `C++`, `Java`, `Python`, `TypeScript`, `JavaScript`, `Go`, `Rust`, `Ruby`.
  2. **CodeMender Core + Supported Web/Enterprise Frameworks:** Adds `HTML` and `CSS` (alongside framework code in Django, Flask, React, Spring Boot, and Express).
  3. **All Core Source Code:** Excludes non-application markup, documents, and notebooks (`HTML`, `CSS`, `Rich Text Format`, `Jupyter Notebook`, `XSLT`, etc.).
  4. **Unfiltered Fleet:** Includes all entries in the input JSON.
- **Language Volume Tiering:** Classifies each language bucket into:
  - **Small:** `<50k LOC`
  - **Medium:** `50k–250k LOC`
  - **Large:** `>250k LOC`
- **Enterprise Repository Distribution (Pareto Model):**
  Estimates the number of Small, Medium, and Large repositories from aggregate LOC using industry-standard enterprise distributions:
  - **Small Repos (`<50k LOC`):** `20%` of total LOC ÷ `15,000 LOC` average repo size (~68% of repository count)
  - **Medium Repos (`50k–250k LOC`):** `35%` of total LOC ÷ `100,000 LOC` average repo size (~23% of repository count)
  - **Large Repos (`>250k LOC`):** `45%` of total LOC ÷ `500,000 LOC` average repo size (~9% of repository count)
- **Fleet Scans (Repository Drift) Calculation:**
  Computes monthly scan volumes for:
  - **Full Scans / Month** (default: `1` per repo/month)
  - **Daily Diff Scans / Month** (default: `30` per repo/month)
  - **Combined Monthly Scans** (default: `31` scan events per repo/month)
- **Spreadsheet Export:** Generates a ready-to-import CSV (`sizing_breakdown.csv`) ranked by byte count and LOC.

---

## Requirements

- **Python 3.10+** (uses Python standard library only; no external dependencies required).

---

## Input JSON Formats

`calculate_sizing.py` accepts two JSON formats:

### 1. Detailed Linguist Breakdown (`bytes` and `percentage`)
```json
{
  "Java": {
    "bytes": 240000000,
    "percentage": 24.0
  },
  "TypeScript": {
    "bytes": 180000000,
    "percentage": 18.0
  }
}
```

### 2. Standard GitHub REST API (`/repos/{owner}/{repo}/languages`)
```json
{
  "Java": 240000000,
  "TypeScript": 180000000
}
```

---

## Usage

Run with the included synthetic `sample_languages.json`:

```bash
python3 calculate_sizing.py
```

Run with a custom language breakdown JSON file and custom scan cadence:

```bash
python3 calculate_sizing.py \
  --input my_org_languages.json \
  --output-csv my_org_sizing.csv \
  --bytes-per-loc 40 \
  --full-scans 1 \
  --diff-scans 30
```

### CLI Options

| Flag | Default | Description |
| :--- | :--- | :--- |
| `-i`, `--input` | `sample_languages.json` | Input JSON filename inside the working directory |
| `-o`, `--output-csv` | `sizing_breakdown.csv` | Output CSV filename inside the working directory |
| `--bytes-per-loc` | `40` | Bytes per Line of Code conversion factor |
| `--full-scans` | `1` | Full repository scans per month |
| `--diff-scans` | `30` | Incremental/daily diff scans per month |

---

## Sample Output

```text
Input file: sample_languages.json (14 languages)
Conversion rate: 40 bytes/LOC
Scan cadence: 1 Full Scan(s)/mo + 30 Diff Scan(s)/mo (31 total scans/mo)

Total Unfiltered Fleet (14 langs): 1,000,000,000 bytes | 25,000,000 LOC
All Core Source Code (excl. Markup/Data/Notebooks, 12 langs): 870,000,000 bytes | 21,750,000 LOC
CodeMender Core Supported Languages (8 langs): 802,000,000 bytes | 20,050,000 LOC
CodeMender Core + Web Frameworks (10 langs): 932,000,000 bytes | 23,300,000 LOC

=== Option A: CodeMender Core Application Languages (Excl. HTML/CSS) (20,050,000 LOC) ===
  SMALL :  268 repos (LOC share:   4,010,000) | Full Scans/mo (1x) =   268 | Diff Scans/mo (30x) =  8,040 | Total Scans/mo (31x) =  8,308
  MEDIUM:   71 repos (LOC share:   7,017,500) | Full Scans/mo (1x) =    71 | Diff Scans/mo (30x) =  2,130 | Total Scans/mo (31x) =  2,201
  LARGE :   19 repos (LOC share:   9,022,500) | Full Scans/mo (1x) =    19 | Diff Scans/mo (30x) =    570 | Total Scans/mo (31x) =    589
  TOTAL REPOS: 358
```
