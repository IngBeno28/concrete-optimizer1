# Streamlit App: Concrete Mix Design Optimizer
import streamlit as st
import pandas as pd
from io import BytesIO
import matplotlib.pyplot as plt
from fpdf import FPDF
import os
import sys

# --- Modern Streamlit Config ---
st.set_page_config(
    page_title="Concrete Mix Optimizer",
    page_icon="🧱",
    layout="wide",
    initial_sidebar_state="auto"
)

# --- Theme Config (Auto-generated if missing) ---
if not os.path.exists('.streamlit'):
    os.makedirs('.streamlit')

if not os.path.exists('.streamlit/config.toml'):
    with open('.streamlit/config.toml', 'w') as f:
        f.write("""
[theme]
primaryColor = "#1a5276"
backgroundColor = "#f5f5f5"
secondaryBackgroundColor = "#e8f4f8"
textColor = "#212121"
font = "sans serif"
""")

# --- Cache Management ---
if st.sidebar.button("🔄 Clear ALL Cache"):
    st.cache_data.clear()
    st.success("Cache cleared! Refreshing...")
    st.rerun()

# --- App UI ---
st.title("🧱 Concrete Mix Design Optimizer")
st.markdown("""
<div style='text-align: center; padding: 10px;'>
    <h3 style='font-family: Arial, sans-serif; color: #007FFF;'>
        UPLOAD LAB RESULTS OR ENTER DESIGN INPUTS
    </h3>
</div>
""", unsafe_allow_html=True)

# --- Data Upload ---
uploaded_file = st.sidebar.file_uploader("📂 Upload CSV/Excel", type=["csv", "xlsx"])
if uploaded_file:
    try:
        df_uploaded = pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file)
        st.subheader("📄 Uploaded Data Preview")
        st.dataframe(df_uploaded)
    except Exception as e:
        st.error(f"Error reading file: {str(e)}")

# --- Input Section ---
with st.expander("📋 Design Parameters", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        fck = st.number_input("🧪 Target strength (MPa)", 10.0, 80.0, 25.0)
        slump = st.slider("📏 Slump (mm)", 25, 200, 75)
        use_slump_for_water = st.checkbox("📉 Estimate water from slump", True)
        w_c_ratio = st.number_input("💧 Water/Cement Ratio", 0.3, 0.7, 0.5, 0.01)
        
    with col2:
        admixture_pct = st.number_input("⚗️ Admixture (%)", 0.0, 10.0, 0.0, 0.1)
        fa_ratio = st.number_input("🪨 Fine Agg Ratio", 0.2, 0.6, 0.35, 0.01)
        ca_ratio = st.number_input("🧱 Coarse Agg Ratio", 0.3, 0.8, 0.65, 0.01)

# --- Cached Calculation Function ---
@st.cache_data(ttl=3600)  # Auto-clear after 1 hour
def calculate_mix(input_params):
    class MixDesignCalculator:
        def __init__(self, params):
            self.params = params
        
        def calculate(self):
            water = 185 if not self.params["use_slump"] else max(130, min(210, 130 + (self.params["slump"] - 25) * 0.8))
            cement = water / self.params["w_c_ratio"]
            admixture = cement * self.params["admixture_pct"] / 100
            return {
                'Water': round(water, 1),
                'Cement': round(cement, 1),
                'Admixture': round(admixture, 1)
            }
    
    return MixDesignCalculator(input_params).calculate()

# --- Main Logic ---
if st.button("🔍 Calculate", type="primary"):
    input_params = {
        "use_slump": use_slump_for_water,
        "slump": slump,
        "w_c_ratio": w_c_ratio,
        "admixture_pct": admixture_pct,
        "fa_ratio": fa_ratio,
        "ca_ratio": ca_ratio
    }
    
    try:
        result = calculate_mix(input_params)
        st.session_state.result = result
        st.success("✅ Calculation complete!")
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")

# --- Results Display ---
if 'result' in st.session_state:
    st.header("📊 Results")
    df = pd.DataFrame.from_dict(st.session_state.result, orient='index', columns=['kg/m³'])
    st.dataframe(df, use_container_width=True)
    
    # Export Buttons
    excel_data = BytesIO()
    df.to_excel(excel_data, index=True)
    st.download_button("⬇️ Download Excel", excel_data, "mix_design.xlsx")
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Concrete Mix Design Report", ln=1, align='C')
    for k, v in st.session_state.result.items():
        pdf.cell(200, 10, txt=f"{k}: {v} kg/m³", ln=1)
    st.download_button("⬇️ Download PDF", pdf.output(dest='S').encode('latin-1'), "mix_report.pdf")

# --- Footer ---
st.markdown("---")
st.caption("© 2025 Concrete Mix Optimizer | Powered By Automation_Hub")
