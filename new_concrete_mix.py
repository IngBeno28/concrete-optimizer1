# Streamlit App: Concrete Mix Design Optimizer
import streamlit as st
import pandas as pd
from io import BytesIO
import matplotlib.pyplot as plt
from fpdf import FPDF
import os

# --- Create .streamlit/config.toml if it doesn't exist ---
if not os.path.exists('.streamlit'):
    os.makedirs('.streamlit')

config_content = """
[theme]
# Primary accent color for interactive elements
primaryColor = "#1a5276"

# Background color for the main content area
backgroundColor = "#f5f5f5"

# Background color for sidebar and most interactive widgets
secondaryBackgroundColor = "#e8f4f8"

# Color used for text
textColor = "#212121"

# Font family (can be "sans serif", "serif", "monospace")
font = "sans serif"

[runner]
# Allows you to run the app without the warning about running as root
allowRunOnSave = true

[server]
# Enable XSRF protection for additional security
enableXsrfProtection = true
# Configure the port if needed
port = 8501
"""

if not os.path.exists('.streamlit/config.toml'):
    with open('.streamlit/config.toml', 'w') as f:
        f.write(config_content.strip())

# --- App Config ---
st.set_page_config(
    page_title="Concrete Mix Optimizer", 
    layout="wide",
    page_icon="🧱"
)

# --- Sidebar Layout ---
st.sidebar.title("🧭 Navigation")
st.sidebar.markdown("Navigate app sections and upload data files.")

uploaded_file = st.sidebar.file_uploader("📂 Upload CSV or Excel", type=["csv", "xlsx"])
if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        df_uploaded = pd.read_csv(uploaded_file)
    else:
        df_uploaded = pd.read_excel(uploaded_file)
    st.subheader("📄 Uploaded Data Preview")
    st.dataframe(df_uploaded)

# --- App Title and Description ---
st.title("🧱 Concrete Mix Design Optimizer")
st.markdown("""
Welcome! This app calculates mix proportions for normal concrete using a simplified ACI method. 
You can enter inputs manually or upload test data files.
""")

# --- Inputs Section ---
st.header("1️⃣ Mix Design Parameters")
with st.expander("📋 Design Inputs", expanded=True):
    col1, col2 = st.columns(2)
    
    with col1:
        fck = st.number_input("🧪 Target compressive strength (MPa)", 10.0, 80.0, 25.0)
        slump = st.slider("📏 Slump (mm)", 25, 200, 75)
        use_slump_for_water = st.checkbox("📉 Use slump to estimate water content", value=False)
        w_c_ratio = st.number_input("💧 Water/Cement Ratio", 0.3, 0.7, 0.5, step=0.01)
        cement_sg = st.number_input("🧱 Cement SG", 2.0, 4.0, 3.15, step=0.01)
        water_sg = st.number_input("💦 Water SG", 0.9, 1.1, 1.0, step=0.01)
        
    with col2:
        admixture_pct = st.number_input("⚗️ Admixture (% of cement)", 0.0, 10.0, 0.0, step=0.1)
        fa_ratio = st.number_input("🪨 Fine Aggregate Volume Ratio", 0.2, 0.6, 0.35, step=0.01)
        fa_sg = st.number_input("🧮 Fine Aggregate SG", 2.4, 2.8, 2.65, step=0.01)
        fa_abs = st.number_input("🧂 Fine Aggregate Absorption (%)", 0.0, 5.0, 1.0, step=0.1)
        ca_sg = st.number_input("🪨 Coarse Aggregate SG", 2.4, 2.8, 2.65, step=0.01)
        ca_abs = st.number_input("🧂 Coarse Aggregate Absorption (%)", 0.0, 5.0, 0.5, step=0.1)

    moisture_content = st.number_input("💧 Moisture Content (%)", 0.0, 10.0, 2.0, step=0.1)
    ca_ratio = st.number_input("🧱 Coarse Aggregate Volume Ratio", 0.3, 0.8, 0.65, step=0.01)

