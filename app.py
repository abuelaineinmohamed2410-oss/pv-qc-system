import streamlit as st
import pdfplumber
import re

# =========================
# PAGE CONFIG (PRO UI)
# =========================
st.set_page_config(
    page_title="PV QC System",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =========================
# HEADER (PROFESSIONAL STYLE)
# =========================
st.markdown("""
<style>
.main-title {
    font-size: 32px;
    font-weight: 600;
    margin-bottom: 5px;
}
.sub-title {
    font-size: 16px;
    color: #666;
    margin-bottom: 20px;
}
.card {
    background-color: #f8f9fa;
    padding: 15px;
    border-radius: 10px;
    border: 1px solid #e0e0e0;
}
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='main-title'>Pharmacovigilance QC System</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-title'>QC vs Agent — discrepancy detection engine</div>", unsafe_allow_html=True)

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
# LABELS
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
# EXTRACTION ENGINE (UNCHANGED LOGIC)
# =========================
def extract_fields(text):

    text = clean(text)
    lines = [re.sub(r"\s+", " ", l.strip()) for l in text.split("\n") if l.strip()]

    fields = {k: "" for k in LABELS.keys()}

    for i, line in enumerate(lines):

        low = line.lower()

        for field, keys in LABELS.items():

            if any(k in low for k in keys):

                if ":" in line:
                    val = line.split(":", 1)[1].strip()
                    if val and not noise(val):
                        fields[field] = val
                        continue

                for j in range(i + 1, min(i + 6, len(lines))):
                    v = lines[j].strip()

                    if noise(v):
                        continue

                    if any(k in v.lower() for ks in LABELS.values() for k in ks):
                        break

                    fields[field] = v
                    break

    return {k: v.lower().strip() for k, v in fields.items() if v}

# =========================
# COMPARE ENGINE
# =========================
def compare(qc, agent):

    all_keys = set(qc.keys()).union(set(agent.keys()))
    results = []

    for k in all_keys:

        q = qc.get(k, "MISSING")
        a = agent.get(k, "MISSING")

        if q != a:
            results.append((k.upper(), q, a))

    return results

# =========================
# UI INPUT SECTION
# =========================
col1, col2 = st.columns(2)

with col1:
    qc_file = st.file_uploader("Upload QC PDF", type=["pdf"])

with col2:
    agent_file = st.file_uploader("Upload Agent PDF", type=["pdf"])

# =========================
# PROCESS
# =========================
if qc_file and agent_file:

    qc_text = read_pdf(qc_file)
    agent_text = read_pdf(agent_file)

    qc_data = extract_fields(qc_text)
    agent_data = extract_fields(agent_text)

    if st.button("Run QC Validation"):

        results = compare(qc_data, agent_data)

        st.markdown("### QC Validation Report")

        if not results:

            st.success("No discrepancies detected")

        else:

            st.markdown("""
            <div class='card'>
            <h4>Detected Discrepancies</h4>
            </div>
            """, unsafe_allow_html=True)

            st.write("")

            for field, qc_val, ag_val in results:

                st.markdown(f"""
### {field}

| QC Value | Agent Value |
|----------|-------------|
| {qc_val} | {ag_val} |

---
""")
