import streamlit as st
import pdfplumber
from docx import Document
import re

# =========================
# APP CONFIG
# =========================
st.set_page_config(page_title="PV QC System", layout="wide")

st.title("Pharmacovigilance Control System")
st.markdown("QC vs Agent comparison (Word + PDF pharma-grade validation)")

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
# WORD READER (FIXED - IMPORTANT)
# =========================
def read_docx(file):
    doc = Document(file)

    text_parts = []

    # paragraphs
    for p in doc.paragraphs:
        if p.text.strip():
            text_parts.append(p.text)

    # tables (VERY IMPORTANT FOR PV FORMS)
    for table in doc.tables:
        for row in table.rows:
            row_data = []
            for cell in row.cells:
                if cell.text.strip():
                    row_data.append(cell.text.strip())
            if row_data:
                text_parts.append(" | ".join(row_data))

    return "\n".join(text_parts)

# =========================
# UNIVERSAL FILE HANDLER
# =========================
def extract_text(file):
    if file.name.lower().endswith(".pdf"):
        return read_pdf(file)
    return read_docx(file)

# =========================
# FIELD EXTRACTION (PHARMA STRUCTURE)
# =========================
def extract_fields(text):

    text = clean_text(text)

    def find(pattern):
        m = re.search(pattern, text, re.IGNORECASE)
        return m.group(1).strip() if m else ""

    fields = {
        "drug": find(r"Product Name.*?:\s*(.+)"),
        "dose": find(r"Dose\s*:\s*(.+)"),
        "indication": find(r"Indication\s*:\s*(.+)"),
        "mrd": find(r"Date Reported.*?:\s*(.+)"),
        "patient_id": find(r"Patient ID.*?:\s*(.+)"),
        "dob": find(r"Date of Birth\s*:\s*(.+)"),
        "age": find(r"Age.*?:\s*(.+)"),
        "gender": find(r"Gender\s*:\s*(.+)"),
        "country": find(r"Country.*?:\s*(.+)")
    }

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

    # DEBUG (REMOVE LATER IF NOT NEEDED)
    with st.expander("QC Extracted Data"):
        st.write(qc_data)

    with st.expander("Agent Extracted Data"):
        st.write(agent_data)

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