# --- PDF Export Function ---
def generate_pdf_report(result):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Concrete Mix Design Report", ln=True, align='C')
    pdf.ln(10)
    for k, v in result.items():
        pdf.cell(200, 10, txt=f"{k}: {v} kg/m³", ln=True)
    return pdf.output(dest="S").encode("latin-1")

# --- Excel Export Function ---
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Mix Design')
    return output.getvalue()

# --- Mix Design Calculator Class ---
class MixDesignCalculator:
    def __init__(self, params):
        self.params = params
        self.result = {}

    def estimate_water_content(self):
        if self.params["use_slump_for_water"]:
            return max(130, min(210, 130 + (self.params["slump"] - 25) * 0.8))
        return 185

    def calculate_cement_content(self, water_content):
        return water_content / self.params["w_c_ratio"]

    def calculate_admixture_dose(self, cement_content):
        return cement_content * self.params["admixture_pct"] / 100

    def calculate_aggregate_volumes(self, cement, water, admixture):
        cement_vol = cement / (self.params["cement_sg"] * 1000)
        water_vol = water / (self.params["water_sg"] * 1000)
        admixture_vol = admixture / (1.05 * 1000)
        return 1 - (cement_vol + water_vol + admixture_vol)

    def calculate_aggregate_masses(self, total_agg_vol):
        fa_mass_ssd = self.params["fa_ratio"] * total_agg_vol * self.params["fa_sg"] * 1000
        ca_mass_ssd = self.params["ca_ratio"] * total_agg_vol * self.params["ca_sg"] * 1000
        fa_correction = 1 + (self.params["moisture_content"] - self.params["fa_abs"]) / 100
        ca_correction = 1 + (self.params["moisture_content"] - self.params["ca_abs"]) / 100
        fa_mass = fa_mass_ssd * fa_correction
        ca_mass = ca_mass_ssd * ca_correction
        return fa_mass, ca_mass

    def calculate(self):
        water = round(self.estimate_water_content(), 1)
        cement = round(self.calculate_cement_content(water), 1)
        admixture = round(self.calculate_admixture_dose(cement), 1)
        total_agg_vol = self.calculate_aggregate_volumes(cement, water, admixture)
        fa_mass, ca_mass = self.calculate_aggregate_masses(total_agg_vol)
        self.result = {
            'Water': water,
            'Cement': cement,
            'Fine Aggregate': round(fa_mass, 1),
            'Coarse Aggregate': round(ca_mass, 1),
            'Admixture': admixture
        }
        return self.result

# --- Mix Design Button ---
if st.button("🔍 Calculate Mix Design", type="primary"):
    try:
        input_params = {
            "use_slump_for_water": use_slump_for_water,
            "slump": slump,
            "w_c_ratio": w_c_ratio,
            "cement_sg": cement_sg,
            "water_sg": water_sg,
            "admixture_pct": admixture_pct,
            "fa_ratio": fa_ratio,
            "fa_sg": fa_sg,
            "fa_abs": fa_abs,
            "ca_sg": ca_sg,
            "ca_abs": ca_abs,
            "moisture_content": moisture_content,
            "ca_ratio": ca_ratio
        }
        calculator = MixDesignCalculator(input_params)
        result = calculator.calculate()
        st.session_state.result = result
        st.success("✅ Mix design calculated successfully!")
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")

# --- Results and Exports ---
if 'result' in st.session_state:
    result = st.session_state.result
    mix_df = pd.DataFrame({
        'Component': result.keys(),
        'Quantity (kg/m³)': result.values()
    })

    st.header("📊 2️⃣ Calculated Mix Summary")
    st.dataframe(mix_df, use_container_width=True, hide_index=True)

    st.subheader("Mix Proportion Visualization")
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.pie(result.values(), labels=result.keys(), autopct='%1.1f%%', startangle=90)
    ax.axis('equal')
    st.pyplot(fig)

    st.header("📤 3️⃣ Export Report")
    col1 = st.columns()
    
    with col1:
        st.download_button(
            label="⬇️ Download Excel File",
            data=to_excel(mix_df),
            file_name="concrete_mix_design.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


# --- Footer ---
st.markdown("---")
st.caption("© 2025 Concrete Mix Design Optimizer | Built by Automation_hub")
