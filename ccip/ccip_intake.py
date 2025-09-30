"""Data intake and processing for CCIP survey responses."""

import logging
import os
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)

# Reverse-scored items (Q2 and Q11)
REVERSE_ITEMS = [2, 11]

# Dimension mappings (1-indexed question numbers)
DIMENSION_ITEMS = {
    "DT": [1, 6, 11, 16, 21],
    "TR": [2, 7, 12, 17, 22],
    "CO": [3, 8, 13, 18, 23],
    "CA": [4, 9, 14, 19, 24],
    "EP": [5, 10, 15, 20, 25]
}


def _column_i_preferred(df: pd.DataFrame) -> Tuple[Optional[int], Optional[int]]:
    """
    Primary method: Check if Q1 is at Excel column I (index 8).
    """
    anchor = "prefer to be clear and direct"
    if len(df.columns) > 8:  # Column I exists (0-indexed = 8)
        col_i_header = str(df.columns[8])
        if anchor.lower() in col_i_header.lower():
            # Check if we have 24 more columns after I (J..AG)
            if len(df.columns) >= 8 + 25:  # I + 24 more = 25 total
                logger.info("QDetect: Using ColumnIPreferred (I..AG)")
                return 8, 8 + 24
    return None, None


def _contiguous_after_anchor(df: pd.DataFrame) -> Tuple[Optional[int], Optional[int]]:
    """
    Fallback 1: Classic mode - anchor column + 25 contiguous columns after it.
    """
    anchor = "prefer to be clear and direct"
    for idx, col in enumerate(df.columns):
        if anchor.lower() in str(col).lower():
            # Check if there are exactly 25 columns after this anchor
            if idx + 25 < len(df.columns):
                logger.info(f"QDetect: Using AfterAnchor ({idx+1}..{idx+25})")
                return idx + 1, idx + 25
    return None, None


def _anchor_is_q1(df: pd.DataFrame) -> Tuple[Optional[int], Optional[int]]:
    """
    Fallback 2: Anchor column IS Q1, with exactly 24 columns after it.
    """
    anchor = "prefer to be clear and direct"
    for idx, col in enumerate(df.columns):
        if anchor.lower() in str(col).lower():
            # Check if there are exactly 24 columns after this (making 25 total)
            if idx + 24 < len(df.columns):
                logger.info(f"QDetect: Using AnchorIsQ1 ({idx} + 24)")
                return idx, idx + 24
    return None, None


def _header_based_search(df: pd.DataFrame) -> Tuple[Optional[int], Optional[int]]:
    """
    Fallback 3: Search for Q1-Q25 headers with variants.
    """
    # Generate all possible variants for Q1-Q25
    q_variants = {}
    for i in range(1, 26):
        variants = [
            f"Q{i}", f"Q {i}", f"Q{i:02d}", f"Q{i}_Response", f"Q{i} Response",
            f"q{i}", f"q {i}", f"q{i:02d}", f"q{i}_response", f"q{i} response"
        ]
        for variant in variants:
            q_variants[variant] = i

    # Find columns matching Q variants
    found_questions = {}
    for idx, col in enumerate(df.columns):
        col_str = str(col).strip()
        if col_str in q_variants:
            q_num = q_variants[col_str]
            if q_num not in found_questions:
                found_questions[q_num] = idx

    # Check if we have all 25 questions
    missing = []
    for i in range(1, 26):
        if i not in found_questions:
            missing.append(f"Q{i}")

    if missing:
        if found_questions:  # Some found but not all
            raise ValueError(f"Missing question columns: {missing}")
        return None, None

    # Sort by question number to get ordered indices
    ordered_indices = [found_questions[i] for i in range(1, 26)]
    start_idx = min(ordered_indices)
    end_idx = max(ordered_indices)

    logger.info(f"QDetect: Using HeaderBased (Q1..Q25)")
    return start_idx, end_idx


def _statistical_heuristic(df: pd.DataFrame) -> Tuple[Optional[int], Optional[int]]:
    """
    Fallback 4: Look for 25-wide contiguous blocks that look like Likert responses.
    """
    anchor = "prefer to be clear and direct"
    likert_patterns = {'1', '2', '3', '4', '5', '6', '7',
                      'strongly disagree', 'disagree', 'neutral', 'agree', 'strongly agree',
                      'strongly_disagree', 'strongly_agree'}

    candidates = []

    # Scan for 25-wide blocks
    for start_idx in range(len(df.columns) - 24):
        block_cols = df.columns[start_idx:start_idx + 25]

        # Check if first column contains anchor text
        first_col_has_anchor = anchor.lower() in str(block_cols[0]).lower()

        if not first_col_has_anchor:
            continue

        # Check if this block looks like Likert responses
        likert_score = 0
        total_cells = 0

        for col in block_cols:
            for _, cell_value in df[col].items():
                if pd.notna(cell_value):
                    total_cells += 1
                    cell_str = str(cell_value).strip().lower()

                    # Check for numeric 1-7
                    try:
                        if 1 <= int(cell_str) <= 7:
                            likert_score += 1
                            continue
                    except ValueError:
                        pass

                    # Check for text patterns
                    for pattern in likert_patterns:
                        if pattern in cell_str:
                            likert_score += 1
                            break

        # If >50% of cells look like Likert responses, consider it a candidate
        if total_cells > 0 and (likert_score / total_cells) > 0.5:
            candidates.append((start_idx, start_idx + 24, likert_score / total_cells))

    if len(candidates) == 0:
        return None, None
    elif len(candidates) == 1:
        start_idx, end_idx, score = candidates[0]
        logger.info(f"QDetect: Using StatisticalHeuristic ({start_idx}..{end_idx}, score={score:.2f})")
        return start_idx, end_idx
    else:
        # Multiple candidates - fail safely
        candidate_ranges = [f"{start}-{end}" for start, end, _ in candidates]
        logger.warning(f"QDetect: Multiple candidate blocks found; failing safely")
        raise ValueError(f"Multiple plausible 25-wide blocks found: {candidate_ranges}. Please specify Q1 location explicitly.")


