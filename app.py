import streamlit as st
import pdfplumber
import re

st.set_page_config(page_title="PV QC Engine", layout="wide")
st.title("Pharmacovigilance Smart Matching Engine")

# =========================
# READ
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
def clean(text):
    text = text.lower()
    text = text.replace("·", " ")
    text = re.sub(r"\s+", " ", text)
    return text

# =========================
# SMART FIELD FINDER
# =========================
def find_field(text, keywords):

    best = []

    for line in text.split("."):
        for k in keywords:
            if k in line:
                best.append(line.strip())

    return best

# =========================
# VALUE EXTRACTOR
# =========================
def extract_value(lines, pattern):

    values = []

    for l in lines:
        match = re.findall(pattern, l)
        values.extend(match)

    return list(set(values))

# =========================
# FULL PARSER (SMART)
# =========================
def extract(text):

    text = clean(text)

    data = {}

    # DRUG
    drug_lines = find_field(text, ["product name", "entresto"])
    data["drug"] = extract_value(drug_lines, r"entresto\s*\d+\s*mg")

    # DOSE
    data["dose"] = extract_value(text.split("."), r"\d+\s*mg")

    # FREQUENCY
    freq = []
    if "once" in text:
        freq.append("once")
    if "twice" in text:
        freq.append("twice")
    data["frequency"] = list(set(freq))

    # AE (semantic)
    ae = []
    if "non compliance" in text or "non-complaint" in text:
        ae.append("non compliance")
    if "stopping" in text:
        ae.append("stopping")
    if "off-label" in text:
        ae.append("off-label")

    data["ae"] = ae

    # MRD
    mrd = re.findall(r"\d{1,2}-[a-z]{3}-\d{2,4}", text)
    data["mrd"] = mrd[0] if mrd else ""

    # PATIENT ID
    pid = re.findall(r"\d{4}-\d{4}-\d{4}-\d{6}", text)
    data["patient_id"] = pid[0] if pid else ""

    return data

# =========================
# COMPARE (REAL LOGIC)
# =========================
def compare(qc, ag):

    result = []

    for k in qc.keys():

        qc_v = set(qc.get(k) if isinstance(qc.get(k), list) else [qc.get(k)])
        ag_v = set(ag.get(k) if isinstance(ag.get(k), list) else [ag.get(k)])

        qc_v.discard("")
        ag_v.discard("")

        if qc_v != ag_v:
            result.append({
                "field": k.upper(),
                "qc": list(qc_v),
                "agent": list(ag_v)
            })

    return result

# =========================
# UI
# =========================
qc_file = st.file_uploader("QC PDF", type=["pdf"])
ag_file = st.file_uploader("Agent PDF", type=["pdf"])

if qc_file and ag_file:

    qc = extract(read_pdf(qc_file))
    ag = extract(read_pdf(ag_file))

    if st.button("Compare"):

        res = compare(qc, ag)

        if not res:
            st.success("No discrepancies detected")
        else:
            for r in res:
                st.markdown(f"""
### {r['field']}

QC: `{r['qc']}`  
Agent: `{r['agent']}`
---
""")
