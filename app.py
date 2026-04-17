import streamlit as st
import pdfplumber
from docx import Document
import re

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(page_title="PV QC System", layout="wide")

st.title("Pharmacovigilance Control System")
st.markdown("QC vs Agent comparison (pharma-grade structured mismatch detection)")

# =========================
# FILE READERS
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
# CLEAN TEXT (IMPORTANT FIX)
# =========================
def clean_text(text):
    text = text.replace("\xa0", " ")
    text = text.replace("", "\n")
    text = text.replace("•", "\n")
    return text

# =========================
# FIELD EXTRACTION (ROBUST)
# =========================
def extract_fields(text):

    text = clean_text(text)

    fields = {
        "drug": "",
        "dose": "",
        "indication": "",
        "mrd": "",
        "patient_id": "",
        "dob": "",
        "age": "",
        "gender": "",
        "country": ""
    }

    lines = text.split("\n")

    def get_value(line):
        if ":" in line:
            return line.split(":", 1)[1].strip()
        return ""

    for line in lines:
        l = line.lower()

        if "product name" in l:
            fields["drug"] = get_value(line)

        elif "dose" in l:
            fields["dose"] = get_value(line)

        elif "indication" in l:
            fields["indication"] = get_value(line)

        elif "date reported" in l or "mrd" in l:
            fields["mrd"] = get_value(line)

        elif "patient id" in l:
            fields["patient_id"] = get_value(line)

        elif "date of birth" in l:
            fields["dob"] = get_value(line)

        elif "age" in l:
            fields["age"] = get_value(line)

        elif "gender" in l:
            fields["gender"] = get_value(line)

        elif "country" in l:
            fields["country"] = get_value(line)

    # normalize
    return {k: v.lower().strip() for k, v in fields.items() if v}

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
# COMPARISON ENGINE
# =========================
def compare(qc, agent):

    results = []

    keys = set(qc.keys()).union(set(agent.keys()))

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

# =========================
# UI
# =========================
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
            st.success("No discrepancies detected")
        else:
            for r in results:

                st.markdown(f"""
### {r['field']}

QC Value: **{r['qc']}**  
Agent Value: **{r['agent']}**  
Severity: **{r['severity']}**

---
""")
