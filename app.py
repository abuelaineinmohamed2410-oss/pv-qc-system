import streamlit as st
import pdfplumber
import re

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="PV QC System", layout="wide")

st.title("Pharmacovigilance QC System")
st.caption("Robust QC vs Agent discrepancy detection (pharma-grade)")

# =========================
# PDF TEXT EXTRACTION
# =========================
def read_pdf(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for p in pdf.pages:
            t = p.extract_text()
            if t:
                text += t + "\n"
    return text


# =========================
# CLEAN TEXT
# =========================
def clean(text):
    text = text.lower()
    text = text.replace("", " ")
    text = text.replace("•", " ")
    text = re.sub(r"\s+", " ", text)
    return text


# =========================
# SMART VALUE FINDER (KEY FIX)
# searches entire text instead of lines
# =========================
def find(patterns, text):
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return ""


# =========================
# FIELD EXTRACTION ENGINE
# =========================
def extract(text):

    text = clean(text)

    data = {}

    # DRUG (captures strength variations)
    data["drug"] = find([
        r"product name.*?entresto\s*([\d]+)\s*mg",
        r"entresto\s*([\d]+)\s*mg",
    ], text)

    # FULL drug string
    drug_match = re.search(r"entresto\s*[\d]+\s*mg", text)
    data["drug_full"] = drug_match.group(0) if drug_match else ""

    # DOSE (captures mg variations anywhere)
    data["dose"] = find([
        r"dose.*?([\d]+\s*mg)",
        r"([\d]+\s*mg)\s*\(milligram\)",
        r"([\d]+\s*mg)"
    ], text)

    # FREQUENCY (very important fix)
    freq_match = re.search(
        r"(once daily|twice daily|three times daily|other|qd|bid|tid)",
        text
    )
    data["frequency"] = freq_match.group(1) if freq_match else ""

    # INDICATION
    ind = re.search(r"indication.*?([a-z\s]+?)(?:route|dose|frequency|$)", text)
    data["indication"] = ind.group(1).strip() if ind else ""

    # MRD (date reported)
    mrd = re.search(r"date reported.*?(\d{1,2}-[a-z]{3}-\d{2,4})", text)
    data["mrd"] = mrd.group(1) if mrd else ""

    # DOB
    dob = re.search(r"date of birth.*?(\d{1,2}[-/][a-z0-9]+[-/]\d{2,4})", text)
    data["dob"] = dob.group(1) if dob else ""

    # AGE
    age = re.search(r"(\d{1,3})\s*years", text)
    data["age"] = age.group(1) if age else ""

    # GENDER
    gender = re.search(r"\b(male|female)\b", text)
    data["gender"] = gender.group(1) if gender else ""

    # PATIENT ID
    pid = re.search(r"patient id.*?(\d{4,}-\d{2,}-\d{2,}-\d+)", text)
    data["patient_id"] = pid.group(1) if pid else ""

    # COUNTRY
    country = re.search(r"country.*?(egypt|germany|china|austria)", text)
    data["country"] = country.group(1) if country else ""

    return data


# =========================
# NORMALIZATION
# =========================
def norm(x):
    return re.sub(r"\s+", " ", x.strip().lower())


# =========================
# STRONG COMPARISON ENGINE
# =========================
def compare(qc, agent):

    results = []

    keys = set(qc.keys()).union(agent.keys())

    for k in keys:

        q = norm(qc.get(k, ""))
        a = norm(agent.get(k, ""))

        if q != a:
            results.append({
                "field": k.upper(),
                "qc": q,
                "agent": a
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

    qc_data = extract(qc_text)
    agent_data = extract(agent_text)

    st.subheader("DEBUG (QC)")
    st.json(qc_data)

    st.subheader("DEBUG (AGENT)")
    st.json(agent_data)

    if st.button("Run QC Validation"):

        diffs = compare(qc_data, agent_data)

        st.subheader("STRUCTURED MISMATCH REPORT")

        if not diffs:
            st.success("No discrepancies detected")
        else:
            for d in diffs:
                st.markdown(f"""
### {d['field']}
- QC: `{d['qc']}`
- Agent: `{d['agent']}`
---
""")
