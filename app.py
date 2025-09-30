import io
import os
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from ccip.ccip_compose import compose_workbook
from ccip.ccip_intake import detect_survey_columns

st.set_page_config(page_title="CCIP Processor", page_icon="📊", layout="centered")

st.title("📊 CCIP Processor")
st.markdown("Upload your survey data to generate Cross-Cultural Intelligence Profile reports.")

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
                    output_path = Path(temp_dir) / "CCIP_Results.xlsx"
                    
                    # Generate the workbook
                    success = compose_workbook(df, output_path, start_idx, end_idx)
                    
                    if not success:
                        st.error("❌ Failed to generate CCIP report. Please check your input data.")
                        st.stop()
                    
                    # Read the generated file into memory
                    with open(output_path, "rb") as f:
                        excel_data = f.read()
        
            st.success("✅ CCIP report generated successfully!")
            
            # Download button
            st.download_button(
                label="📥 Download CCIP Results.xlsx",
                data=excel_data,
                file_name="CCIP_Results.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )
            
        except Exception as e:
            st.error(f"❌ Error processing file: {str(e)}")
            st.exception(e)

else:
    st.info("👆 Please upload a survey file to get started")

# Add some information about the tool
with st.expander("ℹ️ About CCIP"):
    st.markdown("""
    **Cross-Cultural Intelligence Profile (CCIP)** generates detailed reports based on survey responses across five key dimensions:
    
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