"""CLI entry point for CCIP package."""

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

from .ccip_compose import compose_workbook, validate_col_against_required
from .ccip_intake import detect_survey_columns

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_input_file(input_path: Path) -> pd.DataFrame:
    """Load CSV or Excel file."""
    if input_path.suffix.lower() == '.csv':
        return pd.read_csv(input_path)
    elif input_path.suffix.lower() in ['.xlsx', '.xls']:
        return pd.read_excel(input_path)
    else:
        raise ValueError(f"Unsupported file type: {input_path.suffix}")


def check_forbidden_glyphs():
    """Check for forbidden glyphs in source code."""
    forbidden = ["✓", "✔", "✗", "tick", "checkmark", "status icon"]
    
    package_dir = Path(__file__).parent
    for py_file in package_dir.glob("*.py"):
        content = py_file.read_text()
        for glyph in forbidden:
            if glyph in content:
                logger.error(f"Forbidden glyph '{glyph}' found in {py_file.name}")
                return False
    
    return True


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='CCIP - Cross-Cultural Intelligence Profile Report Generator'
    )
    parser.add_argument(
        '--input', '-i',
        type=Path,
        required=True,
        help='Path to input CSV or Excel file with survey responses'
    )
    parser.add_argument(
        '--output', '-o',
        type=Path,
        required=True,
        help='Path for output Excel workbook'
    )
    parser.add_argument(
        '--check-glyphs',
        action='store_true',
        help='Check for forbidden glyphs in source code'
    )
    
    args = parser.parse_args()
    
    # Check for forbidden glyphs if requested
    if args.check_glyphs:
        if not check_forbidden_glyphs():
            sys.exit(1)
        logger.info("No forbidden glyphs found")
        return
    
    # Validate input file
    if not args.input.exists():
        logger.error(f"Input file not found: {args.input}")
        sys.exit(1)
    
    # Load input data
    try:
        logger.info(f"Loading input file: {args.input}")
        df = load_input_file(args.input)
        logger.info(f"Loaded {len(df)} rows")
    except Exception as e:
        logger.error(f"Failed to load input file: {e}")
        sys.exit(1)
    
    # Detect survey columns
    start_idx, end_idx = detect_survey_columns(df)
    if start_idx is None:
        logger.error("Could not detect survey columns in input file")
        sys.exit(1)
    
    logger.info(f"Detected survey columns from {start_idx} to {end_idx}")
    
    # Compose workbook
    try:
        success = compose_workbook(df, args.output, start_idx, end_idx)
        if success:
            logger.info(f"Successfully created workbook: {args.output}")
        else:
            logger.error("Failed to create workbook")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Error creating workbook: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()