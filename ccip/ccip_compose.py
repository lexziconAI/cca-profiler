"""Main composition logic and constants for CCIP report generation."""

import logging
import tempfile
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

from .ccip_embed import embed_icon, embed_radar, normalize_band_label, safe_render_and_embed_icon, insert_radar, RADAR_PNG_W, RADAR_PNG_H
from .ccip_intake import process_survey_row, derive_date_column
from .ccip_radar import generate_radar_chart_svg_scaled
from .svg_icons_radar import ICONS

logger = logging.getLogger(__name__)

# Dimension order
DIM_ORDER = ["DT", "TR", "CO", "CA", "EP"]

# LOCKED OUTPUT SCHEMA - authoritative; no extras (42 columns)
REQUIRED_COLUMNS = [
    "Date", "ID", "Name", "Email",
    "DT_Score", "TR_Score", "CO_Score", "CA_Score", "EP_Score",
    "KS1_Icon", "KS1_Title", "KS1_Body",
    "KS2_Icon", "KS2_Title", "KS2_Body",
    "KS3_Icon", "KS3_Title", "KS3_Body",
    "DA1_Icon", "DA1_Title", "DA1_Body",
    "DA2_Icon", "DA2_Title", "DA2_Body",
    "DA3_Icon", "DA3_Title", "DA3_Body",
    "PR1_Icon", "PR1_Title", "PR1_Body",
    "PR2_Icon", "PR2_Title", "PR2_Body",
    "PR3_Icon", "PR3_Title", "PR3_Body",
    "RQ1", "RQ2", "RQ3", "RQ4",
    "Summary", "Radar_Chart"
]

# AUTO COL MAP - no manual drift
COL = {c.replace(" ", "_").replace("-", "_").replace("/", "_"): i
       for i, c in enumerate(REQUIRED_COLUMNS)}


# Dimension labels
DIMENSION_LABELS = {
    "DT": "Directness & Transparency",
    "TR": "Task vs Relational Accountability",
    "CO": "Conflict Orientation",
    "CA": "Cultural Adaptability",
    "EP": "Empathy & Perspective-Taking"
}

# Scoring scale conversion helpers
def _to_0_5_from_1_7(x: float) -> float:
    return (float(x) - 1.0) * (5.0 / 6.0)

def _clamp_0_5(x: float) -> float:
    x = float(x)
    return 0.0 if x < 0.0 else (5.0 if x > 5.0 else x)

def _scale_and_clamp_scores_0_5(scores: Dict[str, float]) -> Dict[str, float]:
    out = {}
    for k, v in scores.items():
        if v is None:
            out[k] = None
        else:
            out[k] = _clamp_0_5(_to_0_5_from_1_7(v))
    return out

# Band thresholds
BAND_THRESHOLDS = {
    "Low / Limited": (1.0, 2.5),
    "Developing": (2.5, 3.5),
    "Moderate / Balanced": (3.5, 5.0),
    "High": (5.0, 6.0),
    "Very High": (6.0, 7.0)
}

# Placeholder texts
KS_PLACEHOLDER_TITLE = "Continue developing your strengths"
KS_PLACEHOLDER_BODY = "Your profile shows balanced capabilities across multiple dimensions.\nMaintain your current practices while staying open to growth opportunities.\nRegular self-reflection will help you adapt to evolving leadership challenges."

DA_PLACEHOLDER_TITLE = "Maintain your balanced approach"
DA_PLACEHOLDER_BODY = "Your scores indicate well-developed capabilities across the measured dimensions.\nContinue to refine your skills through deliberate practice and feedback.\nStay curious about how different contexts might require adjusted approaches."

