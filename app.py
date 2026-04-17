import streamlit as st
import pdfplumber
import re

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(page_title="PV QC System", layout="wide")
st.title("PV Mismatch Checker")
st.caption("If Your Fearing of Misisng a Case, You should Try Me...")

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
# NOISE FILTER
# =========================
def is_noise(v):
    return any(x in v for x in [
        "click or tap",
        "choose an item",
        "enter text",
        "na",
        "not reported",
        "unknown / not reported"
    ])


# =========================
# SAFE FIELD EXTRACTION
# =========================
def extract_field(text, patterns):

    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            val = m.group(1).strip()

            if is_noise(val):
                continue

            if len(val) > 120:
                continue

            return val

    return ""


# =========================
# EXTRACTION ENGINE
# =========================
def extract(text):

    text = clean(text)

    data = {}

    # DRUG
    drug = re.search(r"entresto\s*\d+\s*mg", text)
    data["drug"] = drug.group(0) if drug else ""

    # DOSE
    data["dose"] = extract_field(text, [
        r"dose[:\s]*([0-9]+\s*mg)",
        r"(\d+\s*mg)"
    ])

    # FREQUENCY
    data["frequency"] = extract_field(text, [
        r"frequency[:\s]*([a-z\s,/()]+)",
        r"(once daily|twice daily|three times daily|other[^\.]*)"
    ])

    # INDICATION
    data["indication"] = extract_field(text, [
        r"indication[:\s]*([a-z\s]+)"
    ])

    # MRD
    mrd = re.search(r"\d{1,2}-[a-z]{3}-\d{2,4}", text)
    data["mrd"] = mrd.group(0) if mrd else ""

    # DOB
    dob = re.search(r"date of birth[:\s]*([0-9a-z/-]+)", text)
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

    diffs = []

    keys = set(qc.keys()).union(agent.keys())

    for k in keys:
        q = norm(qc.get(k, ""))
        a = norm(agent.get(k, ""))

        if q != a:
            diffs.append({
                "field": k.upper(),
                "qc": q,
                "agent": a
            })

    return diffs


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

    if st.button("Run QC Validation"):

        diffs = compare(qc_data, agent_data)

        st.subheader("Now let's see what you have missed", "I will not notify anyone...")

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
