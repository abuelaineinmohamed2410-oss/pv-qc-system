import streamlit as st
import pdfplumber
import re
from collections import defaultdict

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="PV QC System",
    layout="wide"
)

st.title("Pharmacovigilance QC System")
st.caption("High-precision QC vs Agent discrepancy detection")

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
    text = text.replace("", "\n").replace("•", "\n")
    text = re.sub(r"\s+", " ", text)
    return text


# =========================
# VALUE NORMALIZATION (VERY IMPORTANT)
# =========================
def normalize(v):
    if not v:
        return ""

    v = v.lower().strip()

    # unify mg formats
    v = v.replace("milligram", "mg")
    v = re.sub(r"\s+", " ", v)

    # remove junk placeholders
    junk = [
        "click or tap here to enter text",
        "choose an item",
        "enter text",
        "na",
        "not reported",
        "unknown"
    ]

    for j in junk:
        v = v.replace(j, "")

    return v.strip()


# =========================
# SMART FIELD EXTRACTION (KEY FIX)
# =========================
def extract_kv(text):

    lines = text.split("\n")
    data = defaultdict(list)

    current_key = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # detect key-value line
        if ":" in line:
            parts = line.split(":", 1)
            key = parts[0].strip()
            value = parts[1].strip()

            current_key = key
            data[key].append(value)

        else:
            # continuation of previous field
            if current_key:
                data[current_key].append(line)

    # flatten
    flat = {}
    for k, v in data.items():
        joined = " ".join(v)
        flat[k] = normalize(joined)

    return flat


# =========================
# FIELD MAPPING (IMPORTANT)
# =========================
MAP = {
    "drug": ["product name", "what is the name of the product"],
    "dose": ["dose", "what dose"],
    "frequency": ["frequency", "how often"],
    "indication": ["indication"],
    "mrd": ["date reported", "reported on"],
    "dob": ["date of birth"],
    "age": ["age"],
    "gender": ["gender"],
    "patient_id": ["patient id"],
    "country": ["country"]
}


def find_value(data, keys):
    for k, v in data.items():
        for target in keys:
            if target in k:
                return v
    return ""


# =========================
# STRUCTURE BUILDER
# =========================
def build_struct(data):

    return {
        "drug": find_value(data, MAP["drug"]),
        "dose": find_value(data, MAP["dose"]),
        "frequency": find_value(data, MAP["frequency"]),
        "indication": find_value(data, MAP["indication"]),
        "mrd": find_value(data, MAP["mrd"]),
        "dob": find_value(data, MAP["dob"]),
        "age": find_value(data, MAP["age"]),
        "gender": find_value(data, MAP["gender"]),
        "patient_id": find_value(data, MAP["patient_id"]),
        "country": find_value(data, MAP["country"]),
    }


# =========================
# COMPARISON ENGINE (STRONG)
# =========================
def compare(qc, agent):

    results = []

    for key in qc.keys():

        q = qc.get(key, "")
        a = agent.get(key, "")

        if q != a:
            results.append({
                "field": key.upper(),
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

    qc_raw = extract_kv(clean(qc_text))
    agent_raw = extract_kv(clean(agent_text))

    qc = build_struct(qc_raw)
    agent = build_struct(agent_raw)

    if st.button("Run QC Validation"):

        diffs = compare(qc, agent)

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