# Score interpretations
SCORE_INTERP = {
    "DT": {
        "Low / Limited": "Often unclear or indirect, leading to misunderstandings and reduced trust. High-priority development to improve organisational alignment and results.",
        "Developing": "Sometimes avoids or softens key messages, creating ambiguity or delayed action. Needs deliberate practice in clear, constructive communication while maintaining respect.",
        "Moderate / Balanced": "Demonstrates clear communication in familiar contexts but may adapt inconsistently across diverse settings. A solid base to build stronger clarity and consistency.",
        "High": "Speaks clearly and transparently in most situations, usually balancing directness with cultural sensitivity. Minor inconsistencies may appear under pressure but rarely impact understanding.",
        "Very High": "Communicates expectations and feedback with exceptional clarity and honesty while remaining sensitive to cultural norms. Consistently sets a standard for open, trust-building dialogue."
    },
    "TR": {
        "Low / Limited": "Strongly biased toward task or relationship focus, often undermining either performance or trust. Immediate attention needed to rebalance.",
        "Developing": "Tends to favour either deadlines or harmony, causing friction or missed opportunities. Needs targeted practice in adjusting focus to context.",
        "Moderate / Balanced": "Handles tasks and relationships fairly well but may default to one side under stress. A good platform for conscious flexibility.",
        "High": "Regularly integrates task focus and relationship-building, with only minor leanings toward one side depending on context.",
        "Very High": "Seamlessly balances getting results with nurturing relationships. Maintains efficiency while fostering strong trust and collaboration."
    },
    "CO": {
        "Low / Limited": "Routinely avoids or mismanages conflict, creating ongoing friction or disengagement. Priority focus area for leadership growth.",
        "Developing": "Often postpones or minimises conflict, leading to unresolved tension and lost opportunities for improvement.",
        "Moderate / Balanced": "Handles some conflicts well but may avoid or delay others, allowing small issues to grow. Solid basis for strengthening proactive dialogue.",
        "High": "Generally comfortable engaging in healthy conflict and resolving issues before they escalate; occasional hesitancy may surface in complex situations.",
        "Very High": "Consistently addresses disagreements early and constructively, transforming tension into innovation and stronger collaboration."
    },
    "CA": {
        "Low / Limited": "Rarely adjusts to cultural differences; may unintentionally create misunderstanding or exclusion. High-priority development.",
        "Developing": "Often relies on default styles or assumptions, limiting success in diverse environments. Needs deliberate exposure and practice.",
        "Moderate / Balanced": "Shows willingness to adapt but may revert to familiar norms in complex or unfamiliar cultural settings. Good foundation for broader adaptability.",
        "High": "Comfortable adapting to most cultural situations, learning quickly and adjusting behaviour effectively, with only minor gaps.",
        "Very High": "Rapidly reads cultural cues and flexes communication styles with ease, enabling seamless collaboration across geographies and teams."
    },
    "EP": {
        "Low / Limited": "Rarely considers others' experiences or perspectives, limiting trust and collaboration. Critical area for growth.",
        "Developing": "Sometimes listens without fully integrating others' views, or focuses on tasks at the expense of relationships. Needs deliberate empathy-building practices.",
        "Moderate / Balanced": "Shows understanding and concern for others in many situations, but may overlook perspectives when under pressure.",
        "High": "Frequently shows empathy and perspective-taking, creating strong relationships and effective collaboration, with only occasional gaps.",
        "Very High": "Consistently demonstrates deep empathy and integrates others' viewpoints into decision-making, strengthening trust and inclusion across teams."
    }
}

# KS texts (pre-split)
KS_TEXTS = {
    "DT": {
        "High": "You communicate with clarity and honesty, ensuring that expectations and feedback are well understood.\nYour ability to balance directness with cultural sensitivity helps you give clear guidance without creating defensiveness, a key factor in building psychological safety.\nBecause you consistently express both what needs to be done and why it matters, you minimise misunderstandings and keep projects on track.",
        "Very High": "You communicate with exceptional clarity and candid honesty, ensuring that expectations and feedback are unmistakably understood.\nYour strong ability to balance directness with thoughtful cultural sensitivity helps you give clear guidance without creating defensiveness, a crucial factor in building psychological safety.\nBecause you consistently and explicitly express both what needs to be done and why it matters, you reliably minimise misunderstandings and keep projects firmly on track."
    },
    "TR": {
        "High": "You manage the balance between getting things done and nurturing relationships with skill.\nThis allows you to meet deadlines without sacrificing team cohesion.\nYour ability to adapt, sometimes prioritising efficiency and at other times focusing on rapport, creates resilient, high-performing teams. Colleagues value you as someone who drives outcomes while ensuring people feel respected and included.",
        "Very High": "You manage the balance between getting things done and nurturing relationships with notable skill, which allows you to meet deadlines while maintaining strong team cohesion.\nYour highly adaptive ability to switch focus, sometimes prioritising efficiency and at other times rapport, creates resilient, consistently high-performing teams.\nColleagues strongly value you as someone who drives outcomes while ensuring people feel respected and included."
    },
    "CO": {
        "High": "You approach conflict as an opportunity to clarify issues and strengthen collaboration.\nThis creates space for innovation and better decisions.\nYour comfort in addressing disagreements early helps prevent small issues from escalating and keeps energy focused on solutions. By modelling constructive conflict management, you help build a culture where diverse opinions are valued and integrated.",
        "Very High": "You approach conflict as a valuable opportunity to clarify issues and strengthen collaboration, which consistently creates space for innovation and better decisions.\nYour strong comfort in addressing disagreements early helps prevent small issues from escalating and keeps energy tightly focused on solutions.\nBy reliably modelling constructive conflict management, you help build a culture where diverse opinions are genuinely valued and effectively integrated."
    },
    "CA": {
        "High": "You read cultural cues quickly and adjust your communication and behaviour with ease, enabling smooth collaboration across geographies and teams.\nThis flexibility helps you build rapport with clients and colleagues from diverse backgrounds, strengthening partnerships and reducing misunderstandings.\nYour openness to different customs and practices demonstrates respect and enhances organisational reputation.",
        "Very High": "You read cultural cues very quickly and adjust your communication and behaviour with notable ease, enabling smooth collaboration across geographies and teams.\nThis pronounced flexibility helps you build strong rapport with clients and colleagues from diverse backgrounds, strengthening partnerships and reducing misunderstandings.\nYour evident openness to different customs and practices demonstrates deep respect and enhances organisational reputation."
    },
    "EP": {
        "High": "You naturally seek to understand others' thoughts and emotions, enabling you to build trust and influence without authority.\nColleagues feel heard and valued in your presence, which strengthens engagement and loyalty.\nYour capacity to integrate multiple viewpoints leads to more inclusive decisions and stronger team cohesion.",
        "Very High": "You naturally and actively seek to understand others' thoughts and emotions, enabling you to build strong trust and influence without authority.\nColleagues consistently feel heard and genuinely valued in your presence, which strengthens engagement and loyalty.\nYour strong capacity to integrate multiple viewpoints leads to more inclusive decisions and robust team cohesion."
    }
}

