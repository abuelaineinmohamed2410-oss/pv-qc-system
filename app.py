import streamlit as st
import pdfplumber
import re

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="PV QC System", layout="wide")

st.title("Pharmacovigilance QC System")
st.markdown("QC vs Agent – structured pharma-grade validation (PDF only)")

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
# PDF READER
# =========================
def read_pdf(file):
    text = []
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text.append(page_text)
    return "\n".join(text)

# =========================
# NOISE FILTER (CRITICAL FIX)
# =========================
def is_noise(text):
    t = text.lower()
    return (
        "click or tap" in t or
        "choose an item" in t or
        "enter text" in t or
        t.strip() == ""
    )

# =========================
# SMART VALUE FINDER
# =========================
def find_value(lines, i):

    values = []

    for j in range(i + 1, min(i + 8, len(lines))):

        line = lines[j]

        # stop if new label starts
        if ":" in line and len(line.split(":")[0]) < 60:
            break

        if is_noise(line):
            continue

        values.append(line.strip())

    return " ".join(values).strip()

# =========================
# FIELD EXTRACTOR (FIXED)
# =========================
def extract_fields(text):

    text = clean(text)

    lines = [re.sub(r"\s+", " ", l.strip()) for l in text.split("\n") if l.strip()]

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

    def extract(line, i):

        if ":" in line:
            val = line.split(":", 1)[1].strip()
            if not is_noise(val):
                return val

        return find_value(lines, i)

    for i, line in enumerate(lines):

        l = line.lower()

        # =========================
        # DRUG (CRITICAL)
        # =========================
        if "product name" in l:
            fields["drug"] = extract(line, i)

        # =========================
        # DOSE
        # =========================
        elif "dose" in l and "regimen" not in l:
            fields["dose"] = extract(line, i)

        # =========================
        # INDICATION
        # =========================
        elif "indication" in l:
            fields["indication"] = extract(line, i)

        # =========================
        # MRD
        # =========================
        elif "date reported" in l or "mrd" in l:
            fields["mrd"] = extract(line, i)

        # =========================
        # PATIENT ID
        # =========================
        elif "patient id" in l:
            fields["patient_id"] = extract(line, i)

        # =========================
        # DOB
        # =========================
        elif "date of birth" in l:
            fields["dob"] = extract(line, i)

        # =========================
        # AGE
        # =========================
        elif "age" in l:
            fields["age"] = extract(line, i)

        # =========================
        # GENDER
        # =========================
        elif "gender" in l:
            fields["gender"] = extract(line, i)

        # =========================
        # COUNTRY
        # =========================
        elif "country" in l:
            fields["country"] = extract(line, i)

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
qc_file = st.file_uploader("Upload QC PDF", type=["pdf"])
agent_file = st.file_uploader("Upload Agent PDF", type=["pdf"])

if qc_file and agent_file:

    qc_text = read_pdf(qc_file)
    agent_text = read_pdf(agent_file)

    st.subheader("Raw QC Text")
    st.text_area("", qc_text, height=200)

    st.subheader("Raw Agent Text")
    st.text_area("", agent_text, height=200)

    qc_data = extract_fields(qc_text)
    agent_data = extract_fields(agent_text)

    st.subheader("QC Extracted Data")
    st.json(qc_data)

    st.subheader("Agent Extracted Data")
    st.json(agent_data)

    if st.button("Run QC Check"):

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
