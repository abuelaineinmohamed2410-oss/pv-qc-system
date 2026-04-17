import streamlit as st
import pdfplumber
import re

st.set_page_config(page_title="PV QC Smart Engine", layout="wide")
st.title("Pharmacovigilance QC Smart Comparator")

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
# CLEAN TEXT
# =========================
def clean(text):
    text = text.lower()
    text = text.replace("·", " ")
    text = re.sub(r"\s+", " ", text)
    return text

# =========================
# IGNORE NOISE (CRITICAL FIX)
# =========================
def remove_noise(text):

    noise_patterns = [
        "other dosage",
        "describe the frequency",
        "additional dosage",
        "click or tap here to enter text",
        "choose an item"
    ]

    for n in noise_patterns:
        text = text.replace(n, " ")

    return text

# =========================
# SMART FIELD EXTRACTION
# =========================
def extract(text):

    text = remove_noise(clean(text))

    data = {
        "drug": [],
        "dose": [],
        "frequency": [],
        "ae": [],
        "mrd": "",
        "dob": "",
        "patient_id": "",
        "gender": "",
        "age": "",
        "country": ""
    }

    # ================= DRUG =================
    data["drug"] = list(set(re.findall(r"entresto\s*\d+\s*mg", text)))

    # ================= DOSE =================
    data["dose"] = list(set(re.findall(r"\d+\s*mg", text)))

    # ================= FREQUENCY =================
    freq = []
    if "once daily" in text or "once a day" in text:
        freq.append("once daily")
    if "twice daily" in text or "twice a day" in text:
        freq.append("twice daily")
    data["frequency"] = list(set(freq))

    # ================= AE =================
    ae_map = {
        "non compliance": ["non compliance", "non-complaint"],
        "stopping": ["stop", "stopped", "stopping"],
        "off-label": ["off-label", "off label"]
    }

    for key, variants in ae_map.items():
        if any(v in text for v in variants):
            data["ae"].append(key)

    data["ae"] = list(set(data["ae"]))

    # ================= MRD (IMPORTANT FIX) =================
    mrd_patterns = [
        r"date reported\s*[:\-]?\s*(\d{1,2}-[a-z]{3}-\d{2,4})",
        r"reported on\s*(\d{1,2}-[a-z]{3}-\d{2,4})",
        r"mrd\s*[:\-]?\s*(\d{1,2}-[a-z]{3}-\d{2,4})"
    ]

    for p in mrd_patterns:
        m = re.search(p, text)
        if m:
            data["mrd"] = m.group(1)
            break

    # ================= DOB (IMPORTANT FIX) =================
    dob_patterns = [
        r"date of birth\s*[:\-]?\s*(\d{1,2}-[a-z]{3}-\d{2,4})",
        r"born\s*[:\-]?\s*(\d{1,2}-[a-z]{3}-\d{2,4})"
    ]

    for p in dob_patterns:
        m = re.search(p, text)
        if m:
            data["dob"] = m.group(1)
            break

    # ================= PATIENT ID =================
    pid = re.search(r"\d{4}-\d{4}-\d{4}-\d{6}", text)
    if pid:
        data["patient_id"] = pid.group()

    # ================= AGE =================
    age = re.search(r"\d+\s*years", text)
    if age:
        data["age"] = age.group()

    # ================= GENDER =================
    if "male" in text:
        data["gender"] = "male"
    if "female" in text:
        data["gender"] = "female"

    # ================= COUNTRY =================
    if "egypt" in text:
        data["country"] = "egypt"

    return data

# =========================
# SAFE COMPARE
# =========================
def compare(qc, ag):

    results = []

    keys = qc.keys()

    for k in keys:

        qc_v = qc.get(k)
        ag_v = ag.get(k)

        # normalize lists
        if isinstance(qc_v, list):
            qc_v = set(qc_v)
        else:
            qc_v = {qc_v} if qc_v else set()

        if isinstance(ag_v, list):
            ag_v = set(ag_v)
        else:
            ag_v = {ag_v} if ag_v else set()

        qc_v.discard("")
        ag_v.discard("")

        if qc_v != ag_v:
            results.append({
                "field": k.upper(),
                "qc": list(qc_v),
                "agent": list(ag_v)
            })

    return results

# =========================
# UI
# =========================
qc_file = st.file_uploader("Upload QC PDF", type=["pdf"])
ag_file = st.file_uploader("Upload Agent PDF", type=["pdf"])

if qc_file and ag_file:

    qc_text = read_pdf(qc_file)
    ag_text = read_pdf(ag_file)

    qc = extract(qc_text)
    ag = extract(ag_text)

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