# DA texts (pre-split)
DA_TEXTS = {
    "DT": {
        "Developing": "You may at times leave some room for ambiguity, causing others to guess at priorities or next steps.\nYou might occasionally avoid difficult conversations or soften messages enough that key information is partly lost.\nDeveloping greater clarity, while respecting cultural nuances, will help you build trust and reduce rework or conflict.",
        "Low / Limited": "You often leave considerable room for ambiguity, causing others to guess at priorities or next steps.\nYou may frequently avoid difficult conversations or soften messages so much that key information is lost.\nEstablishing greater clarity, while still respecting cultural nuances, will help you rebuild trust and significantly reduce rework or conflict."
    },
    "TR": {
        "Developing": "Your current pattern may sometimes tilt too heavily toward either tasks or relationships, which can lead to occasional missed deadlines or disengaged team members.\nThere may be times when relational needs are overlooked in the drive for efficiency, or where progress slows because harmony is prioritised over results.\nLearning to flex more consciously between task and relationship focus will help you maintain productivity and strengthen trust simultaneously.",
        "Low / Limited": "Your current pattern often tilts heavily toward either tasks or relationships, which can lead to repeated missed deadlines or disengaged team members.\nRelational needs are frequently overlooked in the drive for efficiency, or progress often slows because harmony is prioritised over results.\nLearning to flex deliberately between task and relationship focus is essential to restore productivity and rebuild trust."
    },
    "CO": {
        "Developing": "You may hesitate to surface conflict or wait until issues become urgent, which can allow small problems to grow.\nWhen conflict does arise, you might sometimes withdraw or react defensively, reducing trust and slowing resolution.\nDeveloping skills to initiate timely, balanced conflict conversations will increase team resilience and creative problem solving.",
        "Low / Limited": "You often hesitate to surface conflict or wait until issues become urgent, which allows small problems to grow significantly.\nWhen conflict arises, you may withdraw or react defensively, which reduces trust and slows resolution.\nEstablishing skills to initiate timely, balanced conflict conversations is essential to strengthen team resilience and improve problem solving."
    },
    "CA": {
        "Developing": "You may sometimes default to familiar communication styles, missing subtle cues that a different approach is needed.\nThere can be a tendency to rely on assumptions about other cultures rather than pausing to learn or ask questions.\nBuilding greater awareness of cross-cultural norms and practising adaptive strategies will expand your effectiveness in global or multi-cultural settings.",
        "Low / Limited": "You often default to familiar communication styles, missing important cues that a different approach is needed.\nThere is a frequent tendency to rely on assumptions about other cultures rather than pausing to learn or ask questions.\nEstablishing greater awareness of cross-cultural norms and consistently practising adaptive strategies will be essential to operate effectively in global or multi-cultural settings."
    },
    "EP": {
        "Developing": "In high-pressure situations, you may at times focus more on tasks than on understanding the emotional context, which can erode trust.\nAt times you may listen without fully integrating what you have heard into next steps, missing chances to strengthen collaboration.\nDeliberately pausing to explore how others experience a situation, and how that should shape your response, will deepen relationships and improve outcomes.",
        "Low / Limited": "In high-pressure situations, you often focus on tasks rather than understanding the emotional context, which erodes trust.\nYou may listen without integrating what you have heard into next steps, which repeatedly misses chances to strengthen collaboration.\nEstablishing a deliberate pause to explore how others experience a situation, and allowing that to shape your response, is essential to repair relationships and improve outcomes."
    }
}

