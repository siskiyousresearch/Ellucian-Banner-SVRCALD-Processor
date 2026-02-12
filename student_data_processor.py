import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import re
import csv
from datetime import datetime
from collections import defaultdict


# ── Shared helpers ──────────────────────────────────────────────────────────

def preprocess_data(data):
    lines = data.splitlines()
    return lines


# ── Non-Standardized accounting helpers (Script 1) ─────────────────────────

ACCT_METHOD_MAP_NONSTD = {
    "W":  "WEEKLY, Part II",
    "D":  "DAILY, Part III",
    "P":  "ACTUAL, Part IV",
    "IW": "ISWEEK, Part V",
    "ID": "ISDAY, Part VI",
    "IN": "ISNC, Part VII",
}


def calculate_ftes_nonstd(acct_method, resident_hours, non_resident_hours, cr_ind):
    totalresANDeligbNCResContHrs = resident_hours

    if acct_method == "W":
        resident_ftes = (resident_hours * 16.5) / 525
        non_resident_ftes = (non_resident_hours * 16.5) / 525
    elif acct_method == "D":
        resident_ftes = resident_hours / 525
        non_resident_ftes = non_resident_hours / 525
    elif acct_method == "P":
        if cr_ind == "N" and non_resident_hours > 0:
            totalresANDeligbNCResContHrs += non_resident_hours
        resident_ftes = totalresANDeligbNCResContHrs / 525
        non_resident_ftes = non_resident_hours / 525
    elif acct_method == "IW":
        resident_ftes = (resident_hours * 17.5) / 525
        non_resident_ftes = (non_resident_hours * 17.5) / 525
    elif acct_method == "ID":
        resident_ftes = resident_hours / 525
        non_resident_ftes = non_resident_hours / 525
    elif acct_method == "IN":
        resident_hours *= 17.5
        non_resident_hours *= 17.5
        totalresANDeligbNCResContHrs = (resident_hours + non_resident_hours) / 2
        resident_ftes = totalresANDeligbNCResContHrs / 525
        non_resident_ftes = 0
    else:
        resident_ftes = 0
        non_resident_ftes = 0

    return resident_ftes, non_resident_ftes, resident_hours, non_resident_hours, totalresANDeligbNCResContHrs


# ── Standardized accounting helpers (Script 2) ─────────────────────────────

STANDARDIZED_CODES = {"S", "ID", "IW", "W", "D"}

ACCT_LABEL_STD = {
    "S":  "Standardized",
    "P":  "ACTUAL, Part IV",
    "IN": "ISNC, Part VII",
}


def normalize_acct_method(raw: str) -> str:
    c = (raw or "").strip().upper()
    if c in ("IN", "ISNC"):
        return "IN"
    if c in ("P", "ACTUAL"):
        return "P"
    if c in STANDARDIZED_CODES:
        return "S"
    return "UNKNOWN"


def calculate_ftes_std(acct_method, resident_hours, non_resident_hours, tlm_mult, cr_ind):
    totalresANDeligbNCResContHrs = resident_hours

    if acct_method == "S":
        resident_ftes = resident_hours / 525
        non_resident_ftes = non_resident_hours / 525
    elif acct_method == "P":
        if cr_ind == "N" and non_resident_hours > 0:
            totalresANDeligbNCResContHrs += non_resident_hours
        resident_ftes = totalresANDeligbNCResContHrs / 525
        non_resident_ftes = non_resident_hours / 525
    elif acct_method == "IN":
        resident_hours *= 17.5
        non_resident_hours *= 17.5
        totalresANDeligbNCResContHrs = (resident_hours + non_resident_hours) / 2
        resident_ftes = totalresANDeligbNCResContHrs / 525
        non_resident_ftes = 0
    else:
        resident_ftes = 0
        non_resident_ftes = 0

    return resident_ftes, non_resident_ftes, resident_hours, non_resident_hours, totalresANDeligbNCResContHrs


# ── Shared funding calculation ──────────────────────────────────────────────

