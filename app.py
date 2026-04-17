import streamlit as st
import pdfplumber
import re

st.set_page_config(page_title="PV QC Engine", layout="wide")
st.title("Pharmacovigilance Smart Reconciliation Engine")

# =========================
# READ PDF
# =========================
def read_pdf(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for p in pdf.pages:
            if p.extract_text():
                text += p.extract_text() + "\n"
    return text.lower()

# =========================
# CLEAN TEXT
# =========================
def clean(text):
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text

# =========================
# EXTRACT CONTEXT WINDOWS (KEY FIX)
# =========================
def get_context(text, keywords, window=200):

    hits = []

    for k in keywords:
        for m in re.finditer(k, text):
            start = max(0, m.start() - window)
            end = min(len(text), m.end() + window)
            hits.append(text[start:end])

    return hits

# =========================
# SMART VALUE EXTRACTOR
# =========================
def extract_values(contexts, pattern):

    values = []

    for c in contexts:
        values += re.findall(pattern, c)

    return list(set(values))

# =========================
# MAIN EXTRACTOR (ROBUST)
# =========================
def extract(text):

    text = clean(text)

    data = {
        "drug": set(),
        "dose": set(),
        "frequency": set(),
        "ae": set(),
        "mrd": "",
        "dob": "",
        "patient_id": "",
        "gender": "",
        "age": "",
        "country": ""
    }

    # ================= DRUG =================
    drug_ctx = get_context(text, ["entresto", "product name"])
    data["drug"] = set(extract_values(drug_ctx, r"entresto\s*\d+\s*mg"))

    # ================= DOSE =================
    data["dose"] = set(re.findall(r"\d+\s*mg", text))

    # ================= FREQUENCY =================
    freq_ctx = get_context(text, ["frequency", "once", "twice"])
    if any("once" in c for c in freq_ctx):
        data["frequency"].add("once daily")
    if any("twice" in c for c in freq_ctx):
        data["frequency"].add("twice daily")

    # ================= AE =================
    ae_ctx = get_context(text, ["adverse", "event", "stopping", "non"])
    ae_map = {
        "non compliance": ["non compliance", "non-complaint"],
        "stopping": ["stop", "stopped"],
        "off-label": ["off-label", "off label"]
    }

    for k, v in ae_map.items():
        if any(any(x in c for x in v) for c in ae_ctx):
            data["ae"].add(k)

    # ================= MRD (CRITICAL FIX) =================
    date_ctx = get_context(text, ["reported", "date", "mrd"])

    date_match = re.findall(r"\d{1,2}-[a-z]{3}-\d{2,4}", " ".join(date_ctx))
    if date_match:
        data["mrd"] = date_match[0]

    # ================= DOB =================
    dob_ctx = get_context(text, ["birth", "born", "dob"])

    dob_match = re.findall(r"\d{1,2}-[a-z]{3}-\d{2,4}", " ".join(dob_ctx))
    if dob_match:
        data["dob"] = dob_match[0]

    # ================= PATIENT ID =================
    pid = re.findall(r"\d{4}-\d{4}-\d{4}-\d{6}", text)
    if pid:
        data["patient_id"] = pid[0]

    # ================= AGE =================
    age = re.findall(r"\d+\s*years", text)
    if age:
        data["age"] = age[0]

    # ================= GENDER =================
    if "male" in text:
        data["gender"] = "male"
    elif "female" in text:
        data["gender"] = "female"

    # ================= COUNTRY =================
    if "egypt" in text:
        data["country"] = "egypt"

    return data

# =========================
# COMPARE ENGINE
# =========================
def compare(qc, ag):

    results = []

    for k in qc.keys():

        qc_v = qc.get(k)
        ag_v = ag.get(k)

        qc_set = set(qc_v) if isinstance(qc_v, set) else {qc_v} if qc_v else set()
        ag_set = set(ag_v) if isinstance(ag_v, set) else {ag_v} if ag_v else set()

        qc_set.discard("")
        ag_set.discard("")

        if qc_set != ag_set:
            results.append({
                "field": k.upper(),
                "qc": list(qc_set),
                "agent": list(ag_set)
            })

    return results

# =========================
# UI
# =========================
qc_file = st.file_uploader("Upload QC PDF", type=["pdf"])
ag_file = st.file_uploader("Upload Agent PDF", type=["pdf"])

if qc_file and ag_file:

    qc = extract(read_pdf(qc_file))
    ag = extract(read_pdf(ag_file))

    if st.button("Run Comparison"):

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
