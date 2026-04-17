import streamlit as st
import pdfplumber
import re

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(page_title="PV QC System", layout="wide")
st.title("Pharmacovigilance QC System")
st.caption("Structured QC vs Agent mismatch detection engine")

# =========================
# PDF READER
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
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text


# =========================
# REMOVE NOISE VALUES
# =========================
def is_noise(v):
    noise_words = [
        "click or tap",
        "choose an item",
        "enter text",
        "na ",
        "na",
        "not reported",
        "unknown / not reported"
    ]
    return any(n in v for n in noise_words)


# =========================
# SAFE FIELD EXTRACTION (IMPORTANT FIX)
# =========================
def extract_field(text, label_patterns):

    for pattern in label_patterns:
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            val = match.group(1).strip()

            # remove garbage
            if is_noise(val):
                continue

            # prevent full document capture
            if len(val) > 120:
                continue

            return val

    return ""


# =========================
# MAIN EXTRACTION ENGINE
# =========================
def extract(text):

    text = clean(text)

    data = {}

    # -------------------------
    # DRUG
    # -------------------------
    drug = re.search(r"entresto\s*\d+\s*mg", text)
    data["drug"] = drug.group(0) if drug else ""

    # -------------------------
    # DOSE
    # -------------------------
    data["dose"] = extract_field(text, [
        r"dose[:\s]*([0-9]+\s*mg)",
        r"what dose.*?([0-9]+\s*mg)",
        r"(\d+\s*mg)"
    ])

    # -------------------------
    # FREQUENCY (FIXED PROPERLY)
    # -------------------------
    freq = extract_field(text, [
        r"frequency[:\s]*([a-z\s,/]+)",
        r"what was the frequency\??\s*([a-z\s,/()]+)",
        r"(once daily|twice daily|three times daily|other[^\.]*)"
    ])
    data["frequency"] = freq

    # -------------------------
    # INDICATION
    # -------------------------
    data["indication"] = extract_field(text, [
        r"indication[:\s]*([a-z\s]+)",
    ])

    # -------------------------
    # MRD (DATE REPORTED)
    # -------------------------
    mrd = re.search(r"\d{1,2}-[a-z]{3}-\d{2,4}", text)
    data["mrd"] = mrd.group(0) if mrd else ""

    # -------------------------
    # DOB
    # -------------------------
    dob = re.search(r"date of birth[:\s]*([0-9a-z/-]+)", text)
    data["dob"] = dob.group(1) if dob else ""

    # -------------------------
    # AGE
    # -------------------------
    age = re.search(r"(\d{1,3})\s*years", text)
    data["age"] = age.group(1) if age else ""

    # -------------------------
    # GENDER
    # -------------------------
    gender = re.search(r"\b(male|female)\b", text)
    data["gender"] = gender.group(1) if gender else ""

    # -------------------------
    # PATIENT ID
    # -------------------------
    pid = re.search(r"\d{4,}-\d{2,}-\d{2,}-\d+", text)
    data["patient_id"] = pid.group(0) if pid else ""

    # -------------------------
    # COUNTRY
    # -------------------------
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

    keys = set(qc.keys()).union(set(agent.keys()))

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

    st.subheader("QC Extracted Data")
    st.json(qc_data)

    st.subheader("Agent Extracted Data")
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
