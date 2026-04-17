import streamlit as st
import pdfplumber
from docx import Document
import re

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="PV QC System", layout="wide")

st.title("Pharmacovigilance Quality Control System")
st.markdown("Pharma-grade validation: QC vs Agent (value-level comparison)")

# =========================
# FILE READING
# =========================
def read_pdf(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text


def read_docx(file):
    doc = Document(file)
    return "\n".join([p.text for p in doc.paragraphs])


def extract_text(file):
    if file.name.lower().endswith(".pdf"):
        return read_pdf(file)
    return read_docx(file)

# =========================
# FIELDS (PHARMA STRUCTURE)
# =========================
FIELDS = {
    "Drug": ["drug"],
    "Start Date": ["start date"],
    "End Date": ["end date"],
    "Indication": ["indication"],
    "Dose": ["dose"],
    "Frequency": ["frequency"],
    "Action Taken": ["action taken"],

    "Adverse Event": ["ae", "adverse event"],
    "Causality": ["causality"],
    "Outcome": ["outcome"],
    "Seriousness": ["seriousness"],
    "Description": ["description"],

    "MRD": ["mrd"],
    "DOB": ["dob", "date of birth"],
    "Patient ID": ["patient id"],
    "Gender": ["gender"],
    "Age": ["age"],
    "Weight": ["weight"],
    "Height": ["height"],

    "Country": ["country"],
    "Medical History": ["medical history"],
    "Allergies": ["allergies"],
    "Smoking": ["smoking"],

    "Patient Name": ["patient name"],
    "Patient Phone": ["phone"],
    "Doctor Name": ["doctor name"],
    "Doctor Phone": ["doctor phone"]
}

# =========================
# VALUE EXTRACTION
# =========================
def extract_value(line):
    if ":" in line:
        return line.split(":", 1)[1].strip()
    return line.strip()

# =========================
# PARSE FILE INTO STRUCTURE
# =========================
def parse(text):
    data = {}

    lines = [l.strip() for l in text.split("\n") if l.strip()]

    for line in lines:
        low = line.lower()

        for field, keys in FIELDS.items():
            if any(k in low for k in keys):
                value = extract_value(line)
                data.setdefault(field, []).append(value)

    return data

# =========================
# DIFFERENCE DETECTION
# =========================
def detect_difference(qc, ag):

    qc_l = qc.lower()
    ag_l = ag.lower()

    # numeric/date mismatch
    if re.search(r"\d", qc_l) and re.search(r"\d", ag_l):
        if qc_l != ag_l:
            return "Value mismatch (numeric/date)"

    return "Text mismatch"

# =========================
# SEVERITY RULES
# =========================
def severity(field):

    if field in ["MRD", "DOB", "Patient ID"]:
        return "High"

    if field in ["Adverse Event", "Drug", "Indication", "Dose", "Frequency"]:
        return "Moderate"

    return "Minor"

# =========================
# COMPARE FUNCTION
# =========================
def compare(qc, agent):

    results = []

    for field in FIELDS:

        qc_vals = qc.get(field, [])
        ag_vals = agent.get(field, [])

        max_len = max(len(qc_vals), len(ag_vals))

        for i in range(max_len):

            qc_val = qc_vals[i] if i < len(qc_vals) else "MISSING"
            ag_val = ag_vals[i] if i < len(ag_vals) else "MISSING"

            if qc_val.strip().lower() != ag_val.strip().lower():

                results.append({
                    "field": field,
                    "qc": qc_val,
                    "agent": ag_val,
                    "severity": severity(field),
                    "diff": detect_difference(qc_val, ag_val)
                })

    return results

# =========================
# UI
# =========================
st.subheader("Upload Files")

qc_file = st.file_uploader("Upload QC File", type=["pdf", "docx"])
agent_file = st.file_uploader("Upload Agent File", type=["pdf", "docx"])

if qc_file and agent_file:

    qc_text = extract_text(qc_file)
    agent_text = extract_text(agent_file)

    qc_data = parse(qc_text)
    agent_data = parse(agent_text)

    if st.button("Run QC Validation"):

        results = compare(qc_data, agent_data)

        st.subheader("Mismatch Report (QC vs Agent)")

        if not results:
            st.write("No discrepancies detected.")
        else:

            for r in results:

                st.markdown(f"""
### {r['field']}

| QC Value | Agent Value | Difference Type | Severity |
|----------|-------------|----------------|----------|
| {r['qc']} | {r['agent']} | {r['diff']} | {r['severity']} |

---
""")
