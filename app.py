import streamlit as st
import pdfplumber
import re

st.set_page_config(page_title="PV QC System", layout="wide")
st.title("Pharmacovigilance QC System (Enterprise Mode)")

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
def clean(t):
    return t.replace("", "\n").replace("•", "\n")

# =========================
# EXTRACT FROM TEXT (SMART REGEX CORE)
# =========================
def extract_all(text):

    text = clean(text).lower()

    data = {
        "drugs": [],
        "dose": [],
        "mrd": "",
        "dob": "",
        "patient_id": "",
        "gender": "",
        "age": "",
        "country": "",
        "aes": []
    }

    # ================= DRUG =================
    drugs = re.findall(r"entresto\s*\d+\s*mg", text)
    if drugs:
        data["drugs"] = list(set(drugs))

    # ================= DOSE =================
    doses = re.findall(r"\d+\s*mg", text)
    if doses:
        data["dose"] = list(set(doses))

    # ================= MRD =================
    mrd = re.search(r"\d{1,2}-[a-z]{3}-\d{2,4}", text)
    if mrd:
        data["mrd"] = mrd.group()

    # ================= DOB =================
    dob = re.search(r"\d{1,2}-[a-z]{3}-\d{2,4}", text)
    if dob:
        data["dob"] = dob.group()

    # ================= PATIENT ID =================
    pid = re.search(r"\d{4}-\d{4}-\d{4}-\d{6}", text)
    if pid:
        data["patient_id"] = pid.group()

    # ================= GENDER =================
    if "male" in text:
        data["gender"] = "male"
    elif "female" in text:
        data["gender"] = "female"

    # ================= AGE =================
    age = re.search(r"\d+\s*years", text)
    if age:
        data["age"] = age.group()

    # ================= COUNTRY =================
    if "egypt" in text:
        data["country"] = "egypt"

    # ================= AE DETECTION =================
    ae_keywords = ["non compliance", "stopping", "off-label", "off label", "adverse event"]
    for k in ae_keywords:
        if k in text:
            data["aes"].append(k)

    return data

# =========================
# COMPARE (REAL LOGIC)
# =========================
def compare(qc, agent):

    results = []

    # DRUG mismatch
    if set(qc["drugs"]) != set(agent["drugs"]):
        results.append(("DRUG", qc["drugs"], agent["drugs"]))

    # DOSE mismatch
    if set(qc["dose"]) != set(agent["dose"]):
        results.append(("DOSE", qc["dose"], agent["dose"]))

    # MRD mismatch
    if qc["mrd"] != agent["mrd"]:
        results.append(("MRD", qc["mrd"], agent["mrd"]))

    # DOB mismatch
    if qc["dob"] != agent["dob"]:
        results.append(("DOB", qc["dob"], agent["dob"]))

    # PATIENT ID
    if qc["patient_id"] != agent["patient_id"]:
        results.append(("PATIENT ID", qc["patient_id"], agent["patient_id"]))

    # GENDER
    if qc["gender"] != agent["gender"]:
        results.append(("GENDER", qc["gender"], agent["gender"]))

    # AGE
    if qc["age"] != agent["age"]:
        results.append(("AGE", qc["age"], agent["age"]))

    # COUNTRY
    if qc["country"] != agent["country"]:
        results.append(("COUNTRY", qc["country"], agent["country"]))

    # AE comparison
    if set(qc["aes"]) != set(agent["aes"]):
        results.append(("ADVERSE EVENTS", qc["aes"], agent["aes"]))

    return results

# =========================
# UI
# =========================
qc_file = st.file_uploader("Upload QC PDF", type=["pdf"])
agent_file = st.file_uploader("Upload Agent PDF", type=["pdf"])

if qc_file and agent_file:

    qc_text = read_pdf(qc_file)
    agent_text = read_pdf(agent_file)

    qc_data = extract_all(qc_text)
    agent_data = extract_all(agent_text)

    if st.button("Run QC Check"):

        results = compare(qc_data, agent_data)

        st.subheader("Mismatch Report")

        if not results:
            st.success("No discrepancies detected")
        else:
            for field, qc_val, ag_val in results:

                st.markdown(f"""
### {field}

QC: **{qc_val}**  
Agent: **{ag_val}**

---
""")
