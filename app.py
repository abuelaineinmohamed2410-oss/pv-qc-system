import streamlit as st
import pdfplumber
import re

st.set_page_config(page_title="PV Comparator", layout="wide")
st.title("Pharmacovigilance QC vs Agent Comparator")

# =========================
# READ
# =========================
def read_pdf(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for p in pdf.pages:
            text += p.extract_text() or ""
    return text.lower()

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
# STRONG LABEL DETECTOR
# =========================
LABELS = [
    "product name",
    "dose",
    "frequency",
    "indication",
    "start date",
    "end date",
    "date reported",
    "gender",
    "age",
    "patient id",
    "date of birth",
    "country",
    "adverse event"
]

# =========================
# LINE-BASED PARSER (CORE FIX)
# =========================
def parse(text):

    text = clean(text)
    lines = text.split(".")

    data = {
        "drug": [],
        "dose": [],
        "frequency": [],
        "indication": [],
        "mrd": [],
        "dob": [],
        "patient_id": [],
        "gender": [],
        "age": [],
        "country": [],
        "ae": []
    }

    current_label = None

    for line in lines:

        line = line.strip()

        if not line:
            continue

        # detect label
        for l in LABELS:
            if l in line:
                current_label = l

        # extract values safely
        if "entresto" in line:
            data["drug"].append(line.split("entresto")[0] + "entresto" + re.findall(r"\d+\s*mg", line)[0])

        if "dose" in current_label and re.search(r"\d+\s*mg", line):
            data["dose"].append(re.findall(r"\d+\s*mg", line)[0])

        if "frequency" in current_label:
            if "twice" in line:
                data["frequency"].append("twice daily")
            if "once" in line:
                data["frequency"].append("once daily")

        if "indication" in current_label:
            data["indication"].append(line.split(":")[-1].strip())

        if "date reported" in line:
            data["mrd"].extend(re.findall(r"\d{1,2}-[a-z]{3}-\d{2,4}", line))

        if "birth" in line:
            data["dob"].extend(re.findall(r"\d{1,2}-[a-z]{3}-\d{2,4}", line))

        if "patient id" in line:
            data["patient_id"].extend(re.findall(r"\d{4}-\d{4}-\d{4}-\d{6}", line))

        if "age" in line:
            data["age"].extend(re.findall(r"\d+", line))

        if "male" in line or "female" in line:
            data["gender"].append("male" if "male" in line else "female")

        if "egypt" in line:
            data["country"].append("egypt")

        if "non compliance" in line or "stopping" in line or "off-label" in line:
            data["ae"].append(line.strip())

    # FINAL CLEANUP (CRITICAL)
    for k in data:
        data[k] = list(set([x.strip() for x in data[k] if x]))

    return data

# =========================
# COMPARE
# =========================
def compare(qc, ag):

    result = {}

    for k in qc.keys():

        if qc[k] != ag[k]:
            result[k] = {
                "qc": qc[k],
                "agent": ag[k]
            }

    return result

# =========================
# UI
# =========================
qc_file = st.file_uploader("Upload QC PDF", type=["pdf"])
ag_file = st.file_uploader("Upload Agent PDF", type=["pdf"])

if qc_file and ag_file:

    qc = parse(read_pdf(qc_file))
    ag = parse(read_pdf(ag_file))

    if st.button("Compare"):

        res = compare(qc, ag)

        st.subheader("MISMATCH REPORT (CLEAN)")

        for k, v in res.items():

            st.markdown(f"""
### {k.upper()}
**QC:** {v['qc']}
**AGENT:** {v['agent']}
""")
