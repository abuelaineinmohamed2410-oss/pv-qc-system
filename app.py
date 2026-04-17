import streamlit as st
import pdfplumber
import re

st.set_page_config(page_title="PV QC Comparator", layout="wide")
st.title("Pharmacovigilance Structured Comparator (Stable Engine)")

# =========================
# READ PDF
# =========================
def read_pdf(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for p in pdf.pages:
            text += p.extract_text() or ""
    return text

# =========================
# CLEAN
# =========================
def clean(text):
    text = text.lower()
    text = text.replace("", " ")
    text = text.replace("•", " ")
    text = text.replace("\uf0b7", " ")
    text = re.sub(r"\s+", " ", text)
    return text

# =========================
# SPLIT BY DRUG BLOCKS (FIXED)
# =========================
def get_drug_blocks(text):

    pattern = r"(entresto\s*\d+\s*mg)"
    parts = re.split(pattern, text)

    blocks = []

    for i in range(1, len(parts), 2):
        drug = parts[i]
        context = parts[i+1] if i+1 < len(parts) else ""
        blocks.append((drug.strip(), context))

    return blocks

# =========================
# EXTRACT DRUG INFO (STRICT)
# =========================
def parse_drug(name, block):

    return {
        "drug": name,
        "dose": re.findall(r"\d+\s*mg", block),
        "frequency": "twice daily" if "twice" in block else "once daily" if "once" in block else "",
        "indication": extract_between(block, "indication", ["start date", "end date", "route", "dose"]),
    }

# =========================
# SAFE FIELD EXTRACTOR
# =========================
def extract_between(text, start_key, stop_keys):

    try:
        start = text.index(start_key)
        chunk = text[start:]

        for s in stop_keys:
            if s in chunk:
                chunk = chunk.split(s)[0]

        return chunk.replace(start_key, "").strip()
    except:
        return ""

# =========================
# PATIENT BLOCK (STRICT)
# =========================
def get_patient(text):

    patient_section = ""

    try:
        patient_section = text.split("patient")[1]
    except:
        patient_section = text

    return {
        "age": re.findall(r"\d+\s*years", patient_section),
        "dob": re.findall(r"\d{1,2}-[a-z]{3}-\d{2,4}", patient_section),
        "gender": "male" if "male" in patient_section else "female" if "female" in patient_section else "",
        "patient_id": re.findall(r"\d{4}-\d{4}-\d{4}-\d{6}", patient_section),
    }

# =========================
# MRD (CONTACT ONLY - FIX)
# =========================
def get_mrd(text):

    contact_section = ""

    try:
        contact_section = text.split("contact")[1]
    except:
        contact_section = text

    mrd = re.findall(r"\d{1,2}-[a-z]{3}-\d{2,4}", contact_section)

    return mrd

# =========================
# AE (NARRATIVE BLOCK FIX)
# =========================
def get_ae(text):

    ae_section = ""

    try:
        ae_section = text.split("adverse event")[1]
    except:
        return []

    keywords = ["non compliance", "stopping", "off-label", "off label"]

    found = []

    for k in keywords:
        if k in ae_section:
            found.append(k)

    return list(set(found))

# =========================
# FULL PARSER
# =========================
def parse(text):

    text = clean(text)

    drugs = get_drug_blocks(text)
    patient = get_patient(text)
    mrd = get_mrd(text)
    ae = get_ae(text)

    structured_drugs = []

    for d, b in drugs:
        x = parse_drug(d, b)
        structured_drugs.append(x)

    return {
        "drugs": structured_drugs,
        "patient": patient,
        "mrd": mrd,
        "ae": ae
    }

# =========================
# COMPARISON (CLEAN OBJECT-BASED)
# =========================
def compare(qc, ag):

    result = {
        "drugs": [],
        "patient": {},
        "mrd": {},
        "ae": {}
    }

    # DRUGS
    for i in range(max(len(qc["drugs"]), len(ag["drugs"]))):

        q = qc["drugs"][i] if i < len(qc["drugs"]) else None
        a = ag["drugs"][i] if i < len(ag["drugs"]) else None

        if q != a:
            result["drugs"].append((q, a))

    # PATIENT
    if qc["patient"] != ag["patient"]:
        result["patient"] = (qc["patient"], ag["patient"])

    # MRD
    if qc["mrd"] != ag["mrd"]:
        result["mrd"] = (qc["mrd"], ag["mrd"])

    # AE
    if set(qc["ae"]) != set(ag["ae"]):
        result["ae"] = (qc["ae"], ag["ae"])

    return result

# =========================
# UI
# =========================
qc_file = st.file_uploader("Upload QC PDF", type=["pdf"])
ag_file = st.file_uploader("Upload Agent PDF", type=["pdf"])

if qc_file and ag_file:

    qc = parse(read_pdf(qc_file))
    ag = parse(read_pdf(ag_file))

    if st.button("Run Comparison"):

        res = compare(qc, ag)

        st.subheader("STRUCTURED MISMATCH REPORT")

        st.markdown("## DRUGS")
        for i, (q, a) in enumerate(res["drugs"]):
            st.write(f"Drug {i+1}")
            st.write("QC:", q)
            st.write("Agent:", a)

        st.markdown("## PATIENT")
        st.write(res["patient"])

        st.markdown("## MRD")
        st.write(res["mrd"])

        st.markdown("## ADVERSE EVENTS")
        st.write(res["ae"])
