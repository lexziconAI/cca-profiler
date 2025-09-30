# AI Coding Agent Instructions for CCIP (copilot-instructions.md)

Authoritative, copy-pasteable guidance for working on the **CCIP** project in this workspace. This reflects the current, working design and **must** be kept in sync with the code.

---

## Overview

**CCIP (Cross-Cultural Intelligence Profile)** ingests survey data (CSV/XLSX), computes per-dimension scores with reverse items, renders a radar chart and icons via **CairoSVG**, and composes a single Excel worksheet using **XlsxWriter**. Processing is **deterministic** and produces a **three-sentence Summary** per participant in British English.

---

## Run the project (CLI)

From the project root:

```powershell
# Windows / VS Code terminal (venv active)
python -m ccip --input "C:\path\to\input.xlsx" --output "C:\path\to\CCIP_Results.xlsx"
Input: .csv or .xlsx (close the file in Excel before running).

Output: one Excel workbook with all required columns, embedded icons, and radar image.

Input detection and scoring rules
Date column

If a Date column exists, use it as-is.

Otherwise derive from Start time / Start Time (Excel serials and common strings supported, dayfirst=True), else file modified time, else today.

All dates are formatted dd/mm/yyyy.

Question columns (Q1–Q25)

Preferred layout: Q1 starts at column I.

Robust fallback: find the anchor header containing the phrase “prefer to be clear and direct”, then treat the next 25 columns as Q1–Q25.

Likert parsing handles canonical labels (e.g., Strongly Agree … Strongly Disagree) and numerics.

Reverse scoring: Q2 and Q11.

Dimensions (means of 5 items each)
DT, TR, CO, CA, EP → written out as:
Directness & Transparency (DT), Task vs Relational Accountability (TR), Conflict Orientation (CO), Cultural Adaptability (CA), Empathy & Perspective-Taking (EP).

Bands (get_band)
≥4.5 Very High; ≥3.5 High; ≥2.5 Moderate / Balanced; ≥1.5 Developing; else Low / Limited.

Selection logic (deterministic)

KS (Key Strengths): choose only {High, Very High}; sort by score DESC then DIM_ORDER; pad with placeholders to 3.

DA (Development Areas): choose only {Developing, Low / Limited}; sort by score ASC then DIM_ORDER; pad with placeholders to 3.

PR (Priority Recommendations): start with DA dims, then lowest remaining by score and DIM_ORDER, de-dup to exactly 3.

KS/DA titles: "Label - X.X" (one-decimal HALF-UP).

Bodies for KS/DA/PR are exactly three lines (split by sentence/semicolon; joined with \n).

Summary: exactly three sentences, deterministic phrasing.

Strict rendering & Excel constraints
Allowed icons only (callable SVG factories):
LEVEL_TOOLS, LEVEL_SHIELD, LEVEL_SEEDLING, PR_DT, PR_TR, PR_CO, PR_CA, PR_EP.
Forbidden: crosses/ticks/checkmarks/“status indicator” symbols (do not create/reference them).

SVG → PNG: CairoSVG only, via the canonical helper; exactly one automatic retry; on repeated failure log ERROR and leave the cell empty.
PNGs must be 600×600, RGBA, 144 DPI; embed with equal x/y scale and object_position=2.

Excel writer: pd.ExcelWriter(..., engine="xlsxwriter").

British spelling throughout.

Required columns (exact order)
pgsql
Copy code
Date, ID, Name, Email,
DT_Score, TR_Score, CO_Score, CA_Score, EP_Score,
KS1_Icon, KS1_Title, KS1_Body,
KS2_Icon, KS2_Title, KS2_Body,
KS3_Icon, KS3_Title, KS3_Body,
DA1_Icon, DA1_Title, DA1_Body,
DA2_Icon, DA2_Title, DA2_Body,
DA3_Icon, DA3_Title, DA3_Body,
PR1_Icon, PR1_Title, PR1_Body,
PR2_Icon, PR2_Title, PR2_Body,
PR3_Icon, PR3_Title, PR3_Body,
RQ1, RQ2, RQ3, RQ4,
Summary, Radar_PNG
Code must validate the column indices against this schema and raise on mismatch.

Development environment
Python & dependencies (venv)
powershell
Copy code
# create / activate (Windows)
python -m venv venv
.\venv\Scripts\Activate.ps1

# deps
pip install -U pip
pip install pandas numpy Pillow XlsxWriter cairosvg cairocffi openpyxl pytest
Cairo on Windows (required for PNG rendering)
Install the GTK runtime (ships libcairo-2.dll) in an Administrator PowerShell:

powershell
Copy code
choco install gtk-runtime -y
In the VS Code terminal before running, prepend the GTK bin to PATH:

powershell
Copy code
$env:Path = "C:\Program Files\GTK3-Runtime Win64\bin;$env:Path"
python -c "import cairosvg, cairocffi; print('Cairo OK')"
If the folder name differs, locate libcairo-2.dll under C:\Program Files\ and add its bin folder to PATH for the session.

VS Code tips
Select interpreter: …\CCIP\venv\Scripts\python.exe
(Ctrl+Shift+P → Python: Select Interpreter)

Optional workspace pin (create .vscode/settings.json):

json
Copy code
{
  "python.defaultInterpreterPath": "${workspaceFolder}\\venv\\Scripts\\python.exe",
  "terminal.integrated.env.windows": {
    "PATH": "C:\\Program Files\\GTK3-Runtime Win64\\bin;${env:PATH}"
  }
}
One-click debug (.vscode/launch.json):

json
Copy code
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Run CCIP",
      "type": "python",
      "request": "launch",
      "module": "ccip",
      "justMyCode": true,
      "args": [
        "--input", "C:\\Users\\regan\\Downloads\\Cultural & Communication Intelligence Profiler Dummy Raw Inputs.xlsx",
        "--output","C:\\Users\\regan\\Downloads\\CCIP_Results.xlsx"
      ]
    }
  ]
}
Tests & quality gates
Smoke tests:

powershell
Copy code
pytest -q
They cover CSV→Excel flow, CairoSVG conversion, forbidden glyph linter, and icon factory callability.

Manual spot-checks (open the output workbook):

Only Level_* and PR_* icons appear; no ticks/crosses.

KS/DA/PR bodies are exactly three lines.

Summary is exactly three sentences.

Date format dd/mm/yyyy.

Troubleshooting
OSError: no library called "cairo" → GTK runtime not installed or not on PATH. See “Cairo on Windows”.

PermissionError: [Errno 13] Permission denied → Close the input/output workbook in Excel.

Icons/radar missing → CairoSVG conversion failed twice; check logs. Ensure PNG size/DPI/alpha handling code is in place.

Schema error → Column order did not match Required columns; update the composer or input file headers accordingly.

Don’ts (to keep determinism)
Don’t add new icons or any “status” glyphs (ticks/checkmarks/crosses).

Don’t introduce randomness without a fixed seed.

Don’t change KS/DA/PR text sources outside ccip_textbank.py.

Don’t mutate input DataFrame in place; operate on a copy.

Quick reference (copy/paste)
powershell
Copy code
# Activate (Windows)
.\venv\Scripts\Activate.ps1
# Ensure Cairo can load
$env:Path = "C:\Program Files\GTK3-Runtime Win64\bin;$env:Path"
python -c "import cairosvg, cairocffi; print('Cairo OK')"
# Run
python -m ccip --input "C:\path\to\input.xlsx" --output "C:\path\to\CCIP_Results.xlsx"
This document is the single source of truth for CCIP developer operations in this workspace. If behaviour changes, update this file in the same pull request as the code.

makefile
Copy code
::contentReference[oaicite:0]{index=0}