# PR texts (pre-split)
PR_TEXTS = {
    "DT": "Practise concise \"what–why–next\" framing in meetings to improve clarity and focus.\nSeek regular feedback on the clarity of both written and verbal messages to identify blind spots.\nRole-play challenging conversations with a mentor or coach to build skill and confidence under pressure.",
    "TR": "Schedule brief relationship-building check-ins during busy projects to strengthen trust without losing momentum.\nBalance meeting agendas to include both task updates and discussions about team well-being and collaboration.\nReflect weekly on recent interactions to ensure neither task completion nor relationship maintenance is being overlooked.",
    "CO": "Use the S.C.O.P.E. Feedforward Model™ or similar forward-facing methods to reframe conflicts as shared problem-solving opportunities.\nDebrief conflicts quickly and constructively to capture lessons and prevent repetition without assigning blame.\nPractise early, low-stakes conflict conversations, starting with minor disagreements to build confidence and reduce escalation.",
    "CA": "Before key meetings, research the cultural norms and communication preferences of stakeholders or teams you'll engage with.\nObserve and adapt to subtle verbal and non-verbal cues in new settings, adjusting style to maintain inclusivity.\nSeek regular cross-cultural experiences or mentorship (e.g., international projects, diverse team collaborations) to broaden adaptive range.",
    "EP": "Pause to paraphrase others' viewpoints before responding, ensuring their perspective is accurately understood.\nPractise a \"day-in-the-life\" reflection, imagining issues from a colleague's or stakeholder's perspective to build deeper empathy.\nAsk open-ended, curiosity-driven questions in meetings to surface perspectives that might otherwise remain hidden."
}


def one_dp_half_up(score: float) -> str:
    """Format score to 1 decimal place using ROUND_HALF_UP."""
    if score is None:
        return "N/A"
    return str(Decimal(str(score)).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP))


def get_band(score: float) -> str:
    """Get band label for a score."""
    if score is None:
        return "Unknown"

    # Updated thresholds for spec compliance
    if score >= 4.5:
        return "Very High"
    elif score >= 3.5:
        return "High"
    elif score >= 2.5:
        return "Moderate / Balanced"
    elif score >= 1.5:
        return "Developing"
    else:
        return "Low / Limited"


def format_score_cell(score: float, dim: str) -> str:
    """Format score cell with interpretation."""
    if score is None:
        return "N/A"
    
    band = get_band(score)
    band = normalize_band_label(band)
    
    interp = SCORE_INTERP.get(dim, {}).get(band, "")
    if not interp:
        interp = "Score interpretation not available"
    
    # Take first sentence only
    first_sentence = interp.split('.')[0] + '.' if '.' in interp else interp
    
    return f"{score:.2f} - {first_sentence}"


def build_scores_with_bands(scores: Dict[str, float]) -> List[Tuple[str, float, str]]:
    """Build scores with bands list in DIM_ORDER."""
    result = []
    for dim in DIM_ORDER:
        if dim in scores and scores[dim] is not None:
            score = scores[dim]
            band = get_band(score)
            result.append((dim, score, band))
    return result


def format_body_to_three_lines(text: str) -> str:
    """Convert paragraph to exactly 3 lines by splitting on sentence/semicolon boundaries."""
    if not text:
        return ""

    # Split on sentence endings and semicolons
    segments = []
    current = ""

    for char in text:
        current += char
        if char in '.;' and current.strip():
            segments.append(current.strip())
            current = ""

    # Add any remaining text
    if current.strip():
        segments.append(current.strip())

    # Take first three segments, pad if needed
    while len(segments) < 3:
        segments.append("")

    return "\n".join(segments[:3])


def select_key_strengths(scores: Dict[str, float]) -> List[Tuple[str, str, str, str]]:
    """
    Select top 3 key strengths (High/Very High only).
    Returns list of (dim, icon_key, title, body) tuples.
    """
    scores_with_bands = build_scores_with_bands(scores)

    # Filter for High/Very High bands
    ks_candidates = [(dim, score, band) for dim, score, band in scores_with_bands
                     if band in ["High", "Very High"]]

    # Sort by score DESC, then by DIM_ORDER
    ks_candidates.sort(key=lambda x: (-x[1], DIM_ORDER.index(x[0])))

    result = []
    for dim, score, band in ks_candidates[:3]:
        icon_key = "LEVEL_SHIELD"  # Real KS items use shield
        title = f"{DIMENSION_LABELS[dim]} - {one_dp_half_up(score)}"
        body_text = KS_TEXTS.get(dim, {}).get(band, "")
        body = format_body_to_three_lines(body_text)
        result.append((dim, icon_key, title, body))

    # Check if all placeholders
    all_placeholders = len(result) == 0

    # Pad with placeholders
    while len(result) < 3:
        icon_key = "LEVEL_TOOLS"  # Placeholders use tools
        if all_placeholders:
            title = "No key strengths were identified."
        else:
            title = "No additional key strengths were identified."
        body = "This reflects limited positive signals in this cycle, interpret with caution."
        result.append(("", icon_key, title, body))

    return result


