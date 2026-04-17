import streamlit as st
import pdfplumber
import re
from collections import defaultdict

st.set_page_config(page_title="PV QC Comparator", layout="wide")
st.title("Pharmacovigilance QC vs Agent Comparator")

# =========================
# PDF READER
# =========================
def read_pdf(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text.lower()

# =========================
# CLEAN VALUE
# =========================
def normalize(v):
    if not v:
        return ""
    v = v.lower().strip()
    v = re.sub(r"\s+", " ", v)
    return v

# =========================
# FIELD MAP (KEY FIX)
# =========================
FIELD_MAP = {
    "drug": ["product name", "entresto"],
    "dose": ["dose"],
    "frequency": ["frequency"],
    "indication": ["indication"],
    "mrd": ["date reported", "mrd"],
    "dob": ["date of birth", "birth"],
    "patient_id": ["patient id"],
    "gender": ["gender"],
    "age": ["age"],
    "country": ["country"],
    "ae": ["adverse event", "event description"]
}

# =========================
# VALUE EXTRACTOR
# =========================
def extract_field(text, keys):

    results = []

    lines = text.split("\n")

    for i, line in enumerate(lines):
        line_low = line.lower()

        for key in keys:
            if key in line_low:

                # take same line + next line (VERY IMPORTANT FIX)
                block = line_low

                if i + 1 < len(lines):
                    block += " " + lines[i + 1].lower()

                # extract values after ":" if exists
                if ":" in block:
                    value = block.split(":", 1)[1]
                else:
                    value = block

                value = normalize(value)

                if value and "click" not in value:
                    results.append(value)

    return list(set(results))

# =========================
# PARSER
# =========================
def parse(text):

    data = {}

    for field, keys in FIELD_MAP.items():
        data[field] = extract_field(text, keys)

    # fallback regex (critical fields)
    data["dose"] += re.findall(r"\d+\s*mg", text)
    data["patient_id"] += re.findall(r"\d{4}-\d{4}-\d{4}-\d{6}", text)
    data["dob"] += re.findall(r"\d{1,2}-[a-z]{3}-\d{2,4}", text)
    data["mrd"] += re.findall(r"\d{1,2}-[a-z]{3}-\d{2,4}", text)

    # cleanup
    for k in data:
        data[k] = list(set([normalize(x) for x in data[k] if x]))

    return data

# =========================
# SMART COMPARE
# =========================
def compare(qc, ag):

    mismatches = []

    all_keys = set(qc.keys()).union(set(ag.keys()))

    for k in all_keys:

        qc_vals = set(qc.get(k, []))
        ag_vals = set(ag.get(k, []))

        # remove noise
        qc_vals.discard("")
        ag_vals.discard("")

        if qc_vals != ag_vals:

            mismatches.append({
                "field": k.upper(),
                "qc": sorted(list(qc_vals)),
                "agent": sorted(list(ag_vals))
            })

    return mismatches

# =========================
# UI
# =========================
qc_file = st.file_uploader("Upload QC PDF", type=["pdf"])
ag_file = st.file_uploader("Upload Agent PDF", type=["pdf"])

if qc_file and ag_file:

    qc_text = read_pdf(qc_file)
    ag_text = read_pdf(ag_file)

    qc_data = parse(qc_text)
    ag_data = parse(ag_text)

    if st.button("Run Comparison"):

        results = compare(qc_data, ag_data)

        st.subheader("Mismatch Report")

        if not results:
            st.success("No discrepancies detected")
        else:
            for r in results:
                st.markdown(f"""
### {r['field']}

**QC:** {r['qc']}  
**Agent:** {r['agent']}

---
""")
