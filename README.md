# CodeMender Fleet Sizing Calculator

A standalone Python CLI utility that estimates **Lines of Code (LOC)**, **Small / Medium / Large repository distributions**, and **monthly Fleet Drift Scan volumes** from GitHub/GitLab Linguist language byte breakdowns.

---

## Features

- **Bytes-to-LOC Conversion:** Converts raw byte counts per programming language into estimated Lines of Code (defaults to industry-standard `40 bytes/LOC`, configurable via `--bytes-per-loc`).
- **Multi-Tier Language Filtering:**
  1. **CodeMender Core Application Languages:** `C`, `C++`, `C#`, `Visual Basic .NET`, `F#`, `Go`, `Java`, `JavaScript`, `TypeScript`, `Kotlin`, `Vue`, `Python`, `Cython`, `Ruby`, `Rust`, `PHP`.
  2. **CodeMender Core + Supported Web/Enterprise Frameworks:** Adds `HTML`, `CSS`, `SCSS`, `Less`, `ASP.NET`, and common template engines (`Jinja`, `FreeMarker`, `Handlebars`, `EJS`, `Pug`, `Smarty`, `Haml`).
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
CodeMender Core Supported Languages (11 langs): 869,500,000 bytes | 21,737,500 LOC
CodeMender Core + Web Frameworks (13 langs): 999,500,000 bytes | 24,987,500 LOC

=== Option A: CodeMender Core Application Languages (Excl. HTML/CSS) (21,737,500 LOC) ===
  SMALL :  290 repos (LOC share:   4,347,500) | Full Scans/mo (1x) =   290 | Diff Scans/mo (30x) =  8,700 | Total Scans/mo (31x) =  8,990
  MEDIUM:   77 repos (LOC share:   7,608,125) | Full Scans/mo (1x) =    77 | Diff Scans/mo (30x) =  2,310 | Total Scans/mo (31x) =  2,387
  LARGE :   20 repos (LOC share:   9,781,875) | Full Scans/mo (1x) =    20 | Diff Scans/mo (30x) =    600 | Total Scans/mo (31x) =    620
  TOTAL REPOS: 387
```