def select_development_areas(scores: Dict[str, float]) -> List[Tuple[str, str, str, str]]:
    """
    Select top 3 development areas (Developing/Low only).
    Returns list of (dim, icon_key, title, body) tuples.
    """
    scores_with_bands = build_scores_with_bands(scores)

    # Filter for Developing/Low bands
    da_candidates = [(dim, score, band) for dim, score, band in scores_with_bands
                     if band in ["Developing", "Low / Limited"]]

    # Sort by score ASC, then by DIM_ORDER
    da_candidates.sort(key=lambda x: (x[1], DIM_ORDER.index(x[0])))

    result = []
    for dim, score, band in da_candidates[:3]:
        # DA icon logic: Developing -> SEEDLING, Low/Limited -> TOOLS
        if band == "Developing":
            icon_key = "LEVEL_SEEDLING"
        else:  # Low / Limited
            icon_key = "LEVEL_TOOLS"

        title = f"{DIMENSION_LABELS[dim]} - {one_dp_half_up(score)}"
        body_text = DA_TEXTS.get(dim, {}).get(band, "")
        body = format_body_to_three_lines(body_text)
        result.append((dim, icon_key, title, body))

    # Check if all placeholders
    all_placeholders = len(result) == 0

    # Pad with placeholders
    while len(result) < 3:
        icon_key = "LEVEL_TOOLS"  # Placeholders use tools
        if all_placeholders:
            title = "No developmental areas were identified."
        else:
            title = "No additional developmental areas were identified."
        body = "This reflects limited positive signals in this cycle, interpret with caution."
        result.append(("", icon_key, title, body))

    return result


def select_priority_recommendations(scores: Dict[str, float], da_dims: List[str]) -> List[Tuple[str, str, str]]:
    """
    Select 3 priority recommendations.
    Start with DA dims, then lowest remaining dims.
    Returns list of (dim, title, body) tuples.
    """
    used_dims = set()
    result = []
    
    # First, add DA dimensions (non-placeholders)
    for dim in da_dims:
        if dim and dim not in used_dims:
            title = DIMENSION_LABELS[dim]
            body = PR_TEXTS.get(dim, "")
            if body:
                result.append((dim, title, body))
                used_dims.add(dim)
    
    # Then add lowest remaining dimensions
    remaining = []
    for dim in DIM_ORDER:
        if dim not in used_dims and dim in scores and scores[dim] is not None:
            remaining.append((dim, scores[dim]))
    
    # Sort by score ASC
    remaining.sort(key=lambda x: x[1])
    
    for dim, score in remaining:
        if len(result) >= 3:
            break
        title = DIMENSION_LABELS[dim]
        body = PR_TEXTS.get(dim, "")
        if body:
            result.append((dim, title, body))
            used_dims.add(dim)
    
    # Ensure exactly 3
    while len(result) < 3:
        # Find first unused dimension
        for dim in DIM_ORDER:
            if dim not in used_dims:
                title = DIMENSION_LABELS[dim]
                body = PR_TEXTS.get(dim, "")
                if body:
                    result.append((dim, title, body))
                    used_dims.add(dim)
                    break
        if len(result) < 3:
            # Fallback if somehow we don't have enough
            result.append(("", "Development Priority", "Continue developing communication skills through practice and feedback."))
    
    return result[:3]


def _and_join(items: List[str], final_word: str = "and") -> str:
    """Join list with commas and final word (e.g., 'A, B, and C')."""
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} {final_word} {items[1]}"
    return f"{', '.join(items[:-1])}, {final_word} {items[-1]}"


def _top_strength_dims(scores: Dict[str, float]) -> List[str]:
    """Get top strength dimensions (High/Very High bands)."""
    strengths = []
    for dim in DIM_ORDER:
        if dim in scores and scores[dim] is not None:
            band = get_band(scores[dim])
            if band in ["High", "Very High"]:
                strengths.append((scores[dim], dim))

    # Sort by score DESC, then by DIM_ORDER
    strengths.sort(key=lambda x: (-x[0], DIM_ORDER.index(x[1])))
    return [dim for _, dim in strengths[:3]]


