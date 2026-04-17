import streamlit as st
import pdfplumber
import re

st.set_page_config(page_title="PV QC Smart Comparator", layout="wide")
st.title("Pharmacovigilance Smart QC Comparator")

# =========================
# READ PDF
# =========================
def read_pdf(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for p in pdf.pages:
            t = p.extract_text()
            if t:
                text += t + "\n"
    return text.lower()

# =========================
# NORMALIZATION
# =========================
def norm(x):
    if not x:
        return ""
    x = x.lower()
    x = x.replace("mg", " mg")
    x = re.sub(r"\s+", " ", x)
    return x.strip()

# =========================
# UNIVERSAL FACT EXTRACTOR
# =========================
def extract_facts(text):

    text = norm(text)

    facts = {
        "drug": set(),
        "dose": set(),
        "frequency": set(),
        "ae": set(),
        "mrd": "",
        "dob": "",
        "patient_id": ""
    }

    # DRUGS (robust multi-match)
    facts["drug"] = set(re.findall(r"entresto\s*\d+\s*mg", text))

    # DOSE (normalize all mg values)
    facts["dose"] = set(re.findall(r"\d+\s*mg", text))

    # FREQUENCY (semantic detection)
    if "once daily" in text or "once a day" in text:
        facts["frequency"].add("once daily")
    if "twice daily" in text or "twice a day" in text:
        facts["frequency"].add("twice daily")
    if "other" in text:
        facts["frequency"].add("other")

    # AE (semantic keywords)
    ae_map = {
        "non compliance": ["non compliance", "non-complaint"],
        "stopping": ["stopped", "stop", "stopping"],
        "off label": ["off-label", "off label"]
    }

    for key, variants in ae_map.items():
        if any(v in text for v in variants):
            facts["ae"].add(key)

    # MRD (any date format)
    mrd = re.search(r"\d{1,2}-[a-z]{3}-\d{2,4}", text)
    if mrd:
        facts["mrd"] = mrd.group()

    # DOB
    dob = re.search(r"\d{1,2}-[a-z]{3}-\d{2,4}", text)
    if dob:
        facts["dob"] = dob.group()

    # PATIENT ID
    pid = re.search(r"\d{4}-\d{4}-\d{4}-\d{6}", text)
    if pid:
        facts["patient_id"] = pid.group()

    return facts

# =========================
# SMART COMPARISON ENGINE
# =========================
def compare(qc, ag):

    report = []

    def diff(name, a, b):

        if isinstance(a, set) or isinstance(b, set):
            if set(a) != set(b):
                return True
        else:
            if a != b:
                return True

        return False

    # compare fields
    fields = ["drug", "dose", "frequency", "ae", "mrd", "dob", "patient_id"]

    for f in fields:
        if diff(f, qc.get(f), ag.get(f)):
            report.append({
                "field": f.upper(),
                "qc": qc.get(f),
                "agent": ag.get(f)
            })

    return report

# =========================
# UI
# =========================
qc_file = st.file_uploader("Upload QC PDF", type=["pdf"])
ag_file = st.file_uploader("Upload Agent PDF", type=["pdf"])

if qc_file and ag_file:

    qc_text = read_pdf(qc_file)
    ag_text = read_pdf(ag_file)

    qc = extract_facts(qc_text)
    ag = extract_facts(ag_text)

    if st.button("Run Smart Comparison"):

        result = compare(qc, ag)

        st.subheader("Mismatch Report (Smart Structured Output)")

        if not result:
            st.success("No discrepancies detected")
        else:
            for r in result:

                st.markdown(f"""
### {r['field']}

QC: `{sorted(list(r['qc'])) if isinstance(r['qc'], set) else r['qc']}`  
Agent: `{sorted(list(r['agent'])) if isinstance(r['agent'], set) else r['agent']}`

---
""")
