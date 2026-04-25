```python
import streamlit as st
import pdfplumber
import re
import time

# =========================
# PAGE CONFIG (MUST BE FIRST)
# =========================
st.set_page_config(page_title="PV QC System", layout="wide")

# =========================
# PAGE STYLE (PROFESSIONAL UI)
# =========================
st.markdown("""
    <style>
        body {
            background-color: #f5f7fa;
        }

        .stButton button {
            background-color: #0b5ed7;
            color: white;
            border-radius: 6px;
            height: 40px;
            width: 100%;
            font-weight: 500;
        }

        .stButton button:hover {
            background-color: #084298;
            color: white;
        }

        .stMetric {
            background-color: white;
            padding: 15px;
            border-radius: 8px;
            border: 1px solid #e6e6e6;
        }

        h1, h2, h3 {
            color: #1f2d3d;
        }
    </style>
""", unsafe_allow_html=True)

# =========================
# SESSION STATE INIT
# =========================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "cases_uploaded" not in st.session_state:
    st.session_state.cases_uploaded = 0
if "cases_with_errors" not in st.session_state:
    st.session_state.cases_with_errors = 0
if "start_time" not in st.session_state:
    st.session_state.start_time = None
if "total_time" not in st.session_state:
    st.session_state.total_time = 0

# =========================
# LOGIN SYSTEM
# =========================
def login():
    st.title("User Authentication")
    st.caption("Enter your credentials to access the system")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username == "admin" and password == "1234":
            st.session_state.logged_in = True
            st.session_state.username = username
            st.success("Login successful")
        else:
            st.error("Invalid username or password")

if not st.session_state.logged_in:
    login()
    st.stop()

# =========================
# PAGE HEADER
# =========================
st.title("Pharmacovigilance QC System")
st.caption("Case Quality Check and Discrepancy Detection Tool")

st.markdown(f"**User:** {st.session_state.username}")

# =========================
# TIMER CONTROLS
# =========================
col1, col2 = st.columns(2)

with col1:
    if st.button("Start Case"):
        st.session_state.start_time = time.time()
        st.success("Case tracking started")

with col2:
    if st.button("Finish Case"):
        if st.session_state.start_time:
            duration = time.time() - st.session_state.start_time
            st.session_state.total_time += duration
            st.session_state.start_time = None
            st.info(f"Case completed in {round(duration,2)} seconds")
        else:
            st.warning("Start tracking before finishing")

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
    text = text.lower()
    text = text.replace("", " ")
    text = text.replace("•", " ")
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text

# =========================
# NOISE FILTER
# =========================
def is_noise(v):
    return any(x in v for x in [
        "click or tap",
        "choose an item",
        "enter text",
        "na",
        "not reported",
        "unknown / not reported"
    ])

# =========================
# SAFE FIELD EXTRACTION
# =========================
def extract_field(text, patterns):
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            val = m.group(1).strip()

            if is_noise(val):
                continue

            if len(val) > 120:
                continue

            return val
    return ""

# =========================
# EXTRACTION ENGINE
# =========================
def extract(text):

    text = clean(text)
    data = {}

    drug = re.search(r"entresto\s*\d+\s*mg", text)
    data["drug"] = drug.group(0) if drug else ""

    data["dose"] = extract_field(text, [
        r"dose[:\s]*([0-9]+\s*mg)",
        r"(\d+\s*mg)"
    ])

    data["frequency"] = extract_field(text, [
        r"frequency[:\s]*([a-z\s,/()]+)",
        r"(once daily|twice daily|three times daily|other[^\.]*)"
    ])

    data["indication"] = extract_field(text, [
        r"indication[:\s]*([a-z\s]+)"
    ])

    data["Action Taken Due to Side Effect"] = extract_field(text, [
        r"Action Taken Due to Side Effect[:\s]*([a-z\s]+)"
    ])

    mrd = re.search(r"\d{1,2}-[a-z]{3}-\d{2,4}", text)
    data["mrd"] = mrd.group(0) if mrd else ""

    dob = re.search(r"date of birth[:\s]*([0-9a-z/-]+)", text)
    data["dob"] = dob.group(1) if dob else ""

    age = re.search(r"(\d{1,3})\s*years", text)
    data["age"] = age.group(1) if age else ""

    gender = re.search(r"\b(male|female)\b", text)
    data["gender"] = gender.group(1) if gender else ""

    pid = re.search(r"\d{4,}-\d{2,}-\d{2,}-\d+", text)
    data["patient_id"] = pid.group(0) if pid else ""

    country = re.search(r"\b(egypt|germany|china|austria)\b", text)
    data["country"] = country.group(0) if country else ""

    return data

# =========================
# NORMALIZE
# =========================
def norm(x):
    return re.sub(r"\s+", " ", x.strip().lower())

# =========================
# COMPARE ENGINE
# =========================
def compare(qc, agent):
    diffs = []
    keys = set(qc.keys()).union(agent.keys())

    for k in keys:
        q = norm(qc.get(k, ""))
        a = norm(agent.get(k, ""))

        if q != a:
            diffs.append({
                "field": k.upper(),
                "qc": q,
                "agent": a
            })

    return diffs

# =========================
# FILE UPLOAD
# =========================
qc_file = st.file_uploader("Upload QC PDF", type=["pdf"])
agent_file = st.file_uploader("Upload Agent PDF", type=["pdf"])

if qc_file and agent_file:

    qc_text = read_pdf(qc_file)
    agent_text = read_pdf(agent_file)

    qc_data = extract(qc_text)
    agent_data = extract(agent_text)

    if st.button("Run QC Validation"):

        st.session_state.cases_uploaded += 1

        diffs = compare(qc_data, agent_data)

        st.subheader("Detected Discrepancies")

        if not diffs:
            st.success("No discrepancies detected")
        else:
            st.session_state.cases_with_errors += 1

            for d in diffs:
                st.markdown(f"""
### {d['field']}
- QC: `{d['qc']}`
- Agent: `{d['agent']}`
---
""")

# =========================
# METRICS DASHBOARD
# =========================
st.divider()
st.subheader("Performance Metrics")

col1, col2, col3 = st.columns(3)

total = st.session_state.cases_uploaded
errors = st.session_state.cases_with_errors

accuracy = ((total - errors) / total * 100) if total > 0 else 0

with col1:
    st.metric("Total Cases", total)

with col2:
    st.metric("Cases with Errors", errors)

with col3:
    st.metric("Accuracy (%)", f"{round(accuracy,2)}")

# =========================
# TIME METRIC
# =========================
if total > 0:
    avg_time = st.session_state.total_time / total
    st.info(f"Average Handling Time: {round(avg_time,2)} seconds")
```