def _dev_priority_dims(scores: Dict[str, float]) -> List[str]:
    """Get development priority dimensions (Developing/Low bands)."""
    priorities = []
    for dim in DIM_ORDER:
        if dim in scores and scores[dim] is not None:
            band = get_band(scores[dim])
            if band in ["Developing", "Low / Limited"]:
                priorities.append((scores[dim], dim))

    # Sort by score ASC, then by DIM_ORDER
    priorities.sort(key=lambda x: (x[0], DIM_ORDER.index(x[1])))
    return [dim for _, dim in priorities[:3]]


def build_summary(scores: Dict[str, float]) -> str:
    """Build 3-sentence deterministic summary."""
    if not scores or not any(v is not None for v in scores.values()):
        return "Your results indicate a balanced profile across dimensions. Continue developing your capabilities through practice and feedback. Focus on situations that challenge you to grow while leveraging your existing strengths."

    strength_dims = _top_strength_dims(scores)
    dev_dims = _dev_priority_dims(scores)

    # Sentence 1: Top strengths
    if strength_dims:
        strength_labels = [DIMENSION_LABELS[dim] for dim in strength_dims]
        sentence1 = f"Your strongest areas are {_and_join(strength_labels)}."
    else:
        sentence1 = "Your profile shows balanced capabilities across the measured dimensions."

    # Sentence 2: Development priorities
    if dev_dims:
        dev_labels = [DIMENSION_LABELS[dim] for dim in dev_dims]
        sentence2 = f"Priority development areas include {_and_join(dev_labels)}."
    else:
        sentence2 = "Continue refining your skills through deliberate practice and seeking feedback."

    # Sentence 3: Actionable guidance
    if dev_dims:
        sentence3 = "Focus on targeted practice in these areas while leveraging your strengths to build confidence and momentum."
    else:
        sentence3 = "Look for opportunities that stretch your capabilities while maintaining your current effectiveness."

    return f"{sentence1} {sentence2} {sentence3}"


def format_body_lines(text: str) -> str:
    """Format body text into exactly 3 lines using Alt+Enter breaks."""
    if not text:
        return ""

    # Text is already pre-split with \n
    lines = text.split('\n')

    # Ensure exactly 3 lines
    while len(lines) < 3:
        lines.append("")

    # Join with newline (will be converted to Alt+Enter in Excel)
    return '\n'.join(lines[:3])


def validate_schema_compliance(df: pd.DataFrame) -> None:
    """
    Comprehensive schema validation with detailed logging.
    Raises AssertionError if schema doesn't match exactly.
    """
    # Check column count
    if len(df.columns) != len(REQUIRED_COLUMNS):
        error_msg = f"Schema violation: Expected {len(REQUIRED_COLUMNS)} columns, got {len(df.columns)}"
        logger.error(error_msg)
        raise AssertionError(error_msg)

    # Check column order and names
    mismatches = []
    for i, (actual, required) in enumerate(zip(df.columns, REQUIRED_COLUMNS)):
        if actual != required:
            mismatches.append(f"Column {i}: '{actual}' != '{required}'")

    if mismatches:
        error_msg = f"Schema column mismatches: {'; '.join(mismatches)}"
        logger.error(error_msg)
        raise AssertionError(error_msg)

    # Success logging
    logger.info(f"Schema validation passed: {len(REQUIRED_COLUMNS)} columns match exactly")


def validate_col_against_required(df: pd.DataFrame) -> bool:
    """Validate dataframe columns match REQUIRED_COLUMNS."""
    if len(df.columns) != len(REQUIRED_COLUMNS):
        logger.error(f"Column count mismatch: {len(df.columns)} vs {len(REQUIRED_COLUMNS)} required")
        return False
    
    for i, req_col in enumerate(REQUIRED_COLUMNS):
        if i >= len(df.columns):
            logger.error(f"Missing column at index {i}: {req_col}")
            return False
        actual = df.columns[i]
        if actual != req_col:
            logger.warning(f"Column mismatch at {i}: '{actual}' vs required '{req_col}'")
    
    return True