def calculate_funding_and_label(resident_ftes, credit_ind, special_admit, cdcp_ind,
                                rates, student_type=None):
    """
    rates is a dict: {"cdcp": float, "special_admit": float, "non_credit": float, "credit": float}
    student_type is only used in Non-Standardized mode for the special_admit fallback.
    """
    # Fallback for missing special admit (Non-Standardized mode only)
    if student_type is not None:
        if not special_admit or special_admit.strip() == "":
            special_admit = "Y" if student_type == "Y" else "N"

    if cdcp_ind == "Y":
        ftes_dollars = resident_ftes * rates["cdcp"]
        label = "CDCP"
    elif special_admit == "Y":
        ftes_dollars = resident_ftes * rates["special_admit"]
        label = "Special Admit"
    elif credit_ind == "N" and special_admit == "N":
        ftes_dollars = resident_ftes * rates["non_credit"]
        label = "Non-Credit"
    elif credit_ind == "Y" and special_admit == "N":
        ftes_dollars = resident_ftes * rates["credit"]
        label = "Credit"
    else:
        ftes_dollars = 0
        label = "Unknown"

    return ftes_dollars, label


# ── File processing: Non-Standardized ──────────────────────────────────────

def process_file_nonstd(file_path, rates):
    try:
        with open(file_path, 'r') as file:
            data = file.read()
    except PermissionError as e:
        messagebox.showerror("Permission Error", f"Permission denied: {e}")
        return
    except Exception as e:
        messagebox.showerror("Error", f"Could not read file: {e}")
        return

    lines = preprocess_data(data)
    results = []
    diagnostics = []

    term = subject = crse = crn = ins_mthd = cr_ind = pe_ind = cdcp_ind = None
    acct_method = acct_method_label = cmp_code = None
    start_date = census_date = census2_date = end_date = ""

    for i, line in enumerate(lines):
        diagnostics.append(f"Processing line {i}: {line}")

        # Course header line — starts with 6-digit term code
        if len(line) >= 6 and re.match(r'^\d{6}', line[:6]):
            term = line[0:6].strip()
            subject = line[11:15].strip()
            crse = line[16:20].strip()
            crn = line[22:26].strip()
            cmp_code = line[32:34].strip()          # Cmp (e.g. WC)
            acct_method = line[36:38].strip()
            ins_mthd = line[40:43].strip()
            start_date = line[46:57].strip()         # Start Date
            census_date = line[58:69].strip()        # Census Date
            census2_date = line[70:81].strip()       # Census 2 Date
            end_date = line[82:93].strip()           # End Date
            cr_ind = line[124:125].strip()
            pe_ind = line[132:133].strip()
            cdcp_ind = line[136:137].strip()
            acct_method_label = ACCT_METHOD_MAP_NONSTD.get(acct_method, "Unknown")
            diagnostics.append(
                f"Detected term: {term}, Subject: {subject}, Crse: {crse}, CRN: {crn}, "
                f"Cmp: {cmp_code}, Start: {start_date}, Census: {census_date}, "
                f"Census2: {census2_date}, End: {end_date}"
            )
            continue

        # Student data line — "S" in column 9
        if len(line) > 9 and line[8:9] == 'S':
            sid_window = line[8:17].strip()
            if re.fullmatch(r'S\d{7,9}', sid_window) is None:
                diagnostics.append(f"Skipped non-student row at line {i}: sid_window='{sid_window}'")
                continue

            student_id = sid_window
            student_type = line[5:6].strip()
            reg_stat = line[52:55].strip()
            special_admit = line[75:78].strip()
            res_code = line[91:94].strip()
            res_ind = line[97:98].strip()
            res_enrl = float(line[100:108].strip().replace(',', '') or '0')
            res_hrs = float(line[110:122].strip().replace(',', '') or '0')
            non_res_enrl = float(line[121:132].strip().replace(',', '') or '0')
            non_res_hrs = float(line[132:143].strip().replace(',', '') or '0')

            resident_ftes, non_resident_ftes, res_hrs, non_res_hrs, totalresANDeligbNCResContHrs = calculate_ftes_nonstd(
                acct_method, res_hrs, non_res_hrs, cr_ind
            )
            total_ftes = resident_ftes + non_resident_ftes

            ftes_dollars, scff_label = calculate_funding_and_label(
                resident_ftes, cr_ind, special_admit, cdcp_ind, rates, student_type=student_type
            )

            results.append({
                "Term": term,
                "Subject": subject,
                "Crse": crse,
                "CRN": crn,
                "Cmp": cmp_code,
                "Inst Mthd": ins_mthd,
                "Start Date": start_date,
                "Census Date": census_date,
                "Census 2 Date": census2_date,
                "End Date": end_date,
                "Student ID": student_id,
                "Student Type": student_type,
                "Reg Stat": reg_stat,
                "Special Admit": special_admit,
                "Res Code": res_code,
                "Res Ind": res_ind,
                "Credit Ind": cr_ind,
                "PE Ind": pe_ind,
                "CDCP Ind": cdcp_ind,
                "Acct_Method": acct_method_label,
                "Resident Enrollment": res_enrl,
                "Resident Contact Hours": f"{res_hrs:.2f}",
                "Non-Resident Enrollment": non_res_enrl,
                "Non-Resident Contact Hours": f"{non_res_hrs:.2f}",
                "Resident FTES": f"{resident_ftes:.4f}",
                "Non-Resident FTES": f"{non_resident_ftes:.4f}",
                "Total FTES": f"{total_ftes:.4f}",
                "Total Resident and Eligible Non-Resident Contact Hours": f"{totalresANDeligbNCResContHrs:.2f}",
                "FTES_$": f"{ftes_dollars:.2f}",
                "SCFF_FTES": scff_label,
            })

            diagnostics.append(
                f"Captured student data: ID: {student_id}, Res Hours: {res_hrs}, Non-Res Hours: {non_res_hrs}, "
                f"Res FTES: {resident_ftes}, Non-Res FTES: {non_resident_ftes}, Total FTES: {total_ftes}, "
                f"TotalResANDEligbNCResContHrs: {totalresANDeligbNCResContHrs}, FTES_$: {ftes_dollars}, SCFF_FTES: {scff_label}"
            )

    fieldnames = [
        "Term", "Subject", "Crse", "CRN", "Cmp", "Inst Mthd",
        "Start Date", "Census Date", "Census 2 Date", "End Date",
        "Student ID", "Student Type",
        "Reg Stat", "Special Admit", "Res Code", "Res Ind", "Credit Ind",
        "PE Ind", "CDCP Ind", "Acct_Method", "Resident Enrollment",
        "Resident Contact Hours", "Non-Resident Enrollment",
        "Non-Resident Contact Hours", "Resident FTES", "Non-Resident FTES",
        "Total FTES", "Total Resident and Eligible Non-Resident Contact Hours",
        "FTES_$", "SCFF_FTES",
    ]
    _write_outputs(results, diagnostics, fieldnames, "nonstd")


