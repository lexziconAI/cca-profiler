import io
import os
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from ccip.ccip_compose import compose_workbook
from ccip.ccip_intake import detect_survey_columns

st.set_page_config(page_title="CCA Profiler", page_icon="🌍")

def _require_password():
    pw_env = os.getenv("APP_PASSWORD", "")
    if not pw_env:
        return  # no password set → no gate
    if not st.session_state.get("auth_ok", False):
        st.title("CCA Profiler")
        st.text_input("Password", type="password", key="pw")
        if st.button("Enter"):
            st.session_state["auth_ok"] = (st.session_state.get("pw","") == pw_env)
            if not st.session_state["auth_ok"]:
                st.error("Incorrect password")
            st.session_state["pw"] = ""
        st.stop()

_require_password()

st.title("🌍 CCA Profiler")
st.markdown("Upload your survey data to generate Communication & Culture Advantage reports.")

st.markdown("""
### Communication & Culture Advantage (CCA) Profiler©
**CCA Profiler** is an evidence-based reflection tool designed to help participants identify and adapt their communication tendencies in diverse and multicultural workplaces.

This report benchmarks your ability to recognise, respect, and adapt to cultural differences so you can communicate and work effectively across diverse settings. It does not mean being an expert in every culture.

CCA emphasises staying consciously aware of your cultural surroundings, noticing the clues and cues in people's behaviours, communication styles, and expectations, and making informed judgments based on observations and facts rather than assumptions. At its core, CCA requires placing the interests, feelings, and cultural context of others alongside your own, recognising that what feels natural or "professional" in one culture may not be the same in another.

While not a psychometric assessment, the CCA Profiler draws on established, research-backed frameworks in organisational psychology, intercultural communication, and leadership studies.
""")

# File upload
uploaded = st.file_uploader(
    "Upload survey data (Excel/CSV)",
    type=["xlsx", "xls", "csv"],
    help="Upload an Excel or CSV file containing survey responses"
)

if uploaded:
    st.success(f"File uploaded: {uploaded.name}")

    # Process button
    if st.button("🚀 Process Survey Data", type="primary"):
        try:
            with st.spinner("Processing survey data..."):
                # Read input to DataFrame
                if uploaded.name.lower().endswith(".csv"):
                    df = pd.read_csv(uploaded)
                else:
                    df = pd.read_excel(uploaded)

                st.info(f"Loaded {len(df)} rows from input file")

                # Detect survey columns
                start_idx, end_idx = detect_survey_columns(df)
                if start_idx is None:
                    st.error("❌ Could not detect survey columns in the uploaded file. Please ensure your file contains the required survey structure.")
                    st.stop()

                st.info(f"Detected survey columns from {start_idx} to {end_idx}")

                # Process to temporary file then read to memory
                with tempfile.TemporaryDirectory() as temp_dir:
                    output_path = Path(temp_dir) / "CCA_Profiler_Results.xlsx"

                    # Generate the workbook
                    success = compose_workbook(df, output_path, start_idx, end_idx)

                    if not success:
                        st.error("❌ Failed to generate CCA Profiler report. Please check your input data.")
                        st.stop()

                    # Read the generated file into memory
                    with open(output_path, "rb") as f:
                        excel_data = f.read()

            st.success("✅ CCA Profiler report generated successfully!")

            # Download button
            st.download_button(
                label="📥 Download CCA Profiler Results.xlsx",
                data=excel_data,
                file_name="CCA_Profiler_Results.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )

        except Exception as e:
            st.error(f"❌ Error processing file: {str(e)}")
            st.exception(e)

else:
    st.info("👆 Please upload a survey file to get started")

# Add some information about the tool
with st.expander("ℹ️ About CCA Profiler"):
    st.markdown("""
    **Communication & Culture Advantage (CCA) Profiler** generates detailed reports based on survey responses across five key dimensions:

    - **DT**: Directness & Transparency
    - **TR**: Task vs Relational Accountability
    - **CO**: Conflict Orientation
    - **CA**: Cultural Adaptability
    - **EP**: Empathy & Perspective-Taking

    The generated Excel report includes:
    - Individual dimension scores with interpretations
    - Key strengths recommendations
    - Development areas guidance
    - Priority recommendations with visual icons
    - Radar charts showing each participant's profile
    """)