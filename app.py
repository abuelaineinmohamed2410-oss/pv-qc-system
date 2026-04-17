import streamlit as st
import pdfplumber
import re

st.set_page_config(page_title="PV QC Comparator", layout="wide")
st.title("Pharmacovigilance QC vs Agent Comparator (Clean Engine)")

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
    text = text.replace("", " ")
    text = text.replace("•", " ")
    text = text.replace("\uf0b7", " ")
    text = re.sub(r"\s+", " ", text)
    return text

# =========================
# LABEL MAP (IMPORTANT FIX)
# =========================
FIELDS = {
    "drug": "product name",
    "dose": "dose",
    "frequency": "frequency",
    "indication": "indication",
    "mrd": "date reported",
    "dob": "date of birth",
    "patient_id": "patient id",
    "gender": "gender",
    "country": "country",
}

# =========================
# VALUE CLEANER (CRITICAL FIX)
# =========================
def clean_value(v):

    v = v.strip()

    # remove label contamination
    v = re.sub(r"product information.*?:", "", v)
    v = re.sub(r"indication.*?:", "", v)
    v = re.sub(r"dose.*?:", "", v)

    # remove repeated spaces
    v = re.sub(r"\s+", " ", v)

    return v.strip()

# =========================
# LABEL → VALUE PARSER (CORE FIX)
# =========================
def parse(text):

    text = clean(text)

    data = {k: [] for k in FIELDS.keys()}
    data["ae"] = []

    # split by sentences / bullets
    chunks = re.split(r"[•\.\n]", text)

    for i, chunk in enumerate(chunks):

        chunk = chunk.strip()
        if not chunk:
            continue

        for field, label in FIELDS.items():

            if label in chunk:

                value = chunk.split(label)[-1]

                value = clean_value(value)

                # store only clean value
                if value and len(value) < 200:
                    data[field].append(value)

        # AE detection (separate logic)
        if "non compliance" in chunk or "stopping" in chunk or "off-label" in chunk:
            data["ae"].append(chunk.strip())

    # deduplicate
    for k in data:
        data[k] = list(set(data[k]))

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

        st.subheader("MISMATCH REPORT (CLEAN OUTPUT)")

        for k, v in res.items():

            st.markdown(f"""
### {k.upper()}
**QC:** {v['qc']}
**AGENT:** {v['agent']}
""")
