#!/usr/bin/env python3
"""
CCIP Runner Script - Process Excel survey data and generate CCIP reports

Usage:
    python3 run_ccip.py input_file.xlsx output_file.xlsx
"""

import sys
import logging
import zipfile
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

        if not success:
            logging.error(f"compose_workbook returned False for file: {input_file}")
            print("❌ FAILED: Could not generate CCIP report")
            sys.exit(1)

        # Defensive check: Verify file exists AND is not empty
        if not output_file.exists():
            logging.error(f"compose_workbook returned True but file missing: {output_file}")
            print("❌ FAILED: File generation failed. Please check that your survey data has all 25 required questions.")
            sys.exit(1)

        if output_file.stat().st_size == 0:
            logging.error(f"compose_workbook created empty file: {output_file}")
            print("❌ FAILED: Generated file is empty. Please check your input data.")
            sys.exit(1)

        print(f"✅ SUCCESS: CCIP report generated at '{output_file}'")

        # Show summary
        result_df = pd.read_excel(output_file, sheet_name='CCIP Results')
        print(f"📊 Report contains {len(result_df)} participants")
        print(f"📋 Columns included: {', '.join(result_df.columns[:8])}...")

    except PermissionError as e:
        logging.error(f"PermissionError: {e}")
        print("❌ ERROR: File is locked. Please close the file in Excel and try again.")
        sys.exit(1)
    except pd.errors.EmptyDataError as e:
        logging.error(f"EmptyDataError: {e}")
        print("❌ ERROR: The file appears to be empty or corrupted.")
        sys.exit(1)
    except zipfile.BadZipFile as e:
        logging.error(f"BadZipFile error: {e}")
        print("❌ ERROR: File is corrupted or still open in Excel. Please close and try again.")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Unexpected error: {e}", exc_info=True)
        print(f"❌ ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()