# ── File processing: Standardized ──────────────────────────────────────────

def process_file_std(file_path, rates):
    try:
        with open(file_path, 'r') as file:
            data = file.read()
    except PermissionError as e:
        messagebox.showerror("Permission Error", f"Permission denied: {e}")
        return
    except Exception as e:
        messagebox.showerror("Error", f"Could not read file: {e}")
        return

    lines = preprocess_data(data)
    results = []
    diagnostics = []

    term = subject = crse = crn = cr_ind = pe_ind = cdcp_ind = None
    acct_method = acct_method_label = cmp_code = None
    start_date = census_date = census2_date = end_date = ""
    tlm_mult = 1.0

    for i, line in enumerate(lines):
        diagnostics.append(f"Processing line {i}: {line}")

        # Course header line — starts with 6-digit term code
        if len(line) >= 6 and re.match(r'^\d{6}', line[:6]):
            term = line[0:6].strip()
            subject = line[11:15].strip()
            crse = line[16:20].strip()
            crn = line[22:26].strip()
            cmp_code = line[32:34].strip()          # Cmp (e.g. WC)
            start_date = line[46:57].strip()         # Start Date
            census_date = line[58:69].strip()        # Census Date
            census2_date = line[70:81].strip()       # Census 2 Date
            end_date = line[82:93].strip()           # End Date
            cr_ind = line[124:125].strip()
            pe_ind = line[132:133].strip()
            cdcp_ind = line[136:137].strip()
            tlm_mult = line[95:100].strip()
            acct_method_raw = line[36:40]
            acct_method = normalize_acct_method(acct_method_raw)
            acct_method_label = ACCT_LABEL_STD.get(acct_method, "Unknown")
            diagnostics.append(
                f"Detected term: {term}, Subject: {subject}, Crse: {crse}, CRN: {crn}, "
                f"Cmp: {cmp_code}, Start: {start_date}, Census: {census_date}, "
                f"Census2: {census2_date}, End: {end_date}"
            )
            continue

        # Student data line — "S" in column 9
        if len(line) > 9 and line[8:9] == 'S':
            student_id = line[8:17].strip()
            student_type = line[5:6].strip()
            reg_stat = line[52:54].strip()
            special_admit = line[76:77].strip()
            res_code = line[92:93].strip()
            res_ind = line[97:98].strip()
            res_enrl = float(line[100:108].strip().replace(',', '') or '0')
            res_hrs = float(line[110:122].strip().replace(',', '') or '0')
            non_res_enrl = float(line[121:132].strip().replace(',', '') or '0')
            non_res_hrs = float(line[132:143].strip().replace(',', '') or '0')

            tlm_val = tlm_mult
            if isinstance(tlm_val, str):
                tlm_val = float(tlm_val) if tlm_val.replace('.', '', 1).isdigit() else 1.0

            resident_ftes, non_resident_ftes, res_hrs, non_res_hrs, totalresANDeligbNCResContHrs = calculate_ftes_std(
                acct_method, res_hrs, non_res_hrs, tlm_val, cr_ind
            )
            total_ftes = resident_ftes + non_resident_ftes

            ftes_dollars, scff_label = calculate_funding_and_label(
                resident_ftes, cr_ind, special_admit, cdcp_ind, rates
            )

            results.append({
                "Term": term,
                "Subject": subject,
                "Crse": crse,
                "CRN": crn,
                "Cmp": cmp_code,
                "Start Date": start_date,
                "Census Date": census_date,
                "Census 2 Date": census2_date,
                "End Date": end_date,
                "Student ID": student_id,
                "Student Type": student_type,
                "Reg Stat": reg_stat,
                "Special Admit": special_admit,
                "Res Code": res_code,
                "Res Ind": res_ind,
                "Credit Ind": cr_ind,
                "PE Ind": pe_ind,
                "CDCP Ind": cdcp_ind,
                "Acct_Method": acct_method_label,
                "TLM": tlm_val,
                "Resident Enrollment": res_enrl,
                "Resident Contact Hours": f"{res_hrs:.2f}",
                "Non-Resident Enrollment": non_res_enrl,
                "Non-Resident Contact Hours": f"{non_res_hrs:.2f}",
                "Resident FTES": f"{resident_ftes:.4f}",
                "Non-Resident FTES": f"{non_resident_ftes:.4f}",
                "Total FTES": f"{total_ftes:.4f}",
                "Total Resident and Eligible Non-Resident Contact Hours": f"{totalresANDeligbNCResContHrs:.2f}",
                "FTES_$": f"{ftes_dollars:.2f}",
                "SCFF_FTES": scff_label,
            })

            diagnostics.append(
                f"Captured student data: ID: {student_id}, Res Hours: {res_hrs}, Non-Res Hours: {non_res_hrs}, "
                f"Res FTES: {resident_ftes}, Non-Res FTES: {non_resident_ftes}, Total FTES: {total_ftes}, "
                f"TotalResANDEligbNCResContHrs: {totalresANDeligbNCResContHrs}, FTES_$: {ftes_dollars}, SCFF_FTES: {scff_label}"
            )

    fieldnames = [
        "Term", "Subject", "Crse", "CRN", "Cmp",
        "Start Date", "Census Date", "Census 2 Date", "End Date",
        "Student ID", "Student Type",
        "Reg Stat", "Special Admit", "Res Code", "Res Ind", "Credit Ind",
        "PE Ind", "CDCP Ind", "Acct_Method", "TLM", "Resident Enrollment",
        "Resident Contact Hours", "Non-Resident Enrollment",
        "Non-Resident Contact Hours", "Resident FTES", "Non-Resident FTES",
        "Total FTES", "Total Resident and Eligible Non-Resident Contact Hours",
        "FTES_$", "SCFF_FTES",
    ]
    _write_outputs(results, diagnostics, fieldnames, "std")


