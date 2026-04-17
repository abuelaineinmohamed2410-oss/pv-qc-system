import streamlit as st
import pdfplumber
import re

st.set_page_config(page_title="PV QC System", layout="wide")
st.title("Pharmacovigilance QC System")

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
# CLEAN
# =========================
def clean(text):
    text = text.replace("", "\n").replace("•", "\n")
    text = text.replace("\xa0", " ")
    return text

# =========================
# NOISE FILTER
# =========================
def noise(x):
    x = x.lower()
    return "click or tap" in x or "choose an item" in x or "enter text" in x

# =========================
# TARGET LABELS
# =========================
LABELS = {
    "drug": ["product name"],
    "dose": ["dose"],
    "indication": ["indication"],
    "mrd": ["date reported"],
    "patient_id": ["patient id"],
    "dob": ["date of birth"],
    "age": ["age"],
    "gender": ["gender"],
    "country": ["country"]
}

# =========================
# SMART TOKEN PARSER (FIX)
# =========================
def extract_fields(text):

    text = clean(text)

    lines = [re.sub(r"\s+", " ", l.strip()) for l in text.split("\n") if l.strip()]

    fields = {k: "" for k in LABELS.keys()}

    for i, line in enumerate(lines):

        low = line.lower()

        for field, keys in LABELS.items():

            if any(k in low for k in keys):

                # CASE 1: same line value
                if ":" in line:
                    val = line.split(":", 1)[1].strip()
                    if val and not noise(val):
                        fields[field] = val
                        continue

                # CASE 2: next meaningful line
                for j in range(i + 1, min(i + 6, len(lines))):

                    v = lines[j].strip()

                    if noise(v):
                        continue

                    # stop if next label starts
                    if any(k in v.lower() for ks in LABELS.values() for k in ks):
                        break

                    fields[field] = v
                    break

    return {k: v.lower().strip() for k, v in fields.items() if v}

# =========================
# COMPARE
# =========================
def compare(qc, agent):

    all_keys = set(qc.keys()).union(set(agent.keys()))
    results = []

    for k in all_keys:

        q = qc.get(k, "MISSING")
        a = agent.get(k, "MISSING")

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

    qc_data = extract_fields(qc_text)
    agent_data = extract_fields(agent_text)

    st.subheader("QC Extracted")
    st.json(qc_data)

    st.subheader("Agent Extracted")
    st.json(agent_data)

    if st.button("Run QC Check"):

        results = compare(qc_data, agent_data)

        st.subheader("Mismatch Report")

        if not results:
            st.error("No discrepancies detected (check extraction!)")
        else:
            for r in results:
                st.markdown(f"""
### {r['field']}
QC: **{r['qc']}**  
Agent: **{r['agent']}**
---
""")
