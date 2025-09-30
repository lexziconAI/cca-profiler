#!/usr/bin/env python3
"""
CCIP Runner Script - Process Excel survey data and generate CCIP reports

Usage:
    python3 run_ccip.py input_file.xlsx output_file.xlsx
"""

import sys
import logging
import pandas as pd
from pathlib import Path
from ccip.ccip_compose import compose_workbook
from ccip.ccip_intake import detect_survey_columns

# Enable INFO logging to show Q1 detection method
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 run_ccip.py <input_excel_file> <output_excel_file>")
        print("Example: python3 run_ccip.py survey_data.xlsx ccip_results.xlsx")
        sys.exit(1)

    input_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2])

    # Check input file exists
    if not input_file.exists():
        print(f"Error: Input file '{input_file}' not found!")
        sys.exit(1)

    try:
        # Load Excel file
        print(f"Loading Excel file: {input_file}")
        df = pd.read_excel(input_file)
        print(f"Loaded {len(df)} rows with {len(df.columns)} columns")

        # Detect survey columns
        print("Detecting survey columns...")
        start_idx, end_idx = detect_survey_columns(df)

        if start_idx is None or end_idx is None:
            print("Error: Could not detect survey columns!")
            print("Make sure your Excel file has:")
            print("- An anchor column with text like 'I prefer to be clear and direct'")
            print("- 25 survey response columns with numerical data")
            sys.exit(1)

        print(f"Survey columns detected: {start_idx} to {end_idx}")

        # Generate CCIP report
        print(f"Generating CCIP report...")
        success = compose_workbook(df, output_file, start_idx, end_idx, str(input_file))

        if success:
            print(f"✅ SUCCESS: CCIP report generated at '{output_file}'")

            # Show summary
            result_df = pd.read_excel(output_file, sheet_name='CCIP Results')
            print(f"📊 Report contains {len(result_df)} participants")
            print(f"📋 Columns included: {', '.join(result_df.columns[:8])}...")

        else:
            print("❌ FAILED: Could not generate CCIP report")
            sys.exit(1)

    except Exception as e:
        print(f"❌ ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()