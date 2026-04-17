import streamlit as st
import pdfplumber
from docx import Document

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="PV QC System", layout="wide")

st.title("Pharmacovigilance Control System")
st.markdown("QC vs Agent - robust pharma-grade comparison")

# =========================
# CLEAN TEXT
# =========================
def clean(text):
    if not text:
        return ""
    text = text.replace("\xa0", " ")
    text = text.replace("", "\n")
    text = text.replace("•", "\n")
    return text

# =========================
# PDF (IMPROVED)
# =========================
def read_pdf(file):
    text = []
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text.append(t)
    return "\n".join(text)

# =========================
# DOCX (STABLE METHOD)
# =========================
def read_docx(file):
    doc = Document(file)

    text = []

    # paragraphs
    for p in doc.paragraphs:
        if p.text.strip():
            text.append(p.text.strip())

    # tables
    for table in doc.tables:
        for row in table.rows:
            row_text = []
            for cell in row.cells:
                if cell.text.strip():
                    row_text.append(cell.text.strip())
            if row_text:
                text.append(" ".join(row_text))

    return "\n".join(text)

# =========================
# EXTRACT TEXT
# =========================
def extract_text(file):
    if file.name.lower().endswith(".pdf"):
        return read_pdf(file)
    return read_docx(file)

# =========================
# SMART FIELD PARSER (FIX)
# =========================
def extract_fields(text):

    text = clean(text)

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

    current_key = None

    for line in lines:

        l = line.lower()

        # detect label
        if "product name" in l:
            current_key = "drug"
            continue
        elif "dose" in l:
            current_key = "dose"
            continue
        elif "indication" in l:
            current_key = "indication"
            continue
        elif "date reported" in l or "mrd" in l:
            current_key = "mrd"
            continue
        elif "patient id" in l:
            current_key = "patient_id"
            continue
        elif "date of birth" in l:
            current_key = "dob"
            continue
        elif "age" in l:
            current_key = "age"
            continue
        elif "gender" in l:
            current_key = "gender"
            continue
        elif "country" in l:
            current_key = "country"
            continue

        # value capture (IMPORTANT FIX)
        if current_key and ":" not in line:
            if fields[current_key] == "":
                fields[current_key] = line.strip()

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
# COMPARE
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
qc_file = st.file_uploader("Upload QC File", type=["pdf", "docx"])
agent_file = st.file_uploader("Upload Agent File", type=["pdf", "docx"])

if qc_file and agent_file:

    qc_text = extract_text(qc_file)
    agent_text = extract_text(agent_file)

    st.subheader("DEBUG QC RAW TEXT")
    st.text_area("QC TEXT", qc_text, height=200)

    st.subheader("DEBUG AGENT RAW TEXT")
    st.text_area("AGENT TEXT", agent_text, height=200)

    qc_data = extract_fields(qc_text)
    agent_data = extract_fields(agent_text)

    st.subheader("QC Extracted")
    st.json(qc_data)

    st.subheader("Agent Extracted")
    st.json(agent_data)

    if st.button("Run QC Check"):

        results = compare(qc_data, agent_data)

        st.subheader("Mismatch Report")

        if not results:
            st.error("No discrepancies detected")
        else:
            for r in results:
                st.markdown(f"""
### {r['field']}

QC: **{r['qc']}**  
Agent: **{r['agent']}**  
Severity: **{r['severity']}**

---
""")
