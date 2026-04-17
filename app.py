import streamlit as st
import pdfplumber
import re

# =========================
# UI
# =========================
st.set_page_config(page_title="PV QC System", layout="wide")
st.title("Pharmacovigilance QC System")
st.caption("Robust QC vs Agent comparison engine")

# =========================
# PDF READ
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
# CLEAN
# =========================
def clean(t):
    t = t.lower()
    t = t.replace("", " ")
    t = t.replace("•", " ")
    t = re.sub(r"\s+", " ", t)
    return t


# =========================
# SMART VALUE EXTRACTOR
# searches multiple patterns + paragraph context
# =========================
def smart_find(text, keywords):

    # split into pseudo-blocks (important fix)
    blocks = re.split(r"\n|·|•", text)

    for b in blocks:
        b = b.strip()

        if any(k in b for k in keywords):

            # try extract after colon first
            if ":" in b:
                parts = b.split(":", 1)
                val = parts[1].strip()
                if val:
                    return val

            # fallback: last meaningful token
            return b

    return ""


# =========================
# FIELD EXTRACTION (FIXED LOGIC)
# =========================
def extract(text):

    text = clean(text)

    data = {}

    # DRUG
    drug = re.search(r"entresto\s*\d+\s*mg", text)
    data["drug"] = drug.group(0) if drug else ""

    # DOSE (IMPORTANT FIX)
    dose = re.search(r"dose.*?(\d+\s*mg|\d+mg)", text)
    if not dose:
        dose = re.search(r"(\d+\s*mg)", text)
    data["dose"] = dose.group(1) if dose else ""

    # FREQUENCY (FIXED - handles ALL cases)
    freq = smart_find(text, [
        "frequency",
        "once daily",
        "twice daily",
        "other",
        "qd",
        "bid"
    ])
    data["frequency"] = freq

    # INDICATION
    ind = smart_find(text, ["indication"])
    data["indication"] = ind

    # MRD (VERY IMPORTANT FIX)
    mrd = re.search(r"\d{1,2}-[a-z]{3}-\d{2,4}", text)
    data["mrd"] = mrd.group(0) if mrd else ""

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
    pid = re.search(r"\d{4,}-\d{2,}-\d{2,}-\d+", text)
    data["patient_id"] = pid.group(0) if pid else ""

    # COUNTRY
    country = re.search(r"\b(egypt|germany|china|austria)\b", text)
    data["country"] = country.group(0) if country else ""

    return data


# =========================
# NORMALIZE
# =========================
def norm(x):
    return re.sub(r"\s+", " ", x.strip().lower())


# =========================
# COMPARE ENGINE
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

    st.subheader("QC Extracted")
    st.json(qc_data)

    st.subheader("Agent Extracted")
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
