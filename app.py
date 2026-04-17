import streamlit as st
import pdfplumber
from docx import Document

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="PV QC System", layout="wide")

st.title("Pharmacovigilance Control System")
st.markdown("QC vs Agent comparison (Word + PDF structured PV validation)")

# =========================
# CLEAN TEXT
# =========================
def clean_text(text):
    if not text:
        return ""
    text = text.replace("\xa0", " ")
    text = text.replace("", "\n")
    text = text.replace("•", "\n")
    return text

# =========================
# PDF READER
# =========================
def read_pdf(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text

# =========================
# DOCX READER (FIXED)
# =========================
def read_docx(file):
    doc = Document(file)

    lines = []

    # paragraphs
    for p in doc.paragraphs:
        if p.text.strip():
            lines.append(p.text)

    # tables (IMPORTANT)
    for table in doc.tables:
        for row in table.rows:
            row_text = []
            for cell in row.cells:
                if cell.text.strip():
                    row_text.append(cell.text.strip())
            if row_text:
                lines.append(" | ".join(row_text))

    return "\n".join(lines)

# =========================
# FILE HANDLER
# =========================
def extract_text(file):
    if file.name.lower().endswith(".pdf"):
        return read_pdf(file)
    return read_docx(file)

# =========================
# FIELD EXTRACTION (ROBUST PV PARSER)
# =========================
def extract_fields(text):

    text = clean_text(text)

    lines = [l.strip() for l in text.split("\n") if l.strip()]

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

    def value(line):
        if ":" in line:
            return line.split(":", 1)[1].strip()
        return ""

    for line in lines:

        l = line.lower()

        if "product name" in l:
            fields["drug"] = value(line)

        elif "dose" in l:
            fields["dose"] = value(line)

        elif "indication" in l:
            fields["indication"] = value(line)

        elif "date reported" in l or "mrd" in l:
            fields["mrd"] = value(line)

        elif "patient id" in l:
            fields["patient_id"] = value(line)

        elif "date of birth" in l:
            fields["dob"] = value(line)

        elif "age" in l:
            fields["age"] = value(line)

        elif "gender" in l:
            fields["gender"] = value(line)

        elif "country" in l:
            fields["country"] = value(line)

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
# COMPARE ENGINE
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
qc_file = st.file_uploader("Upload QC File (PDF or DOCX)", type=["pdf", "docx"])
agent_file = st.file_uploader("Upload Agent File (PDF or DOCX)", type=["pdf", "docx"])

if qc_file and agent_file:

    qc_text = extract_text(qc_file)
    agent_text = extract_text(agent_file)

    qc_data = extract_fields(qc_text)
    agent_data = extract_fields(agent_text)

    st.subheader("Debug - QC Extracted Data")
    st.json(qc_data)

    st.subheader("Debug - Agent Extracted Data")
    st.json(agent_data)

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
