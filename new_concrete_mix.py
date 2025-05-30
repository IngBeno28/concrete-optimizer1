# Streamlit App: ACI-Compliant Concrete Mix Design Optimizer
import streamlit as st
import pandas as pd
from io import BytesIO
import matplotlib.pyplot as plt
from fpdf import FPDF
import os

# --- Modern Streamlit Config ---
st.set_page_config(
    page_title="ACI Concrete Mix Designer",
    page_icon="🧱",
    layout="wide",
    initial_sidebar_state="expanded"
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

# --- ACI Constants ---
ACI_WATER_CONTENT = {
    "Non-Air-Entrained": {10: 205, 20: 185, 40: 160},
    "Air-Entrained": {10: 180, 20: 160, 40: 140}
}

# Adjusted CA volumes based on Fineness Modulus (FM)
ACI_CA_VOLUME = {
    2.4: {10: 0.44, 20: 0.60, 40: 0.68},
    2.6: {10: 0.47, 20: 0.64, 40: 0.72},
    2.8: {10: 0.50, 20: 0.68, 40: 0.76},
    3.0: {10: 0.53, 20: 0.72, 40: 0.80}
}

ACI_EXPOSURE = {
    "Mild": {"max_wcm": 0.55, "min_cement": 250},
    "Moderate": {"max_wcm": 0.50, "min_cement": 300},
    "Severe": {"max_wcm": 0.45, "min_cement": 335}
}

# --- App UI ---
st.title("🧱 ACI 211.1 Concrete Mix Designer")
st.markdown("""
<div style='text-align: center;'>
    <h3 style='color: #007FFF;'>
        ACI-COMPLIANT MIX DESIGN WITH DURABILITY CONTROLS
    </h3>
</div>
""", unsafe_allow_html=True)

# --- Enhanced Input Section ---
with st.expander("📋 ACI Design Parameters", expanded=True):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        fck = st.number_input("🧪 Target strength (MPa)", 10.0, 80.0, 25.0)
        exposure = st.selectbox("🏗️ Exposure Class", list(ACI_EXPOSURE.keys()))
        max_agg_size = st.selectbox("📏 Max Aggregate Size (mm)", [10, 20, 40])
        
    with col2:
        slump = st.slider("📐 Slump (mm)", 25, 200, 75)
        air_entrained = st.checkbox("💨 Air-Entrained Concrete", False)
        target_air = st.slider("🎯 Target Air Content (%)", 1.0, 8.0, 5.0) if air_entrained else 0.0
        fa_fineness = st.slider("📊 Fine Aggregate Fineness Modulus", 2.4, 3.0, 2.7, 0.1)
        
    with col3:
        w_c_ratio = st.number_input("💧 Water/Cement Ratio", 0.3, 0.7, 0.5, 0.01,
                                  help=f"Max {ACI_EXPOSURE[exposure]['max_wcm']} for {exposure} exposure")
        admixture_pct = st.number_input("⚗️ Admixture (%)", 0.0, 10.0, 0.0, 0.1,
                                      help="Water reducer dosage (0.5-2% typical)")
        fa_moisture = st.number_input("💦 FA Moisture (%)", 0.0, 10.0, 2.0)
        ca_moisture = st.number_input("💧 CA Moisture (%)", 0.0, 10.0, 1.0)

# --- Cached Calculation Function ---
@st.cache_data(ttl=3600)
def calculate_aci_mix(params):
    # Validate w/cm ratio against exposure
    if params["w_c_ratio"] > ACI_EXPOSURE[params["exposure"]]["max_wcm"]:
        st.warning(f"⚠️ w/cm exceeds {ACI_EXPOSURE[params['exposure']]['max_wcm']} for {params['exposure']} exposure")
    
    # 1. Water Content (ACI Table 6.3.3)
    water_key = "Air-Entrained" if params["air_entrained"] else "Non-Air-Entrained"
    water = ACI_WATER_CONTENT[water_key][params["max_agg_size"]]
    
    # Adjust for slump (simplified linear adjustment)
    water += (params["slump"] - 75) * 0.3
    
    # Apply water reduction from admixture (if any)
    if params["admixture_pct"] > 0:
        water_reduction = min(0.15, params["admixture_pct"] * 0.05)  # Max 15% reduction
        water *= (1 - water_reduction)
        st.info(f"🔹 Water reduced by {water_reduction*100:.1f}% due to admixture")
    
    # 2. Cement Content (with min. cement check)
    cement = max(water / params["w_c_ratio"], ACI_EXPOSURE[params["exposure"]]["min_cement"])
    
    # 3. Coarse Aggregate (ACI Table 6.3.6 with FM adjustment)
    ca_volume = ACI_CA_VOLUME[params["fa_fineness"]][params["max_agg_size"]]
    ca_mass = ca_volume * 1600  # Assuming rodded density of 1600 kg/m³
    
    # 4. Fine Aggregate (Absolute Volume Method)
    cement_vol = cement / (3.15 * 1000)
    water_vol = water / 1000
    air_vol = params["target_air"] / 100 if params["air_entrained"] else 0.01
    ca_vol = ca_mass / (2.65 * 1000)  # Assuming SG=2.65
    
    fa_vol = 1 - (cement_vol + water_vol + air_vol + ca_vol)
    fa_mass = fa_vol * 2.65 * 1000
    
    # 5. Moisture Corrections
    fa_mass *= (1 + params["fa_moisture"] / 100)
    ca_mass *= (1 + params["ca_moisture"] / 100)
    water -= (fa_mass * (params["fa_moisture"] / 100) + 
              ca_mass * (params["ca_moisture"] / 100))
    
    return {
        'Water (kg/m³)': round(water, 1),
        'Cement (kg/m³)': round(cement, 1),
        'Fine Aggregate (kg/m³)': round(fa_mass, 1),
        'Coarse Aggregate (kg/m³)': round(ca_mass, 1),
        'Air Content (%)': round(params["target_air"], 1),
        'Admixture (kg/m³)': round(cement * params["admixture_pct"] / 100, 2)
    }

# --- Main Logic ---
if st.button("🔍 Calculate ACI Mix", type="primary"):
    input_params = {
        "exposure": exposure,
        "max_agg_size": max_agg_size,
        "slump": slump,
        "air_entrained": air_entrained,
        "target_air": target_air,
        "fa_fineness": fa_fineness,
        "w_c_ratio": w_c_ratio,
        "admixture_pct": admixture_pct,
        "fa_moisture": fa_moisture,
        "ca_moisture": ca_moisture
    }
    
    try:
        result = calculate_aci_mix(input_params)
        st.session_state.result = result
        st.success("✅ ACI Calculation Complete!")
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")

# --- Results Display ---
if 'result' in st.session_state:
    st.header("📊 ACI Mix Proportions")
    df = pd.DataFrame.from_dict(st.session_state.result, orient='index', columns=['Value'])
    st.dataframe(df.style.format("{:.1f}"), use_container_width=True)
    
    # --- Pie Chart (excludes air and admixture) ---
    st.subheader("Mass Distribution (kg/m³)")
    fig, ax = plt.subplots()
    components = {k: v for k, v in st.session_state.result.items() 
                 if "kg/m³" in k and "Admixture" not in k}
    ax.pie(
        components.values(),
        labels=[k.split(" (")[0] for k in components.keys()],
        autopct='%1.1f%%',
        colors=['#66b3ff','#99ff99','#ffcc99','#c2c2f0']
    )
    st.pyplot(fig)
    
    # --- Export ---
    st.download_button(
        "⬇️ Download CSV",
        df.to_csv(),
        "aci_mix_design.csv",
        "text/csv"
    )

# --- Footer ---
st.markdown("---")
st.caption("© 2025 ACI 211.1 Mix Designer | Compliant with ACI 318-19")
