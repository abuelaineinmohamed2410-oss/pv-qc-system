import streamlit as st
import pdfplumber
import re
from collections import defaultdict

st.set_page_config(page_title="PV QC System", layout="wide")
st.title("Pharmacovigilance QC System (Structured Engine)")

# =========================
# PDF READ
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
# NORMALIZATION (CRITICAL FIX)
# =========================
def norm(x):
    x = x.lower()
    x = x.replace("  ", " ")
    x = x.replace("mg", " mg")
    x = re.sub(r"\s+", " ", x)
    return x.strip()

# =========================
# EXTRACT PRODUCTS (BLOCK BASED)
# =========================
def extract_products(text):

    products = []

    blocks = re.split(r"the products|product information", text)

    for block in blocks:

        drugs = re.findall(r"entresto\s*\d+\s*mg", block)
        doses = re.findall(r"\d+\s*mg", block)

        for d in drugs:
            product = {
                "drug": norm(d),
                "dose": []
            }

            # attach doses near drug (context-based)
            for dose in doses:
                product["dose"].append(norm(dose))

            products.append(product)

    return products

# =========================
# EXTRACT AES (STRUCTURED)
# =========================
def extract_aes(text):

    aes = []

    patterns = [
        "non compliance",
        "stopping",
        "off-label",
        "off label",
        "adverse event"
    ]

    for p in patterns:
        if p in text:
            aes.append(p)

    return sorted(set(aes))

# =========================
# EXTRACT FULL CASE
# =========================
def extract_case(text):

    return {
        "products": extract_products(text),
        "aes": extract_aes(text)
    }

# =========================
# COMPARE PRODUCTS PROPERLY
# =========================
def compare_products(qc_products, ag_products):

    results = []

    qc_set = {(p["drug"], tuple(sorted(p["dose"]))) for p in qc_products}
    ag_set = {(p["drug"], tuple(sorted(p["dose"]))) for p in ag_products}

    if qc_set != ag_set:
        results.append({
            "field": "PRODUCTS",
            "qc": list(qc_set),
            "agent": list(ag_set)
        })

    return results

# =========================
# COMPARE AES
# =========================
def compare_aes(qc_aes, ag_aes):

    if set(qc_aes) != set(ag_aes):
        return [{
            "field": "ADVERSE EVENTS",
            "qc": qc_aes,
            "agent": ag_aes
        }]
    return []

# =========================
# FULL COMPARE
# =========================
def compare(qc, ag):

    results = []
    results += compare_products(qc["products"], ag["products"])
    results += compare_aes(qc["aes"], ag["aes"])

    return results

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