def compose_workbook(survey_df: pd.DataFrame, output_path: Path,
                    start_idx: int, end_idx: int, src_path: Optional[str] = None) -> bool:
    """
    Main orchestration function to compose the CCIP workbook.
    Returns True if successful.
    """
    # Derive Date column if needed
    date_series = derive_date_column(survey_df, src_path)

    # Create enhanced dataframe with Date column for processing
    enhanced_df = survey_df.copy()
    enhanced_df['Date'] = date_series

    # Create output dataframe with required columns
    output_data = []
    
    # Create temp directory for images
    temp_dir = Path(tempfile.mkdtemp(prefix="ccip_"))
    logger.info(f"Created temp directory: {temp_dir}")
    
    try:
        # Process each survey row
        for idx, row in enhanced_df.iterrows():
            # Skip rows without valid ID and Email
            if pd.isna(row.get('ID')) or pd.isna(row.get('Email')):
                continue
            
            # Process survey responses
            processed = process_survey_row(row, start_idx, end_idx)
            scores_raw_1_7 = processed['scores']
            if not any(v is not None for v in scores_raw_1_7.values()):
                continue
            scores = _scale_and_clamp_scores_0_5(scores_raw_1_7)
            # guard
            for dim in ["DT","TR","CO","CA","EP"]:
                s = scores.get(dim)
                if s is not None:
                    assert 0.0 <= s <= 5.0, f"{dim} out of range after scaling: {s}"
            
            # Select KS, DA, PR using new format
            ks_items = select_key_strengths(scores)
            da_items = select_development_areas(scores)
            da_dims = [dim for dim, _, _, _ in da_items if dim]
            pr_items = select_priority_recommendations(scores, da_dims)
            
            # Build output row strictly from REQUIRED_COLUMNS
            out_row = {}

            # Core fields
            out_row["ID"] = processed['ID']
            out_row["Email"] = processed['Email']
            out_row["Date"] = row['Date']  # Use derived date directly
            out_row["Name"] = row.get('Name', '')
            # NOTE: Organisation, Level, Level Icon, Primary Focus Area not in locked schema

            # Score fields
            out_row["DT_Score"] = format_score_cell(scores.get('DT'), 'DT')
            out_row["TR_Score"] = format_score_cell(scores.get('TR'), 'TR')
            out_row["CO_Score"] = format_score_cell(scores.get('CO'), 'CO')
            out_row["CA_Score"] = format_score_cell(scores.get('CA'), 'CA')
            out_row["EP_Score"] = format_score_cell(scores.get('EP'), 'EP')

            # Visual fields
            out_row["Radar_Chart"] = ""  # Will be filled with image
            out_row["Summary"] = build_summary(scores)

            # KS items (dim, icon_key, title, body)
            for i, (dim, icon_key, title, body) in enumerate(ks_items, 1):
                out_row[f"KS{i}_Icon"] = ""  # Will be filled with image
                out_row[f"KS{i}_Title"] = title
                out_row[f"KS{i}_Body"] = body

            # DA items (dim, icon_key, title, body)
            for i, (dim, icon_key, title, body) in enumerate(da_items, 1):
                out_row[f"DA{i}_Icon"] = ""  # Will be filled with image
                out_row[f"DA{i}_Title"] = title
                out_row[f"DA{i}_Body"] = body

            # PR items (unchanged format)
            for i, (dim, title, body) in enumerate(pr_items, 1):
                out_row[f"PR{i}_Icon"] = ""  # Will be filled with image
                out_row[f"PR{i}_Title"] = title
                out_row[f"PR{i}_Body"] = format_body_lines(body)

            # RQ fields (placeholder for future use)
            out_row["RQ1"] = ""
            out_row["RQ2"] = ""
            out_row["RQ3"] = ""
            out_row["RQ4"] = ""

            output_data.append(out_row)
        
        # Schema guardrails: ensure only REQUIRED_COLUMNS
        output_rows = [{k: row_dict.get(k, "") for k in REQUIRED_COLUMNS} for row_dict in output_data]

        # Create DataFrame with locked schema
        result_df = pd.DataFrame(output_rows, columns=REQUIRED_COLUMNS)

        # Enhanced schema validation
        validate_schema_compliance(result_df)
        
        # Write to Excel with images
        with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
            result_df.to_excel(writer, sheet_name='CCIP Results', index=False)
            worksheet = writer.sheets['CCIP Results']
            workbook = writer.book
            
            # Format settings
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#4A90E2',
                'font_color': 'white',
                'align': 'center',
                'valign': 'vcenter'
            })
            
            # Apply header format
            for col_num, value in enumerate(result_df.columns):
                worksheet.write(0, col_num, value, header_format)
            
            # Set column widths per spec
            worksheet.set_column(COL['Date'], COL['Email'], 18)  # Meta columns (Date, ID, Name, Email)
            worksheet.set_column(COL['DT_Score'], COL['EP_Score'], 20)  # Score columns
            worksheet.set_column(COL['Summary'], COL['Summary'], 35)  # Summary
            worksheet.set_column(COL['Radar_Chart'], COL['Radar_Chart'], 40)  # Radar Chart (wider for high-res)

            # KS block: Icon/Title/Body
            for i in range(1, 4):
                icon_col = COL[f"KS{i}_Icon"]
                title_col = COL[f"KS{i}_Title"]
                body_col = COL[f"KS{i}_Body"]
                worksheet.set_column(icon_col, icon_col, 12)  # Icon
                worksheet.set_column(title_col, title_col, 28)  # Title
                worksheet.set_column(body_col, body_col, 36)  # Body

            # DA block: Icon/Title/Body
            for i in range(1, 4):
                icon_col = COL[f"DA{i}_Icon"]
                title_col = COL[f"DA{i}_Title"]
                body_col = COL[f"DA{i}_Body"]
                worksheet.set_column(icon_col, icon_col, 12)  # Icon
                worksheet.set_column(title_col, title_col, 28)  # Title
                worksheet.set_column(body_col, body_col, 36)  # Body

            # PR block: Icon/Title/Body
            for i in range(1, 4):
                icon_col = COL[f"PR{i}_Icon"]
                title_col = COL[f"PR{i}_Title"]
                body_col = COL[f"PR{i}_Body"]
                worksheet.set_column(icon_col, icon_col, 12)  # Icon
                worksheet.set_column(title_col, title_col, 28)  # Title
                worksheet.set_column(body_col, body_col, 36)  # Body
            
            # Set row heights for image rows (taller for high-res radar)
            for row_idx in range(1, len(result_df) + 1):
                worksheet.set_row(row_idx, 160)  # Taller rows so scaled radar doesn't look cramped
            
            # Embed images for each row
            for row_idx, row_data in enumerate(output_data):
                excel_row = row_idx + 1  # Skip header

                # Reprocess this row to get KS/DA/PR items with icon keys
                row = survey_df.iloc[row_idx]
                processed = process_survey_row(row, start_idx, end_idx)
                scores_raw_1_7 = processed['scores']
                if not any(v is not None for v in scores_raw_1_7.values()):
                    continue
                scores = _scale_and_clamp_scores_0_5(scores_raw_1_7)
                # guard
                for dim in ["DT","TR","CO","CA","EP"]:
                    s = scores.get(dim)
                    if s is not None:
                        assert 0.0 <= s <= 5.0, f"{dim} out of range after scaling: {s}"

                ks_items = select_key_strengths(scores)
                da_items = select_development_areas(scores)
                da_dims = [dim for dim, _, _, _ in da_items if dim]
                pr_items = select_priority_recommendations(scores, da_dims)

                # NOTE: Level_Icon removed from locked schema

                # KS icons - STRICT: Real dimension → LEVEL_SHIELD, Placeholder → LEVEL_TOOLS
                for i, (dim, icon_key, title, body) in enumerate(ks_items, 1):
                    col_key = f"KS{i}_Icon"
                    if col_key in COL:
                        safe_render_and_embed_icon(worksheet, excel_row, COL[col_key],
                                                  icon_key, temp_dir, f"ks{i}", scale=1.0)

                # DA icons - STRICT: Developing → LEVEL_SEEDLING, Low/Limited or placeholder → LEVEL_TOOLS
                for i, (dim, icon_key, title, body) in enumerate(da_items, 1):
                    col_key = f"DA{i}_Icon"
                    if col_key in COL:
                        safe_render_and_embed_icon(worksheet, excel_row, COL[col_key],
                                                  icon_key, temp_dir, f"da{i}", scale=1.0)

                # Radar chart - extract scores in order [DT, TR, CO, CA, EP]
                participant_scores = []
                for dim in DIM_ORDER:
                    score_val = scores.get(dim)  # Use actual scores, not formatted
                    if score_val is not None:
                        participant_scores.append(score_val)
                    else:
                        participant_scores.append(0.0)  # Default for missing scores

                if len(participant_scores) == 5:  # Ensure we have exactly 5 scores
                    radar_svg = generate_radar_chart_svg_scaled(participant_scores)
                    png_path = insert_radar(
                        worksheet, excel_row, COL['Radar_Chart'],
                        radar_svg, temp_dir, base_name=f"radar_{processed['ID']}",
                        out_w=RADAR_PNG_W, out_h=RADAR_PNG_H, scale=1.0, move_with_cells=True
                    )
                
                # PR icons - STRICT: Use green dimension icons (PR_DT, PR_TR, PR_CO, PR_CA, PR_EP)
                for i, (dim, title, body) in enumerate(pr_items, 1):
                    if dim:
                        pr_icon_key = f"PR_{dim}"
                        col_key = f"PR{i}_Icon"
                        if col_key in COL:
                            safe_render_and_embed_icon(worksheet, excel_row, COL[col_key],
                                                      pr_icon_key, temp_dir, f"pr{i}", scale=1.0)
        
        logger.info(f"Workbook created successfully at {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error creating workbook: {e}")
        return False
        
    finally:
        # Clean up temp directory
        try:
            import shutil
            shutil.rmtree(temp_dir)
            logger.info(f"Cleaned up temp directory: {temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to clean temp directory: {e}")