# Streamlit App: Concrete Mix Design Optimizer
import streamlit as st
import pandas as pd
from io import BytesIO
import matplotlib.pyplot as plt
from fpdf import FPDF
import os

# --- Modern Streamlit Config ---
st.set_page_config(
    page_title="Concrete Mix Optimizer",
    page_icon="🧱",
    layout="wide",
    initial_sidebar_state="auto"
)

# --- Theme Config ---
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
<div style='text-align: center;'>
    <h3 style='color: #007FFF;'>
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

# --- Enhanced Input Section ---
with st.expander("📋 Design Parameters", expanded=True):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        fck = st.number_input("🧪 Target strength (MPa)", 10.0, 80.0, 25.0)
        slump = st.slider("📏 Slump (mm)", 25, 200, 75)
        use_slump_for_water = st.checkbox("📉 Estimate water from slump", True)
        
    with col2:
        w_c_ratio = st.number_input("💧 Water/Cement Ratio", 0.3, 0.7, 0.5, 0.01)
        cement_sg = st.number_input("🏗️ Cement S.G.", 2.5, 3.5, 3.15, 0.01)
        water_sg = st.number_input("💦 Water S.G.", 0.9, 1.1, 1.0, 0.01)
        
    with col3:
        admixture_pct = st.number_input("⚗️ Admixture (%)", 0.0, 10.0, 0.0, 0.1)
        fa_sg = st.number_input("🪨 Fine Agg S.G.", 2.4, 2.8, 2.65, 0.01)
        ca_sg = st.number_input("🧱 Coarse Agg S.G.", 2.4, 2.8, 2.65, 0.01)

# --- Cached Calculation Function ---
@st.cache_data(ttl=3600)
def calculate_mix(input_params):
    class MixDesignCalculator:
        def __init__(self, params):
            self.params = params
        
        def calculate(self):
            # Water calculation
            water = 185 if not self.params["use_slump"] else max(130, min(210, 130 + (self.params["slump"] - 25) * 0.8))
            
            # Cement calculation
            cement = water / self.params["w_c_ratio"]
            
            # Admixture calculation
            admixture = cement * self.params["admixture_pct"] / 100
            
            # Aggregate volumes (using S.G. inputs)
            cement_vol = cement / (self.params["cement_sg"] * 1000)
            water_vol = water / (self.params["water_sg"] * 1000)
            total_agg_vol = 1 - (cement_vol + water_vol)
            
            # Aggregate masses
            fa_mass = total_agg_vol * 0.35 * self.params["fa_sg"] * 1000  # 35% fine aggregate
            ca_mass = total_agg_vol * 0.65 * self.params["ca_sg"] * 1000  # 65% coarse aggregate
            
            return {
                'Water': round(water, 1),
                'Cement': round(cement, 1),
                'Fine Aggregate': round(fa_mass, 1),
                'Coarse Aggregate': round(ca_mass, 1),
                'Admixture': round(admixture, 1)
            }
    
    return MixDesignCalculator(input_params).calculate()

# --- Main Logic ---
if st.button("🔍 Calculate", type="primary"):
    input_params = {
        "use_slump": use_slump_for_water,
        "slump": slump,
        "w_c_ratio": w_c_ratio,
        "cement_sg": cement_sg,
        "water_sg": water_sg,
        "admixture_pct": admixture_pct,
        "fa_sg": fa_sg,
        "ca_sg": ca_sg
    }
    
    try:
        result = calculate_mix(input_params)
        st.session_state.result = result
        st.success("✅ Calculation complete!")
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")

# --- Enhanced Results Display ---
if 'result' in st.session_state:
    st.header("📊 Results")
    df = pd.DataFrame.from_dict(st.session_state.result, orient='index', columns=['kg/m³'])
    st.dataframe(df.style.format("{:.1f}"), use_container_width=True)
    
    # --- Pie Chart Visualization ---
    st.subheader("Mix Proportion Visualization")
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.pie(
        st.session_state.result.values(),
        labels=st.session_state.result.keys(),
        autopct='%1.1f%%',
        startangle=90,
        colors=['#66b3ff','#99ff99','#ffcc99','#c2c2f0','#ff9999']
    )
    ax.axis('equal')  # Equal aspect ratio ensures pie is circular
    st.pyplot(fig)
    
    # --- Export Buttons ---
    col1, col2 = st.columns(2)
    
    with col1:
        excel_data = BytesIO()
        df.to_excel(excel_data)
        st.download_button(
            "⬇️ Download Excel",
            excel_data,
            "mix_design.xlsx",
            help="Export to Excel spreadsheet"
        )
    
    with col2:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="Concrete Mix Design Report", ln=1, align='C')
        for k, v in st.session_state.result.items():
            pdf.cell(200, 10, txt=f"{k}: {v} kg/m³", ln=1)
        st.download_button(
            "⬇️ Download PDF",
            pdf.output(dest='S').encode('latin-1'),
            "mix_report.pdf",
            help="Generate printable PDF report"
        )

# --- Footer ---
st.markdown("---")
st.caption("© 2025 Concrete Mix Optimizer | v2.1")
