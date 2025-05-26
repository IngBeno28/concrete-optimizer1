import streamlit as st
import pandas as pd
from io import BytesIO
import matplotlib.pyplot as plt

st.set_page_config(page_title="Concrete Mix Design Optimizer", layout="wide")
st.title("🧱 Concrete Mix Design Optimizer")

st.markdown("""
This tool helps you compute mix proportions for normal concrete using a simplified ACI method.
Enter your material properties and design targets below.
""")

# --- Sidebar ---
st.sidebar.title("Navigation")
st.sidebar.markdown("Use the sections below to input parameters and review results.")

# --- Input Section ---
st.header("1. Mix Design Parameters")
with st.expander("Design Inputs", expanded=True):
    fck = st.number_input("Target compressive strength (MPa)", 10.0, 80.0, 25.0)
    slump = st.slider("Slump (mm)", 25, 200, 75)
    use_slump_for_water = st.checkbox("Use slump value to estimate water content", value=False)
    w_c_ratio = st.number_input("Water/Cement Ratio", 0.3, 0.7, 0.5)
    cement_sg = st.number_input("Cement specific gravity (SG)", 2.0, 4.0, 3.15)
    water_sg = st.number_input("Water specific gravity (SG)", 0.9, 1.1, 1.0)
    admixture_pct = st.number_input("Admixture (% of cement weight)", 0.0, 10.0, 0.0)
    fa_ratio = st.number_input("Fine Aggregate Volume Ratio", 0.2, 0.6, 0.35)
    fa_sg = st.number_input("Fine aggregate SG", 2.4, 2.8, 2.65)
    fa_abs = st.number_input("Fine aggregate absorption (%)", 0.0, 5.0, 1.0)
    ca_sg = st.number_input("Coarse aggregate SG", 2.4, 2.8, 2.65)
    ca_abs = st.number_input("Coarse aggregate absorption (%)", 0.0, 5.0, 0.5)
    moisture_content = st.number_input("Moisture content of aggregates (%)", 0.0, 10.0, 2.0)
    ca_ratio = st.number_input("Coarse Aggregate Volume Ratio", 0.3, 0.8, 0.65)

# --- Unit Converter ---
st.header("2. Unit Converter")
with st.expander("Quick Unit Conversion"):
    kg = st.number_input("Kilograms (kg)", value=0.0)
    st.write(f"Pounds (lb): {round(kg * 2.20462, 2)}")
    lb = st.number_input("Pounds (lb)", value=0.0)
    st.write(f"Kilograms (kg): {round(lb / 2.20462, 2)}")

# --- Material Costs ---
st.header("3. Optional: Material Costs")
with st.expander("Material Prices (Optional)"):
    cement_cost = st.number_input("Cement cost per kg", 0.0, value=0.5)
    water_cost = st.number_input("Water cost per kg", 0.0, value=0.01)
    fa_cost = st.number_input("Fine aggregate cost per kg", 0.0, value=0.02)
    ca_cost = st.number_input("Coarse aggregate cost per kg", 0.0, value=0.02)
    admixture_cost = st.number_input("Admixture cost per kg", 0.0, value=1.0)
    dollar_to_cedi = st.number_input("Exchange Rate (USD to GHS)", 1.0, value=13.0)

# --- Strength Estimator ---
st.header("4. Optional: Estimate W/C Ratio from Strength")
with st.expander("Estimate W/C Ratio"):
    user_strength = st.number_input("Input target strength (MPa)", 10.0, 80.0, 25.0)
    estimated_wc = round(0.7 - 0.01 * user_strength, 3)
    st.write(f"Estimated W/C Ratio: {estimated_wc}")

# --- Optional User Inputs ---
st.header("5. Optional: Custom Mix Proportions")
with st.expander("Enter Custom Mix Proportions (kg/m³)"):
    user_water = st.number_input("Water (kg/m³)", value=0.0)
    user_cement = st.number_input("Cement (kg/m³)", value=0.0)
    user_fa = st.number_input("Fine Aggregate (kg/m³)", value=0.0)
    user_ca = st.number_input("Coarse Aggregate (kg/m³)", value=0.0)
    user_admixture = st.number_input("Admixture (kg/m³)", value=0.0)
    custom_entered = user_water + user_cement + user_fa + user_ca + user_admixture > 0
    if custom_entered:
        st.success("Custom mix proportions provided. Comparison will be shown after calculation.")

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

# --- Button to trigger calculation ---
if st.button("🔍 Calculate Mix Design"):
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

    except Exception as e:
        st.error(f"An error occurred: {e}")

if 'result' in st.session_state:
    result = st.session_state.result

    mix_df = pd.DataFrame({
        'Component': result.keys(),
        'Quantity (kg/m³)': result.values(),
        'Unit Cost ($/kg)': [water_cost, cement_cost, fa_cost, ca_cost, admixture_cost],
    })
    mix_df['Total Cost ($/m³)'] = mix_df['Quantity (kg/m³)'] * mix_df['Unit Cost ($/kg)']
    mix_df['Total Cost (GHS/m³)'] = mix_df['Total Cost ($/m³)'] * dollar_to_cedi

    st.header("6. Calculated Mix and Cost")
    col1, col2 = st.columns(2)
    with col1:
        st.dataframe(mix_df, use_container_width=True)
        st.metric("💲 Total Cost per m³ (USD)", f"${round(mix_df['Total Cost ($/m³)'].sum(), 2)}")
        st.metric("🇬🇭 Total Cost per m³ (GHS)", f"GH₵{round(mix_df['Total Cost (GHS/m³)'].sum(), 2)}")

    with col2:
        fig, ax = plt.subplots()
        ax.pie(result.values(), labels=result.keys(), autopct='%1.1f%%', startangle=90)
        ax.axis('equal')
        st.pyplot(fig)

    if custom_entered:
        user_mix = {
            'Water': user_water,
            'Cement': user_cement,
            'Fine Aggregate': user_fa,
            'Coarse Aggregate': user_ca,
            'Admixture': user_admixture
        }
        compare_df = pd.DataFrame({
            'Component': result.keys(),
            'Calculated (kg/m³)': result.values(),
            'User Input (kg/m³)': [user_mix[k] for k in result],
            'Difference': [round(float(user_mix[k]) - float(result[k]), 2) for k in result]
        })
        st.subheader("Comparison with User Mix")
        st.dataframe(compare_df, use_container_width=True)

        warnings = []
        for comp in result:
            diff_pct = abs(user_mix[comp] - result[comp]) / result[comp] * 100
            if diff_pct > 10:
                warnings.append(f"⚠️ {comp} deviates by {round(diff_pct, 1)}% from calculated.")
        if warnings:
            st.warning("\n".join(warnings))
        else:
            st.success("All user values are within 10% of calculated mix.")

    st.success("Mix design completed successfully.")

    st.header("7. Export Results")
    st.download_button(
        label="⬇️ Download Excel File",
        data=to_excel(mix_df),
        file_name="concrete_mix_design.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
