import streamlit as st
import pdfplumber
from docx import Document
import re

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(page_title="PV QC System", layout="wide")

st.title("Pharmacovigilance Quality Control System")
st.markdown("Pharma-grade QC vs Agent comparison (value-level detection)")

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
# NORMALIZE TEXT
# =========================
def normalize(text):
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.lower()).strip()

# =========================
# FIELD EXTRACTION (PHARMA LOGIC)
# =========================
def extract_fields(text):

    fields = {}

    patterns = {
        "drug": r"Product Name.*?:\s*(.*)",
        "dose": r"Dose:\s*(.*)",
        "indication": r"Indication:\s*(.*)",
        "mrd": r"Date Reported \(MRD\):\s*(.*)",
        "patient_id": r"Patient ID.*?:\s*(.*)",
        "dob": r"Date of Birth:\s*(.*)",
        "gender": r"Gender:\s*(.*)",
        "age": r"Age.*?:\s*(.*)",
        "country": r"Country Name\s*:\s*(.*)"
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            fields[key] = normalize(match.group(1))

    return fields

# =========================
# SEVERITY ENGINE
# =========================
def severity(field):

    if field in ["mrd", "dob", "patient_id"]:
        return "HIGH"

    if field in ["drug", "dose", "indication"]:
        return "MODERATE"

    return "LOW"

# =========================
# SMART COMPARISON ENGINE
# =========================
def compare(qc, agent):

    results = []

    all_keys = set(qc.keys()).union(set(agent.keys()))

    for key in all_keys:

        qc_val = qc.get(key, "MISSING")
        ag_val = agent.get(key, "MISSING")

        if qc_val != ag_val:

            results.append({
                "field": key.upper(),
                "qc": qc_val,
                "agent": ag_val,
                "severity": severity(key)
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

    qc_data = extract_fields(qc_text)
    agent_data = extract_fields(agent_text)

    if st.button("Run QC Validation"):

        results = compare(qc_data, agent_data)

        st.subheader("Mismatch Report")

        if not results:
            st.success("No discrepancies detected.")
        else:

            for r in results:

                st.markdown(f"""
### {r['field']}

QC Value: **{r['qc']}**  
Agent Value: **{r['agent']}**  
Severity: **{r['severity']}**

---
""")
