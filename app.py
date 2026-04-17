import streamlit as st
import pdfplumber
from docx import Document
import re

st.set_page_config(page_title="PV QC System", layout="wide")

st.title("Pharmacovigilance  Control System")
st.markdown("QC vs Agent comparison (pharma-grade mismatch detection)")

# -------------------------
# FILE READERS
# -------------------------
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


# -------------------------
# NORMALIZE
# -------------------------
def norm(x):
    return re.sub(r"\s+", " ", x.lower()).strip() if x else ""


# -------------------------
# FIELD EXTRACTION
# -------------------------
def extract_fields(text):

    patterns = {
        "drug": r"Product Name.*?:\s*(.*)",
        "dose": r"Dose:\s*(.*)",
        "indication": r"Indication:\s*(.*)",
        "mrd": r"Date Reported \(MRD\):\s*(.*)",
        "patient_id": r"Patient ID.*?:\s*(.*)",
        "dob": r"Date of Birth:\s*(.*)",
        "age": r"Age.*?:\s*(.*)",
        "gender": r"Gender:\s*(.*)",
        "country": r"Country Name\s*:\s*(.*)"
    }

    data = {}

    for k, p in patterns.items():
        m = re.search(p, text, re.IGNORECASE)
        if m:
            data[k] = norm(m.group(1))

    return data


# -------------------------
# SEVERITY
# -------------------------
def severity(field):

    if field in ["mrd", "dob", "patient_id"]:
        return "HIGH"

    if field in ["drug", "dose", "indication"]:
        return "MODERATE"

    return "LOW"


# -------------------------
# COMPARE ENGINE
# -------------------------
def compare(qc, agent):

    results = []

    keys = set(qc.keys()).union(agent.keys())

    for k in keys:

        qc_val = qc.get(k, "MISSING")
        ag_val = agent.get(k, "MISSING")

        if qc_val != ag_val:

            results.append({
                "field": k.upper(),
                "qc": qc_val,
                "agent": ag_val,
                "severity": severity(k)
            })

    return results


# -------------------------
# UI
# -------------------------
qc_file = st.file_uploader("Upload QC File", type=["pdf", "docx"])
agent_file = st.file_uploader("Upload Agent File", type=["pdf", "docx"])

if qc_file and agent_file:

    qc_text = extract_text(qc_file)
    agent_text = extract_text(agent_file)

    qc_data = extract_fields(qc_text)
    agent_data = extract_fields(agent_text)

    if st.button("Run QC Check"):

        results = compare(qc_data, agent_data)

        st.subheader("Mismatch Report")

        if not results:
            st.success("No discrepancies detected")
        else:
            for r in results:
                st.markdown(f"""
**{r['field']}**

QC: {r['qc']}  
Agent: {r['agent']}  
Severity: {r['severity']}

---
""")
