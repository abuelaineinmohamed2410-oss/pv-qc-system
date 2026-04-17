import streamlit as st
import pdfplumber
from docx import Document
import re

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="PV QC System", layout="wide")

st.title("Pharmacovigilance Control System")
st.markdown("QC vs Agent comparison (structured pharma-grade validation)")

# =========================
# CLEAN TEXT
# =========================
def clean_text(text):
    text = text.replace("\xa0", " ")
    text = text.replace("", "\n")
    text = text.replace("•", "\n")
    return text

# =========================
# READ PDF
# =========================
def read_pdf(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text

# =========================
# READ DOCX (FIXED - IMPORTANT)
# =========================
def read_docx(file):
    doc = Document(file)

    text = []

    # paragraphs
    for p in doc.paragraphs:
        text.append(p.text)

    # tables (CRITICAL FIX)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text.append(cell.text)

    return "\n".join(text)

# =========================
# EXTRACT TEXT
# =========================
def extract_text(file):
    if file.name.lower().endswith(".pdf"):
        return read_pdf(file)
    return read_docx(file)

# =========================
# FIELD EXTRACTION (ROBUST)
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

    # normalize
    return {k: v.lower().strip() for k, v in fields.items() if v}

# =========================
# SEVERITY
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
qc_file = st.file_uploader("Upload QC File", type=["pdf", "docx"])
agent_file = st.file_uploader("Upload Agent File", type=["pdf", "docx"])

if qc_file and agent_file:

    qc_text = extract_text(qc_file)
    agent_text = extract_text(agent_file)

    qc_data = extract_fields(qc_text)
    agent_data = extract_fields(agent_text)

    # DEBUG (REMOVE LATER IF YOU WANT)
    with st.expander("Debug - QC Extracted Data"):
        st.write(qc_data)

    with st.expander("Debug - Agent Extracted Data"):
        st.write(agent_data)

    if st.button("Run QC Validation"):

        results = compare(qc_data, agent_data)

        st.subheader("Mismatch Report")

        if not results:
            st.error("No discrepancies detected (check extracted data)")
        else:

            for r in results:

                st.markdown(f"""
### {r['field']}

QC Value: **{r['qc']}**  
Agent Value: **{r['agent']}**  
Severity: **{r['severity']}**

---
""")
