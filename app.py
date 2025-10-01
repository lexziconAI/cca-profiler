import io
import logging
import os
import tempfile
import zipfile
from pathlib import Path

import pandas as pd
from pandas.errors import EmptyDataError
import streamlit as st

from ccip.ccip_compose import compose_workbook
from ccip.ccip_intake import detect_survey_columns

# Add defensive import for openpyxl exception
try:
    from openpyxl.utils.exceptions import InvalidFileException
except ImportError:
    InvalidFileException = type("InvalidFileException", (Exception,), {})

# Set up logging
logger = logging.getLogger(__name__)

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

with st.expander("Survey scale & instructions"):
    st.markdown("""
**Communication & Culture Advantage Profiler**

This profiler—which will require 5 to 7 minutes of your time to complete—is designed to help you reflect on your personal communication style, your adaptability across cultures, and the way you use empathy in workplace conversations.

The CCAP is not a test – there are no right or wrong answers. Instead, this tool will bolster your self-awareness of communication skills in diverse and international contexts.

When submitting this form, be sure to insert information (such as your **Name** and **Email Address**) you wish the system to record and retain – this is used to create your Personal Communication Profile, issued to you prior to your workshop attendance or coaching sessions.

**Instructions**
Read each statement carefully and select the option that best reflects how true it is for you.

**Use the following 5-point scale:**
1 = Strongly Disagree
2 = Disagree
3 = Neutral
4 = Agree
5 = Strongly Agree

**Time required:** 5–7 minutes.

Your responses will be combined into an anonymous communication snapshot that we will explore together during the workshop. Your results will not be shared with anyone.

When you submit this form, it will not automatically collect your details like name and email address unless you provide it yourself.
""")

# File upload
uploaded = st.file_uploader(
    "Upload survey data (Excel/CSV)",
    type=["xlsx", "xls", "csv"],
    help="Upload an Excel or CSV file containing survey responses. ⚠️ Please close the file in Excel before uploading."
)

if uploaded:
    st.success(f"File uploaded: {uploaded.name}")

    # Process button
    if st.button("🚀 Process Survey Data", type="primary"):
        try:
            with st.spinner("Processing survey data..."):
                # Read input file with specific error handling
                try:
                    if uploaded.name.lower().endswith(".csv"):
                        df = pd.read_csv(uploaded)
                    else:
                        df = pd.read_excel(uploaded)
                except PermissionError as e:
                    logger.error(f"Upload PermissionError (likely open in Excel): {e}")
                    st.error("❌ Upload failed. Please **close the file in Excel**, save it, then try again.")
                    st.stop()
                except EmptyDataError as e:
                    logger.error(f"Upload EmptyDataError: {e}")
                    st.error("❌ Upload failed. The file appears to be **empty or corrupted**.")
                    st.stop()
                except (InvalidFileException, zipfile.BadZipFile) as e:
                    logger.error(f"Upload invalid/corrupt Excel (BadZipFile): {e}")
                    st.error("❌ Upload failed. The file is **locked, corrupted, or still open in Excel**. Please close it, save it, and try again.")
                    st.stop()

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
                        logger.error(f"compose_workbook() returned False – generation failed for {uploaded.name}")
                        st.error("❌ Failed to generate CCA Profiler report. Please check your input data.")
                        st.stop()

                    # Defensive check: Verify file exists AND is not empty
                    if not output_path.exists():
                        logger.error(f"compose_workbook returned True but file does not exist: {output_path}")
                        st.error("❌ File generation failed. Please check that your survey data has **all 25 required questions**.")
                        st.stop()

                    if output_path.stat().st_size == 0:
                        logger.error(f"compose_workbook created empty file: {output_path}")
                        st.error("❌ File generation failed. The output file is empty - please check your input data.")
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
            logger.error(f"Unexpected error processing {uploaded.name}: {str(e)}", exc_info=True)
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