# ── Output writer ───────────────────────────────────────────────────────────

def _write_outputs(results, diagnostics, fieldnames, tag):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    diagnostic_file_path = f'diagnostics_{tag}_{timestamp}.txt'
    with open(diagnostic_file_path, 'w') as f:
        f.write('\n'.join(diagnostics))

    output_file_path = f'student_data_{tag}_{timestamp}.csv'
    try:
        with open(output_file_path, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in results:
                writer.writerow(row)
        messagebox.showinfo("Success",
                            f"Output saved to {output_file_path}\n"
                            f"Diagnostics saved to {diagnostic_file_path}")
    except Exception as e:
        messagebox.showerror("Error", f"Could not write to file: {e}")


# ═══════════════════════════════════════════════════════════════════════════
#  GUI
# ═══════════════════════════════════════════════════════════════════════════

DEFAULT_RATES = {
    "nonstd": {"cdcp": 7424.53, "special_admit": 7424.53, "non_credit": 4464.58, "credit": 5294.42},
    "std":    {"cdcp": 7345.93, "special_admit": 7345.93, "non_credit": 4417.31, "credit": 5238.37},
}


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Student Data Processor")
        self.geometry("520x380")
        self.resizable(False, False)

        # ── Mode selector ───────────────────────────────────────────────
        mode_frame = ttk.LabelFrame(self, text="Accounting Mode", padding=10)
        mode_frame.pack(fill="x", padx=15, pady=(15, 5))

        self.mode_var = tk.StringVar(value="nonstd")
        ttk.Radiobutton(mode_frame, text="Non-Standardized Accounting",
                        variable=self.mode_var, value="nonstd",
                        command=self._on_mode_change).pack(anchor="w")
        ttk.Radiobutton(mode_frame, text="Standardized Accounting",
                        variable=self.mode_var, value="std",
                        command=self._on_mode_change).pack(anchor="w")

        # ── Funding rates ───────────────────────────────────────────────
        rates_frame = ttk.LabelFrame(self, text="Funding Rates ($/FTES)", padding=10)
        rates_frame.pack(fill="x", padx=15, pady=10)

        labels = ["CDCP", "Special Admit", "Non-Credit", "Credit"]
        keys   = ["cdcp", "special_admit", "non_credit", "credit"]
        self.rate_entries = {}

        for row_idx, (lbl, key) in enumerate(zip(labels, keys)):
            ttk.Label(rates_frame, text=f"{lbl}:").grid(row=row_idx, column=0, sticky="w", padx=(0, 10), pady=3)
            var = tk.StringVar()
            entry = ttk.Entry(rates_frame, textvariable=var, width=14)
            entry.grid(row=row_idx, column=1, sticky="w", pady=3)
            self.rate_entries[key] = var

        # Initialize with default Non-Standardized rates
        self._load_defaults()

        # ── Buttons ─────────────────────────────────────────────────────
        btn_frame = ttk.Frame(self, padding=10)
        btn_frame.pack(fill="x", padx=15)

        ttk.Button(btn_frame, text="Reset to Defaults",
                   command=self._load_defaults).pack(side="left", padx=(0, 10))
        ttk.Button(btn_frame, text="Open Detailed SVRCALD File & Process",
                   command=self._open_and_process).pack(side="right")

    # ── Internal helpers ────────────────────────────────────────────────

    def _on_mode_change(self):
        """When the user switches mode, reload the default rates for that mode."""
        self._load_defaults()

    def _load_defaults(self):
        mode = self.mode_var.get()
        defaults = DEFAULT_RATES[mode]
        for key, var in self.rate_entries.items():
            var.set(f"{defaults[key]:.2f}")

    def _read_rates(self) -> dict | None:
        """Validate and return the current rate entries as a dict of floats."""
        rates = {}
        for key, var in self.rate_entries.items():
            try:
                rates[key] = float(var.get())
            except ValueError:
                messagebox.showerror("Invalid Rate",
                                     f"'{var.get()}' is not a valid number for {key.replace('_', ' ').title()}.")
                return None
        return rates

    def _open_and_process(self):
        rates = self._read_rates()
        if rates is None:
            return

        file_path = filedialog.askopenfilename(
            title="Select Detailed SVRCALD File (.lis or .txt)",
            filetypes=(
                ("SVRCALD files", "*.lis *.txt"),
                ("LIS files", "*.lis"),
                ("Text files", "*.txt"),
                ("All files", "*.*"),
            ),
        )
        if not file_path:
            return

        mode = self.mode_var.get()
        if mode == "std":
            process_file_std(file_path, rates)
        else:
            process_file_nonstd(file_path, rates)


if __name__ == "__main__":
    App().mainloop()
