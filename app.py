import streamlit as st
import pdfplumber
import re

st.set_page_config(page_title="PV QC System", layout="wide")
st.title("Pharmacovigilance QC System")
st.markdown("QC vs Agent — full discrepancy detection engine")

# =========================
# PDF READER
# =========================
def read_pdf(file):
    text = []
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text.append(t)
    return "\n".join(text)

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
def is_noise(x):
    x = x.lower().strip()
    return (
        x == "" or
        "click or tap" in x or
        "choose an item" in x or
        "enter text" in x
    )

# =========================
# LABEL MAP (PHARMA CORE)
# =========================
LABELS = {
    "drug": ["product name", "drug"],
    "dose": ["dose"],
    "indication": ["indication"],
    "mrd": ["date reported", "mrd"],
    "patient_id": ["patient id"],
    "dob": ["date of birth"],
    "age": ["age"],
    "gender": ["gender"],
    "country": ["country"]
}

# =========================
# SPLIT LINES
# =========================
def get_lines(text):
    text = clean(text)
    lines = [re.sub(r"\s+", " ", l.strip()) for l in text.split("\n")]
    return [l for l in lines if l]

# =========================
# EXTRACT VALUE BLOCK
# =========================
def get_value_block(lines, start, end):
    values = []

    for i in range(start + 1, end):
        if is_noise(lines[i]):
            continue
        if any(lbl in lines[i].lower() for lbls in LABELS.values() for lbl in lbls):
            break
        values.append(lines[i])

    return " ".join(values).strip()

# =========================
# MAIN PARSER (SECTION BASED)
# =========================
def extract_fields(text):

    lines = get_lines(text)

    fields = {
        "drug": "",
        "dose": "",
        "indication": "",
        "mrd": "",
        "patient_id": "",
        "dob": "",
        "age": "",
        "gender": "",
        "country": ""
    }

    label_positions = []

    def is_label(line):
        l = line.lower()
        return any(any(k in l for k in v) for v in LABELS.values())

    for i, line in enumerate(lines):
        if is_label(line):
            label_positions.append(i)

    label_positions.append(len(lines))

    for i in range(len(label_positions) - 1):

        start = label_positions[i]
        end = label_positions[i + 1]

        label_line = lines[start].lower()
        value = get_value_block(lines, start, end)

        # assign fields
        if any(x in label_line for x in LABELS["drug"]):
            fields["drug"] = value

        elif any(x in label_line for x in LABELS["dose"]):
            fields["dose"] = value

        elif any(x in label_line for x in LABELS["indication"]):
            fields["indication"] = value

        elif any(x in label_line for x in LABELS["mrd"]):
            fields["mrd"] = value

        elif any(x in label_line for x in LABELS["patient_id"]):
            fields["patient_id"] = value

        elif any(x in label_line for x in LABELS["dob"]):
            fields["dob"] = value

        elif any(x in label_line for x in LABELS["age"]):
            fields["age"] = value

        elif any(x in label_line for x in LABELS["gender"]):
            fields["gender"] = value

        elif any(x in label_line for x in LABELS["country"]):
            fields["country"] = value

    return {k: v.lower().strip() for k, v in fields.items() if v}

# =========================
# COMPARE ENGINE (STRICT)
# =========================
def compare(qc, agent):

    results = []

    all_keys = set(qc.keys()).union(set(agent.keys()))

    for k in all_keys:

        qc_val = qc.get(k, "MISSING")
        ag_val = agent.get(k, "MISSING")

        if qc_val != ag_val:

            results.append({
                "field": k.upper(),
                "qc": qc_val,
                "agent": ag_val
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
            st.success("No discrepancies detected")
        else:
            for r in results:
                st.markdown(f"""
### {r['field']}

QC: **{r['qc']}**  
Agent: **{r['agent']}**

---
""")