def detect_survey_columns(df: pd.DataFrame) -> Tuple[Optional[int], Optional[int]]:
    """
    Robust Q1 location detection with deterministic fallback hierarchy.

    Order of detection:
    1. Column I preference (Excel column I contains anchor)
    2. Contiguous-after-anchor (anchor + 25 columns after)
    3. Anchor-is-Q1 (anchor = Q1, + 24 columns after)
    4. Header-based search (find Q1..Q25 headers)
    5. Statistical heuristic (find Likert-like 25-wide block)

    Returns (start_idx, end_idx) or (None, None) if not found.
    Raises ValueError for ambiguous cases.
    """
    methods = [
        _column_i_preferred,
        _contiguous_after_anchor,
        _anchor_is_q1,
        _header_based_search,
        _statistical_heuristic
    ]

    for method in methods:
        try:
            result = method(df)
            if result[0] is not None and result[1] is not None:
                return result
        except ValueError as e:
            # Re-raise ValueError from methods (like missing Q columns)
            raise e
        except Exception as e:
            # Log other errors but continue to next method
            logger.warning(f"Detection method {method.__name__} failed: {e}")
            continue

    logger.warning("Could not detect survey columns using any method")
    return None, None


def parse_likert_response(value) -> Optional[int]:
    """
    STRICT 5-point Likert parser: returns 1..5 or None.
    Accepts numeric 1..5, or text variants:
      strongly disagree=1, disagree=2, neutral/neither agree nor disagree=3,
      agree=4, strongly agree=5
    Rejects any 6/7 and any 'somewhat' phrases by raising ValueError.
    """
    if pd.isna(value):
        return None

    # Numeric
    if isinstance(value, (int, float)):
        val = int(value)
        if 1 <= val <= 5:
            return val
        if val in (6, 7):
            raise ValueError("Found 6/7 or 'somewhat' but this survey uses a 5-point Likert scale.")
        return None

    s = str(value).strip().lower()

    # Numeric strings
    if s in {"1","2","3","4","5"}:
        return int(s)
    if s in {"6","7"}:
        raise ValueError("Found 6/7 or 'somewhat' but this survey uses a 5-point Likert scale.")

    # Reject any 'somewhat'
    if "somewhat" in s:
        raise ValueError("Found 6/7 or 'somewhat' but this survey uses a 5-point Likert scale.")

    # Text map (tolerant) - order matters, longer phrases first
    text_map = [
        ("neither agree nor disagree", 3),
        ("strongly disagree", 1),
        ("strongly agree", 5),
        ("disagree", 2),
        ("agree", 4),
        ("neutral", 3),
    ]
    for key, val in text_map:
        if key in s:
            return val

    return None


def reverse_score(value: int) -> int:
    """Reverse score a Likert item (1-5 scale)."""
    return 6 - value


def calculate_dimension_scores(responses: List[Optional[int]]) -> Dict[str, float]:
    """
    Calculate dimension scores from 25 survey responses.
    Applies reverse scoring to items 2 and 11.
    Returns dictionary of dimension scores (DT, TR, CO, CA, EP).
    """
    scores = {}
    
    # Apply reverse scoring
    processed_responses = []
    for i, val in enumerate(responses):
        q_num = i + 1  # 1-indexed
        if val is not None and q_num in REVERSE_ITEMS:
            processed_responses.append(reverse_score(val))
        else:
            processed_responses.append(val)
    
    # Calculate dimension scores
    for dim, items in DIMENSION_ITEMS.items():
        dim_values = []
        for item_num in items:
            idx = item_num - 1  # Convert to 0-indexed
            if idx < len(processed_responses):
                val = processed_responses[idx]
                if val is not None:
                    dim_values.append(val)
        
        if dim_values:
            scores[dim] = sum(dim_values) / len(dim_values)
        else:
            scores[dim] = None
    
    return scores


def parse_date(date_val) -> Optional[datetime]:
    """Parse various date formats to datetime."""
    if pd.isna(date_val):
        return None
    
    if isinstance(date_val, datetime):
        return date_val
    
    if isinstance(date_val, pd.Timestamp):
        return date_val.to_pydatetime()
    
    # Try parsing string dates
    date_str = str(date_val).strip()
    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%Y/%m/%d']:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    return None


