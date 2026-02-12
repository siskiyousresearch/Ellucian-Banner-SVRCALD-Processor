# SVRCALD Student Data Processor

A Python GUI tool for parsing **Detailed SVRCALD** reports (`.lis` or `.txt`) from the California Community Colleges MIS system and extracting student-level FTES data into CSV format.

## Features

- **Dual accounting mode** — choose between Non-Standardized and Standardized accounting before processing
- **Editable funding rates** — CDCP, Special Admit, Non-Credit, and Credit rates are pre-loaded with current defaults and can be adjusted in the GUI before each run
- **Accepts `.lis` and `.txt`** files from the Detailed SVRCALD report
- Outputs a timestamped **CSV** with student-level FTES, contact hours, and estimated funding
- Generates a **diagnostics log** for auditing/troubleshooting

## Accounting Modes

| Mode | Description |
|---|---|
| **Non-Standardized** | Preserves original accounting method codes (W, D, P, IW, ID, IN) with per-method FTES formulas |
| **Standardized** | Normalizes methods to S/P/IN, includes TLM multiplier field |

## Default Funding Rates

| Category | Non-Standardized | Standardized |
|---|---|---|
| CDCP | $7,424.53 | $7,345.93 |
| Special Admit | $7,424.53 | $7,345.93 |
| Non-Credit | $4,464.58 | $4,417.31 |
| Credit | $5,294.42 | $5,238.37 |

> Rates can be edited in the GUI before processing. Use **Reset to Defaults** to restore them.

## Requirements

- Python 3.10+
- No external dependencies — uses only the standard library (`tkinter`, `csv`, `re`, `datetime`)

## Installation

```bash
git clone https://github.com/<your-username>/svrcald-processor.git
cd svrcald-processor
```

## Usage

```bash
python student_data_processor.py
```

1. Select **Non-Standardized** or **Standardized** accounting mode
2. Adjust funding rates if needed (or leave defaults)
3. Click **Open Detailed SVRCALD File & Process**
4. Select your Detailed SVRCALD file (`.lis` or `.txt`)
5. Output CSV and diagnostics log are saved to the current working directory

## Output Fields

| Field | Description |
|---|---|
| Term | 6-digit term code (e.g. 202570) |
| Subject | Subject abbreviation (e.g. ADJ, ART) |
| Crse | Course number |
| CRN | Course Reference Number |
| Cmp | Campus code (e.g. WC) |
| Inst Mthd | Instruction method (Non-Standardized only) |
| Start Date | Section start date |
| Census Date | Census date |
| Census 2 Date | Second census date (if applicable) |
| End Date | Section end date |
| Student ID | Student ID (S + digits) |
| Student Type | Student type code |
| Reg Stat | Registration status |
| Special Admit | Special admit flag |
| Res Code | Residency code |
| Res Ind | Residency indicator (I/O) |
| Credit Ind | Credit indicator (Y/N) |
| PE Ind | PE indicator |
| CDCP Ind | CDCP indicator |
| Acct_Method | Accounting method label |
| TLM | Term length multiplier (Standardized only) |
| Resident Enrollment | Resident enrollment count |
| Resident Contact Hours | Resident contact hours |
| Non-Resident Enrollment | Non-resident enrollment count |
| Non-Resident Contact Hours | Non-resident contact hours |
| Resident FTES | Calculated resident FTES |
| Non-Resident FTES | Calculated non-resident FTES |
| Total FTES | Sum of resident + non-resident FTES |
| Total Res and Eligible Non-Res CH | Combined eligible contact hours |
| FTES_$ | Estimated funding dollars |
| SCFF_FTES | SCFF funding category label |

## License

MIT
