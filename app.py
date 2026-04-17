import streamlit as st
import pdfplumber
import re

st.set_page_config(page_title="PV QC Smart System", layout="wide")
st.title("Pharmacovigilance QC System (Smart Matching Engine)")

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
# SMART FIELD EXTRACTOR (ROBUST)
# =========================
def extract(text):

    data = {
        "drug": [],
        "dose": [],
        "frequency": [],
        "indication": [],
        "mrd": "",
        "dob": "",
        "patient_id": "",
        "gender": "",
        "age": "",
        "country": "",
        "ae": []
    }

    text = norm(text)

    # -------- DRUG --------
    drugs = re.findall(r"entresto\s*\d+\s*mg", text)
    data["drug"] = list(set([norm(d) for d in drugs]))

    # -------- DOSE --------
    doses = re.findall(r"\d+\s*mg", text)
    data["dose"] = list(set([norm(d) for d in doses]))

    # -------- FREQUENCY --------
    if "once daily" in text or "once a day" in text:
        data["frequency"].append("once daily")
    if "twice daily" in text or "twice a day" in text:
        data["frequency"].append("twice daily")
    if "other" in text:
        data["frequency"].append("other")

    data["frequency"] = list(set(data["frequency"]))

    # -------- INDICATION --------
    if "hf" in text or "heart failure" in text:
        data["indication"].append("hf")

    # -------- MRD --------
    mrd = re.search(r"\d{1,2}-[a-z]{3}-\d{2,4}", text)
    if mrd:
        data["mrd"] = mrd.group()

    # -------- DOB --------
    dob = re.search(r"\d{1,2}-[a-z]{3}-\d{2,4}", text)
    if dob:
        data["dob"] = dob.group()

    # -------- PATIENT ID --------
    pid = re.search(r"\d{4}-\d{4}-\d{4}-\d{6}", text)
    if pid:
        data["patient_id"] = pid.group()

    # -------- GENDER --------
    if "male" in text:
        data["gender"] = "male"
    elif "female" in text:
        data["gender"] = "female"

    # -------- AGE --------
    age = re.search(r"\d+\s*years", text)
    if age:
        data["age"] = age.group()

    # -------- COUNTRY --------
    if "egypt" in text:
        data["country"] = "egypt"

    # -------- AE --------
    ae_keywords = [
        "non compliance",
        "stopping",
        "off-label",
        "off label",
        "adverse event"
    ]

    data["ae"] = [k for k in ae_keywords if k in text]

    return data

# =========================
# SMART COMPARATOR (CORE FIX)
# =========================
def smart_compare(qc, agent):

    results = []

    def diff(field, a, b):

        a_set = set(a) if isinstance(a, list) else {a}
        b_set = set(b) if isinstance(b, list) else {b}

        return a_set != b_set

    mapping = [
        "drug", "dose", "frequency", "indication",
        "mrd", "dob", "patient_id", "gender", "age", "country"
    ]

    for f in mapping:
        if diff(f, qc.get(f, []), agent.get(f, [])):
            results.append({
                "field": f.upper(),
                "qc": qc.get(f),
                "agent": agent.get(f)
            })

    # AE separately
    if set(qc.get("ae", [])) != set(agent.get("ae", [])):
        results.append({
            "field": "ADVERSE EVENTS",
            "qc": qc.get("ae"),
            "agent": agent.get("ae")
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

    qc = extract(qc_text)
    agent = extract(agent_text)

    if st.button("Run QC Validation"):

        results = smart_compare(qc, agent)

        st.subheader("Mismatch Report")

        if not results:
            st.success("No discrepancies detected")
        else:
            for r in results:

                st.markdown(f"""
### {r['field']}

QC: `{r['qc']}`  
Agent: `{r['agent']}`

---
""")