def derive_date_column(df: pd.DataFrame, src_path: Optional[str] = None) -> pd.Series:
    """
    Returns a pandas Series of strings formatted dd/mm/yyyy.
    Prefers existing 'Date'. Else derives from 'Start time'.
    Else file mtime; else today.
    """

    # 1. Check if Date column already exists
    date_columns = [col for col in df.columns if str(col).strip().lower() == 'date']
    if date_columns:
        logger.info("Intake: Using existing Date column")
        # Convert existing Date column to dd/mm/yyyy format
        date_series = df[date_columns[0]].copy()
        formatted_dates = []

        for date_val in date_series:
            parsed_date = parse_date(date_val)
            if parsed_date:
                formatted_dates.append(parsed_date.strftime('%d/%m/%Y'))
            else:
                # Fallback for unparseable dates
                fallback_date = _get_fallback_date(src_path)
                formatted_dates.append(fallback_date)

        return pd.Series(formatted_dates, name='Date')

    # 2. Check for Start time column (case-insensitive)
    start_time_columns = [col for col in df.columns
                         if str(col).strip().lower() in ['start time', 'start_time']]

    if start_time_columns:
        logger.info("Intake: Derived Date from 'Start time' column")
        start_time_series = df[start_time_columns[0]]
        return _parse_start_time_to_date(start_time_series, src_path)

    # 3. Fallback to file mtime or today
    fallback_date = _get_fallback_date(src_path)
    if src_path and os.path.exists(src_path):
        logger.warning(f"Intake: Input lacked Date and Start time; using file modified date {fallback_date}")
    else:
        logger.warning(f"Intake: Input lacked Date and Start time; using today {fallback_date}")

    # Return series with same length as dataframe
    return pd.Series([fallback_date] * len(df), name='Date')


def _get_fallback_date(src_path: Optional[str] = None) -> str:
    """Get fallback date as dd/mm/yyyy string."""
    if src_path and os.path.exists(src_path):
        try:
            mtime = os.path.getmtime(src_path)
            file_date = datetime.fromtimestamp(mtime).date()
            return file_date.strftime('%d/%m/%Y')
        except Exception:
            pass

    # Use today as final fallback
    return date.today().strftime('%d/%m/%Y')


def _parse_start_time_to_date(start_time_series: pd.Series, src_path: Optional[str] = None) -> pd.Series:
    """Parse Start time series to dd/mm/yyyy formatted dates."""
    formatted_dates = []
    failed_count = 0
    fallback_date = _get_fallback_date(src_path)

    for value in start_time_series:
        parsed_date = None

        if pd.notna(value):
            # Handle Excel numeric datetime serials
            if isinstance(value, (int, float)):
                try:
                    # Convert Excel serial to datetime
                    parsed_dt = pd.to_datetime(value, unit='D', origin='1899-12-30', errors='coerce')
                    if pd.notna(parsed_dt):
                        parsed_date = parsed_dt.date()
                except Exception:
                    pass
            else:
                # Handle string datetime values
                try:
                    # Primary parsing with dayfirst=True
                    parsed_dt = pd.to_datetime(str(value), dayfirst=True, errors='coerce')
                    if pd.notna(parsed_dt):
                        # Convert timezone-aware to naive if needed
                        if parsed_dt.tz is not None:
                            parsed_dt = parsed_dt.tz_convert(None)
                        parsed_date = parsed_dt.date()
                    else:
                        # Second pass: normalise whitespace and try again
                        normalised_value = ' '.join(str(value).strip().split())
                        parsed_dt = pd.to_datetime(normalised_value, dayfirst=True, errors='coerce')
                        if pd.notna(parsed_dt):
                            if parsed_dt.tz is not None:
                                parsed_dt = parsed_dt.tz_convert(None)
                            parsed_date = parsed_dt.date()
                except Exception:
                    pass

        if parsed_date:
            formatted_dates.append(parsed_date.strftime('%d/%m/%Y'))
        else:
            formatted_dates.append(fallback_date)
            failed_count += 1

    # Log warning if any rows failed to parse
    if failed_count > 0:
        logger.warning(f"Intake: Start time parse failed for {failed_count} rows; filled with fallback date {fallback_date}")

    return pd.Series(formatted_dates, name='Date')


def process_survey_row(row: pd.Series, start_idx: int, end_idx: int) -> Dict:
    """
    Process a single survey response row.
    Returns dict with ID, Email, Date, responses, and dimension scores.
    """
    result = {
        'ID': row.get('ID'),
        'Email': row.get('Email'),
        'Date': parse_date(row.get('Date')),
        'responses': [],
        'scores': {}
    }
    
    # Extract survey responses
    for i in range(start_idx, min(end_idx + 1, len(row))):
        val = parse_likert_response(row.iloc[i])
        result['responses'].append(val)
    
    # Ensure we have exactly 25 responses (pad with None if needed)
    while len(result['responses']) < 25:
        result['responses'].append(None)
    
    # Calculate dimension scores
    result['scores'] = calculate_dimension_scores(result['responses'])
    
    return result