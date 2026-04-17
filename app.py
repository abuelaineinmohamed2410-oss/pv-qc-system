import streamlit as st
import pdfplumber
import re

st.set_page_config(page_title="PV QC System", layout="wide")
st.title("Pharmacovigilance QC System")

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
# NORMALIZE
# =========================
def norm(x):
    x = x.lower()
    x = x.replace("mg", " mg")
    x = re.sub(r"\s+", " ", x)
    return x.strip()

# =========================
# SPLIT PRODUCT BLOCKS (CRITICAL FIX)
# =========================
def split_products(text):

    # real separation of repeated sections
    blocks = re.split(r"the products|product information", text)

    return [b for b in blocks if len(b.strip()) > 50]

# =========================
# EXTRACT ONE PRODUCT FROM BLOCK
# =========================
def extract_product(block):

    # drug
    drug_match = re.search(r"entresto\s*\d+\s*mg", block)
    drug = norm(drug_match.group()) if drug_match else ""

    # dose (ONLY from same block)
    doses = re.findall(r"\d+\s*mg", block)
    doses = list(set([norm(d) for d in doses]))

    # frequency (optional but useful)
    freq = ""
    if "once daily" in block:
        freq = "once daily"
    elif "twice daily" in block:
        freq = "twice daily"
    elif "once a day" in block:
        freq = "once daily"
    elif "other" in block:
        freq = "other"

    return {
        "drug": drug,
        "dose": sorted(doses),
        "frequency": freq
    }

# =========================
# FULL PRODUCT PARSER
# =========================
def extract_products(text):

    blocks = split_products(text)

    products = []

    for b in blocks:

        p = extract_product(b)

        if p["drug"]:
            products.append(p)

    return products

# =========================
# AE EXTRACTION (IMPROVED)
# =========================
def extract_aes(text):

    aes = []

    keywords = [
        "non compliance",
        "stopping",
        "off-label",
        "off label",
        "adverse event"
    ]

    for k in keywords:
        if k in text:
            aes.append(k)

    return sorted(set(aes))

# =========================
# EXTRACT CASE
# =========================
def extract_case(text):

    return {
        "products": extract_products(text),
        "aes": extract_aes(text)
    }

# =========================
# COMPARE PRODUCTS (FIXED)
# =========================
def compare_products(qc, ag):

    qc_set = {(p["drug"], tuple(p["dose"]), p["frequency"]) for p in qc}
    ag_set = {(p["drug"], tuple(p["dose"]), p["frequency"]) for p in ag}

    if qc_set != ag_set:
        return [{
            "field": "PRODUCTS",
            "qc": qc_set,
            "agent": ag_set
        }]

    return []

# =========================
# COMPARE AES
# =========================
def compare_aes(qc, ag):

    if set(qc) != set(ag):
        return [{
            "field": "ADVERSE EVENTS",
            "qc": qc,
            "agent": ag
        }]
    return []

# =========================
# COMPARE FULL
# =========================
def compare(qc, ag):

    return compare_products(qc["products"], ag["products"]) + compare_aes(qc["aes"], ag["aes"])

# =========================
# UI
# =========================
qc_file = st.file_uploader("Upload QC PDF", type=["pdf"])
ag_file = st.file_uploader("Upload Agent PDF", type=["pdf"])

if qc_file and ag_file:

    qc_text = read_pdf(qc_file)
    ag_text = read_pdf(ag_file)

    qc = extract_case(qc_text)
    ag = extract_case(ag_text)

    if st.button("Run QC Check"):

        results = compare(qc, ag)

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
