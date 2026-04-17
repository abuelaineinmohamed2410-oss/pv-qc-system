import streamlit as st
import pdfplumber
import re
from collections import defaultdict

st.set_page_config(page_title="PV Structured Comparator", layout="wide")
st.title("Pharmacovigilance Structured QC vs Agent Comparator")

# =========================
# READ PDF
# =========================
def read_pdf(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for p in pdf.pages:
            text += p.extract_text() or ""
    return text.lower()

# =========================
# CLEAN TEXT
# =========================
def clean(text):
    text = text.lower()
    text = text.replace("", " ").replace("•", " ").replace("\uf0b7", " ")
    text = re.sub(r"\s+", " ", text)
    return text

# =========================
# SPLIT DRUG BLOCKS (CRITICAL FIX)
# =========================
def extract_drug_blocks(text):

    # split by product name occurrence
    blocks = re.split(r"(entresto\s*\d+\s*mg)", text)

    drugs = []

    for i in range(1, len(blocks), 2):
        name = blocks[i].strip()
        content = blocks[i+1] if i+1 < len(blocks) else ""

        drugs.append((name, content))

    return drugs

# =========================
# EXTRACT DRUG INFO
# =========================
def parse_drug(name, block):

    data = {
        "drug": name,
        "dose": "",
        "frequency": "",
        "indication": "",
        "mrd": "",
    }

    # dose
    dose = re.findall(r"\d+\s*mg", block)
    if dose:
        data["dose"] = dose[0]

    # frequency
    if "twice" in block:
        data["frequency"] = "twice daily"
    elif "once" in block:
        data["frequency"] = "once daily"

    # indication
    ind = re.findall(r"indication.*?:\s*([a-z ]+)", block)
    if ind:
        data["indication"] = ind[0].strip()

    return data

# =========================
# PATIENT INFO
# =========================
def extract_patient(text):

    patient = {}

    patient["age"] = re.findall(r"\d+\s*years", text)
    patient["dob"] = re.findall(r"\d{1,2}-[a-z]{3}-\d{2,4}", text)
    patient["gender"] = ["male"] if "male" in text else ["female"] if "female" in text else []
    patient["patient_id"] = re.findall(r"\d{4}-\d{4}-\d{4}-\d{6}", text)
    patient["country"] = ["egypt"] if "egypt" in text else []

    return patient

# =========================
# AE EXTRACTION
# =========================
def extract_ae(text):

    ae_keywords = ["non compliance", "stopping", "off-label", "off label"]

    aes = []

    for a in ae_keywords:
        if a in text:
            aes.append(a)

    return list(set(aes))

# =========================
# MAIN PARSER
# =========================
def parse(text):

    text = clean(text)

    # DRUGS
    drug_blocks = extract_drug_blocks(text)

    drugs = []
    for name, block in drug_blocks:
        drugs.append(parse_drug(name, block))

    # PATIENT
    patient = extract_patient(text)

    # AE
    ae = extract_ae(text)

    return {
        "drugs": drugs,
        "patient": patient,
        "ae": ae
    }

# =========================
# COMPARE
# =========================
def compare(qc, ag):

    report = {"drug_mismatch": [], "patient_mismatch": [], "ae_mismatch": []}

    # DRUG comparison
    for i in range(max(len(qc["drugs"]), len(ag["drugs"]))):

        if i >= len(qc["drugs"]) or i >= len(ag["drugs"]):
            report["drug_mismatch"].append((qc["drugs"][i] if i < len(qc["drugs"]) else None,
                                            ag["drugs"][i] if i < len(ag["drugs"]) else None))
            continue

        q = qc["drugs"][i]
        a = ag["drugs"][i]

        if q != a:
            report["drug_mismatch"].append((q, a))

    # PATIENT
    if qc["patient"] != ag["patient"]:
        report["patient_mismatch"] = (qc["patient"], ag["patient"])

    # AE
    if set(qc["ae"]) != set(ag["ae"]):
        report["ae_mismatch"] = (qc["ae"], ag["ae"])

    return report

# =========================
# UI
# =========================
qc_file = st.file_uploader("Upload QC PDF", type=["pdf"])
ag_file = st.file_uploader("Upload Agent PDF", type=["pdf"])

if qc_file and ag_file:

    qc = parse(read_pdf(qc_file))
    ag = parse(read_pdf(ag_file))

    if st.button("Run Structured Comparison"):

        res = compare(qc, ag)

        st.subheader("STRUCTURED MISMATCH REPORT")

        # DRUGS
        st.markdown("## DRUGS")
        for i, (q, a) in enumerate(res["drug_mismatch"]):
            st.markdown(f"""
### Drug {i+1}
**QC:** {q}
**Agent:** {a}
""")

        # PATIENT
        st.markdown("## PATIENT")
        st.write(res["patient_mismatch"])

        # AE
        st.markdown("## ADVERSE EVENTS")
        st.write(res["ae_mismatch"])
