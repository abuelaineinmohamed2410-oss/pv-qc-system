import streamlit as st
import pdfplumber
import re
from collections import defaultdict

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="PV QC System",
    layout="wide"
)

st.title("Pharmacovigilance QC System")
st.caption("Structured QC vs Agent discrepancy detection engine")

# =========================
# PDF READER
# =========================
def read_pdf(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"
    return text

# =========================
# CLEAN TEXT
# =========================
def clean(text):
    text = text.lower()
    text = text.replace("", "\n").replace("•", "\n")
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text

# =========================
# NOISE FILTER
# =========================
def is_noise(x):
    bad = [
        "click or tap",
        "choose an item",
        "enter text",
        "additional information",
        "product information"
    ]
    return any(b in x for b in bad)

# =========================
# FIELD MAP (PHARMA-GRADE)
# =========================
FIELDS = {
    "drug": ["product name", "entresto", "drug"],
    "dose": ["dose", "mg"],
    "frequency": ["frequency", "daily", "twice", "once"],
    "indication": ["indication", "hf"],
    "mrd": ["date reported", "mrd"],
    "dob": ["date of birth"],
    "age": ["age"],
    "gender": ["gender"],
    "patient_id": ["patient id"],
    "country": ["country"],
}

# =========================
# SMART VALUE NORMALIZER
# =========================
def normalize(v):
    v = v.lower().strip()
    v = v.replace("milligram", "mg")
    v = re.sub(r"\s+", " ", v)
    v = v.replace("(", "").replace(")", "")
    return v

# =========================
# FIELD EXTRACTION (ROBUST)
# =========================
def extract_fields(text):

    text = clean(text)
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    data = defaultdict(list)

    for i, line in enumerate(lines):

        if is_noise(line):
            continue

        for field, keys in FIELDS.items():

            if any(k in line for k in keys):

                value = None

                # Case 1: inline value after :
                if ":" in line:
                    value = line.split(":", 1)[1].strip()

                # Case 2: next meaningful line
                else:
                    for j in range(i+1, min(i+5, len(lines))):
                        if not is_noise(lines[j]):
                            value = lines[j]
                            break

                if value:
                    value = normalize(value)

                    # avoid garbage duplicates
                    if value and value not in data[field]:
                        data[field].append(value)

    return dict(data)

# =========================
# SMART COMPARISON ENGINE
# =========================
def compare(qc, agent):

    report = defaultdict(list)
    all_keys = set(qc.keys()).union(agent.keys())

    for key in all_keys:

        qc_vals = qc.get(key, [])
        ag_vals = agent.get(key, [])

        qc_vals = qc_vals if isinstance(qc_vals, list) else [qc_vals]
        ag_vals = ag_vals if isinstance(ag_vals, list) else [ag_vals]

        qc_set = set(qc_vals)
        ag_set = set(ag_vals)

        missing_in_agent = qc_set - ag_set
        missing_in_qc = ag_set - qc_set

        if missing_in_agent or missing_in_qc:

            report[key.upper()].append({
                "qc": list(qc_set),
                "agent": list(ag_set),
                "missing_in_agent": list(missing_in_agent),
                "missing_in_qc": list(missing_in_qc)
            })

    return report

# =========================
# UI
# =========================
col1, col2 = st.columns(2)

qc_file = col1.file_uploader("Upload QC PDF", type=["pdf"])
agent_file = col2.file_uploader("Upload Agent PDF", type=["pdf"])

# =========================
# RUN
# =========================
if qc_file and agent_file:

    qc_text = read_pdf(qc_file)
    agent_text = read_pdf(agent_file)

    qc_data = extract_fields(qc_text)
    agent_data = extract_fields(agent_text)

    if st.button("Run QC Validation"):

        results = compare(qc_data, agent_data)

        st.subheader("STRUCTURED MISMATCH REPORT")

        if not results:
            st.success("No discrepancies detected")
        else:

            for field, items in results.items():

                for r in items:

                    st.markdown(f"""
## {field}

**QC Values**
{r['qc']}

**Agent Values**
{r['agent']}

**Missing in Agent**
{r['missing_in_agent']}

**Missing in QC**
{r['missing_in_qc']}

---
""")
