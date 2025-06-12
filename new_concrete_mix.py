# Streamlit App: ACI-Compliant Concrete Mix Design Optimizer
# --- Import Dependencies ---
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO

# --- Streamlit Config ---
st.set_page_config("ACI Mix Designer Enhanced", layout="wide")

# --- ACI Reference Tables ---
ACI_WATER_CONTENT = {
    "Non-Air-Entrained": {10: 205, 20: 185, 40: 160},
    "Air-Entrained": {10: 180, 20: 160, 40: 140}
}

ACI_CA_VOLUME = {
    2.4: {10: 0.44, 20: 0.60, 40: 0.68},
    2.7: {10: 0.49, 20: 0.66, 40: 0.74},
    3.0: {10: 0.53, 20: 0.72, 40: 0.80}
}

ACI_EXPOSURE = {
    "Mild": {"max_wcm": 0.55, "min_cement": 250},
    "Moderate": {"max_wcm": 0.50, "min_cement": 300},
    "Severe": {"max_wcm": 0.45, "min_cement": 335}
}

# --- Input UI ---
st.title("🧱 Enhanced ACI 211.1 Concrete Mix Designer")

with st.expander("📋 ACI Design Inputs", expanded=True):
    col1, col2, col3 = st.columns(3)

    with col1:
        fck = st.number_input("f'c (MPa)", 10.0, 80.0, 25.0)
        std_dev = st.number_input("Standard deviation (MPa)", 3.0, 10.0, 5.0)
        exposure = st.selectbox("Exposure Class", list(ACI_EXPOSURE))

    with col2:
        max_agg_size = st.selectbox("Max Aggregate Size (mm)", [10, 20, 40])
        slump = st.slider("Slump (mm)", 25, 200, 75)
        air_entrained = st.checkbox("Air Entrained", False)
        air_content = st.slider("Target Air Content (%)", 1.0, 8.0, 5.0) if air_entrained else 0.0

    with col3:
        wcm = st.number_input("w/c Ratio", 0.3, 0.7, 0.5)
        admixture = st.number_input("Admixture (%)", 0.0, 5.0, 0.0)
        fm = st.slider("FA Fineness Modulus", 2.4, 3.0, 2.7, step=0.1)

with st.expander("🔬 Material Properties"):
    sg_cement = st.number_input("Cement SG", 2.0, 3.5, 3.15)
    sg_fa = st.number_input("Fine Aggregate SG", 2.4, 2.8, 2.65)
    sg_ca = st.number_input("Coarse Aggregate SG", 2.4, 2.8, 2.65)
    unit_weight_ca = st.number_input("CA Unit Weight (kg/m³)", 1400, 1800, 1600)
    moist_fa = st.number_input("FA Moisture (%)", 0.0, 10.0, 2.0)
    moist_ca = st.number_input("CA Moisture (%)", 0.0, 10.0, 1.0)

# --- Calculation Logic ---
def calculate_mix():
    ft = fck + 1.34 * std_dev
    if wcm > ACI_EXPOSURE[exposure]['max_wcm']:
        st.warning("w/c exceeds max for exposure class")

    water = ACI_WATER_CONTENT["Air-Entrained" if air_entrained else "Non-Air-Entrained"][max_agg_size]
    water += (slump - 75) * 0.3
    if admixture:
        water *= 1 - min(0.15, admixture * 0.05)

    cement = max(water / wcm, ACI_EXPOSURE[exposure]['min_cement'])

    try:
        ca_vol = ACI_CA_VOLUME[round(fm,1)][max_agg_size]
    except:
        ca_vol = ACI_CA_VOLUME[2.7][max_agg_size]

    ca_mass = ca_vol * unit_weight_ca

    cement_vol = cement / (sg_cement * 1000)
    water_vol = water / 1000
    air_vol = air_content / 100 if air_entrained else 0.01
    ca_vol_abs = ca_mass / (sg_ca * 1000)
    fa_vol = 1 - (cement_vol + water_vol + air_vol + ca_vol_abs)
    fa_mass = fa_vol * sg_fa * 1000

    # Moisture correction
    fa_mass_adj = fa_mass * (1 + moist_fa / 100)
    ca_mass_adj = ca_mass * (1 + moist_ca / 100)
    water -= (fa_mass * moist_fa / 100 + ca_mass * moist_ca / 100)

    return {
        "Target Mean Strength f't (MPa)": round(ft,2),
        "Water (kg/m³)": round(water,1),
        "Cement (kg/m³)": round(cement,1),
        "Fine Aggregate (kg/m³)": round(fa_mass_adj,1),
        "Coarse Aggregate (kg/m³)": round(ca_mass_adj,1),
        "Air Content (%)": round(air_content,1),
        "Admixture (kg/m³)": round(cement * admixture / 100,2)
    }

if st.button("🧪 Compute Mix Design"):
    result = calculate_mix()
    st.write("### 📊 Mix Proportions:")
    
    # Responsive table display
    df = pd.DataFrame.from_dict(result, orient='index', columns=['Value'])
    
    # Use columns to make layout responsive
    col_table, col_chart = st.columns([3, 1])  # 2:1 ratio on desktop, stacks on mobile
    
    with col_table:
        st.dataframe(
            df.style.format(precision=2),
            height=min(len(result) * 45 + 50, 400),  # Dynamic height
            use_container_width=True 
        )
    
    with col_chart:
        chart_type = st.radio("📈 Chart Type", ["Pie", "Bar"], horizontal=True)
        
        chart_data = {
            k.split(" (")[0]: v for k, v in result.items() 
            if "kg/m³" in k and "Admixture" not in k
        }

        # Dynamic figure size based on screen width
        fig_width = 4 if st.session_state.get('is_mobile', False) else 5
        fig, ax = plt.subplots(figsize=(fig_width, fig_width*0.75))
        
        if chart_type == "Pie":
            ax.pie(
                chart_data.values(), 
                labels=chart_data.keys(), 
                autopct='%1.1f%%', 
                startangle=90,
                textprops={'fontsize': 8}
            )
            ax.axis('equal')
        else:
            bars = ax.bar(chart_data.keys(), chart_data.values(), color='skyblue')
            ax.bar_label(bars, fmt='%.1f', padding=3, fontsize=8)
            ax.set_ylabel("Mass (kg/m³)")
            ax.set_title("Mix Composition")
            plt.xticks(rotation=45, ha='right')
        
        plt.tight_layout()
        st.pyplot(fig)

    # Download button below both elements
    csv = df.to_csv().encode('utf-8')
    st.download_button(
        label="📥 Download CSV",
        data=csv,
        file_name="aci_mix.csv",
        mime='text/csv',
        use_container_width=True
    )

# --- Footer ---
st.markdown("---")
st.caption("© 2025 ACI 211.1 Concrete Mix Designer | Built by Automation_hub")

# Mobile detection (simplified)
st.session_state.is_mobile = st.checkbox("Mobile view", False, disabled=True, label_visibility="collapsed")
