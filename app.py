import streamlit as st
import pdfplumber
import re

st.set_page_config(page_title="PV QC Comparator", layout="wide")
st.title("Pharmacovigilance QC vs Agent Comparator (Clean Mode)")

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
# CLEAN TEXT (CRITICAL FIX)
# =========================
def clean(text):

    text = text.lower()

    # remove bullets & weird chars
    text = text.replace("", " ")
    text = text.replace("•", " ")
    text = text.replace("\uf0b7", " ")

    # normalize spaces
    text = re.sub(r"\s+", " ", text)

    return text

# =========================
# SECTION SPLITTER (KEY FIX)
# =========================
SECTION_KEYS = {
    "product": ["product information", "products"],
    "ae": ["adverse event"],
    "patient": ["patient information", "patient details"],
    "contact": ["contact information"]
}

def split_sections(text):

    sections = {}
    current = "general"
    sections[current] = ""

    for line in text.split("\n"):

        line_low = line.lower()

        found = False
        for sec, keys in SECTION_KEYS.items():
            if any(k in line_low for k in keys):
                current = sec
                sections.setdefault(current, "")
                found = True
                break

        sections[current] += " " + line_low

    return sections

# =========================
# FIELD EXTRACTION (SAFE)
# =========================
def extract_field(section_text, patterns):

    values = []

    for p in patterns:
        matches = re.findall(p, section_text)
        values.extend(matches)

    return list(set([v.strip() for v in values if v]))

# =========================
# PARSER (FIXED LOGIC)
# =========================
def parse(text):

    text = clean(text)
    sections = split_sections(text)

    data = {
        "drug": [],
        "dose": [],
        "frequency": [],
        "mrd": [],
        "dob": [],
        "patient_id": [],
        "gender": [],
        "age": [],
        "country": [],
        "ae": []
    }

    product_text = sections.get("product", "")
    patient_text = sections.get("patient", "")
    contact_text = sections.get("contact", "")
    ae_text = sections.get("ae", "")

    # ================= DRUG =================
    data["drug"] = re.findall(r"entresto\s*\d+\s*mg", product_text)

    # ================= DOSE =================
    data["dose"] = re.findall(r"\d+\s*mg", product_text + " " + ae_text)

    # ================= FREQUENCY =================
    if "once" in product_text:
        data["frequency"].append("once daily")
    if "twice" in product_text:
        data["frequency"].append("twice daily")

    # ================= MRD (STRICT FROM CONTACT ONLY) =================
    mrd = re.findall(r"\d{1,2}-[a-z]{3}-\d{2,4}", contact_text)
    data["mrd"] = mrd

    # ================= DOB (STRICT FROM PATIENT ONLY) =================
    dob = re.findall(r"\d{1,2}-[a-z]{3}-\d{2,4}", patient_text)
    data["dob"] = dob

    # ================= PATIENT ID =================
    pid = re.findall(r"\d{4}-\d{4}-\d{4}-\d{6}", patient_text)
    data["patient_id"] = pid

    # ================= AGE =================
    age = re.findall(r"\d+\s*years", patient_text)
    data["age"] = age

    # ================= GENDER =================
    if "male" in patient_text:
        data["gender"].append("male")
    if "female" in patient_text:
        data["gender"].append("female")

    # ================= COUNTRY =================
    if "egypt" in contact_text:
        data["country"].append("egypt")

    # ================= AE =================
    ae_map = ["non compliance", "stopping", "off-label"]
    for a in ae_map:
        if a in ae_text:
            data["ae"].append(a)

    # CLEAN FINAL
    for k in data:
        data[k] = list(set([x.strip() for x in data[k] if x]))

    return data

# =========================
# COMPARE
# =========================
def compare(qc, ag):

    results = []

    keys = set(qc.keys()).union(set(ag.keys()))

    for k in keys:

        qc_v = set(qc.get(k, []))
        ag_v = set(ag.get(k, []))

        qc_v.discard("")
        ag_v.discard("")

        if qc_v != ag_v:
            results.append({
                "field": k.upper(),
                "qc": sorted(list(qc_v)),
                "agent": sorted(list(ag_v))
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

    qc = parse(qc_text)
    ag = parse(ag_text)

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
