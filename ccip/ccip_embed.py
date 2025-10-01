"""CairoSVG-only rendering and Excel embedding utilities for CCIP."""

import io
import logging
import tempfile
from pathlib import Path
from typing import Optional

import cairosvg
from PIL import Image

logger = logging.getLogger(__name__)

# --- Canonical PNG output parameters ---
PNG_ICON_SIZE = 1000        # was 600. Bigger, crisper icons.
PNG_DPI = (144, 144)

# Radar target output (match our SVG generator defaults)
RADAR_PNG_W = 2160
RADAR_PNG_H = 1680


def svg_to_png(svg_content: str, width: int = 600, height: int = 600) -> Optional[bytes]:
    """
    Convert SVG to PNG using CairoSVG with exactly one automatic retry.
    Returns PNG bytes or None if both attempts fail.
    """
    for attempt in range(2):
        try:
            png_bytes = cairosvg.svg2png(
                bytestring=svg_content.encode('utf-8'),
                output_width=width,
                output_height=height,
                dpi=144
            )
            return png_bytes
        except Exception as e:
            if attempt == 0:
                logger.warning(f"First CairoSVG attempt failed: {e}. Retrying...")
                continue
            else:
                logger.error(f"CairoSVG failed after retry: {e}")
                return None
    return None


def normalize_png(png_bytes: bytes) -> bytes:
    """Normalize PNG to ensure consistent format."""
    try:
        img = Image.open(io.BytesIO(png_bytes))
        output = io.BytesIO()
        img.save(output, format='PNG', optimize=False)
        return output.getvalue()
    except Exception as e:
        logger.error(f"PNG normalization failed: {e}")
        return png_bytes


def ensure_png_rgba_dpi(png_bytes: bytes, target_dpi: int = 144) -> bytes:
    """Ensure PNG is in RGBA mode with correct DPI."""
    try:
        img = Image.open(io.BytesIO(png_bytes))
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        output = io.BytesIO()
        img.save(output, format='PNG', dpi=(target_dpi, target_dpi))
        return output.getvalue()
    except Exception as e:
        logger.error(f"PNG RGBA/DPI conversion failed: {e}")
        return png_bytes


def anchor_options(scale: float,
                   move_with_cells: bool = True,
                   x_offset: int = 2,
                   y_offset: int = 2) -> dict:
    return {
        "object_position": 2 if move_with_cells else 3,
        "x_scale": scale,
        "y_scale": scale,
        "x_offset": x_offset,
        "y_offset": y_offset,
    }

def insert_png(ws, row: int, col: int, png_path: str,
               scale: float = 1.00,            # was 0.20 — embed at 1:1
               move_with_cells: bool = True) -> None:
    ws.insert_image(row, col, png_path, anchor_options(scale, move_with_cells))


def embed_icon(worksheet, row: int, col: int, icon_factory_func, temp_dir: Path,
               width: int = 100, height: int = 100) -> bool:
    """
    Embed an icon from a factory function into Excel worksheet.

    All icons are normalized to 100×100px base size regardless of source viewBox
    for consistent visual weight. Default width/height changed to 100.

    Returns True if successful, False otherwise.
    """
    try:
        # Get SVG from factory
        svg_content = icon_factory_func()

        # Convert to PNG at standard size (default 100x100)
        png_bytes = svg_to_png(svg_content, width, height)
        if png_bytes is None:
            logger.error(f"Icon embedding failed: CairoSVG conversion failed")
            return False

        # Normalize and ensure RGBA
        png_bytes = ensure_png_rgba_dpi(normalize_png(png_bytes))

        # Save to temp file
        temp_path = temp_dir / f"icon_{row}_{col}.png"
        temp_path.write_bytes(png_bytes)

        # Insert into worksheet with equal scaling and object_position=2
        worksheet.insert_image(row, col, str(temp_path), {
            'x_scale': 0.20,
            'y_scale': 0.20,
            'object_position': 2,
            'x_offset': 5,
            'y_offset': 5
        })
        return True
    except Exception as e:
        logger.error(f"Icon embedding failed at ({row}, {col}): {e}")
        return False


def embed_radar(worksheet, row: int, col: int, svg_content: str, temp_dir: Path,
                width: int = 300, height: int = 300) -> bool:
    """
    Embed a radar chart SVG into Excel worksheet.
    Returns True if successful, False otherwise.
    """
    try:
        # Convert to PNG
        png_bytes = svg_to_png(svg_content, width, height)
        if png_bytes is None:
            logger.error(f"Radar embedding failed: CairoSVG conversion failed")
            return False
        
        # Normalize and ensure RGBA
        png_bytes = ensure_png_rgba_dpi(normalize_png(png_bytes))
        
        # Save to temp file
        temp_path = temp_dir / f"radar_{row}_{col}.png"
        temp_path.write_bytes(png_bytes)
        
        # Insert into worksheet
        worksheet.insert_image(row, col, str(temp_path), {
            'x_scale': 0.7, 'y_scale': 0.7
        })
        return True
    except Exception as e:
        logger.error(f"Radar embedding failed at ({row}, {col}): {e}")
        return False


def safe_render_and_embed_icon(worksheet, row: int, col: int, icon_key: str,
                              temp_dir: Path, base_name: str, scale: float = 0.20):
    """
    Safely render and embed icon with error handling and size normalization.

    All icons are normalized to 100×100px base size regardless of source viewBox,
    then scaled by the scale parameter. This ensures consistent visual weight.

    Returns True if successful, False on any error.
    """
    try:
        # Import here to avoid circular imports
        from .svg_icons_radar import ICONS

        # Check if icon key exists and is callable
        if icon_key not in ICONS:
            logger.error(f"Icon key '{icon_key}' not found in ICONS registry")
            return False

        icon_factory = ICONS[icon_key]
        if not callable(icon_factory):
            logger.error(f"Icon key '{icon_key}' is not callable")
            return False

        # Get SVG content
        svg_content = icon_factory()

        # CRITICAL: Standard output size regardless of source viewBox
        # Exception: LINE_ICON preserves its original aspect ratio (3783x21)
        if icon_key == 'LINE_ICON':
            # Line icon: preserve horizontal aspect ratio, use larger width
            png_bytes = svg_to_png(svg_content, width=600, height=4)
        else:
            STANDARD_SIZE = 100  # pixels
            # Convert to PNG at standard size with retry
            # This ensures all icons render at consistent 100x100px base size
            png_bytes = svg_to_png(svg_content, width=STANDARD_SIZE, height=STANDARD_SIZE)
        if png_bytes is None:
            logger.error(f"Failed to convert SVG to PNG for icon '{icon_key}'")
            return False

        # Normalize PNG
        png_bytes = ensure_png_rgba_dpi(normalize_png(png_bytes))

        # Save to temp file
        temp_path = temp_dir / f"{base_name}_{row}_{col}.png"
        temp_path.write_bytes(png_bytes)

        # Insert into worksheet with scaling applied after normalization
        worksheet.insert_image(row, col, str(temp_path), {
            'x_scale': scale,
            'y_scale': scale,
            'object_position': 2,
            'x_offset': 5,  # Center horizontally in cell
            'y_offset': 5   # Center vertically in cell
        })

        if icon_key == 'LINE_ICON':
            logger.debug(f"Embedded {icon_key} at ({row},{col}) - "
                        f"600x4px (preserved aspect ratio), scale={scale}")
        else:
            logger.debug(f"Embedded {icon_key} at ({row},{col}) - "
                        f"normalized to {STANDARD_SIZE}px, scale={scale}")
        return True

    except Exception as e:
        logger.error(f"Failed to render and embed icon '{icon_key}' at ({row}, {col}): {e}")
        return False


def normalize_band_label(label: str) -> str:
    """Normalize band labels to consistent format."""
    label = label.strip()

    # Handle Low/Limited variations
    if label.lower() in ['low', 'limited', 'low / limited', 'low/limited']:
        return 'Low / Limited'

    # Handle Moderate/Balanced variations
    if label.lower() in ['moderate', 'balanced', 'moderate / balanced', 'moderate/balanced']:
        return 'Moderate / Balanced'

    # Handle other standard labels
    label_map = {
        'developing': 'Developing',
        'high': 'High',
        'very high': 'Very High',
        'veryhigh': 'Very High',
        'very_high': 'Very High'
    }

    return label_map.get(label.lower(), label.title())


def render_and_embed_svg(ws, row: int, col: int, svg_text: str, tmp_dir: str,
                        base_name: str, *, out_w: int = RADAR_PNG_W, out_h: int = RADAR_PNG_H,
                        scale: float = 1.0, move_with_cells: bool = True) -> str:
    """
    Render high-res SVG to PNG and embed at full resolution into worksheet.
    Returns path to the final PNG for external use.
    """
    try:
        # Convert SVG to high-res PNG
        png_bytes = svg_to_png(svg_text, out_w, out_h)
        if png_bytes is None:
            logger.error(f"SVG to PNG conversion failed for {base_name}")
            return ""

        # Normalize and ensure RGBA @ 144 DPI
        png_bytes = ensure_png_rgba_dpi(normalize_png(png_bytes), target_dpi=144)

        # Save to temp file
        temp_path = Path(tmp_dir) / f"{base_name}.png"
        temp_path.write_bytes(png_bytes)

        # Insert into worksheet at full resolution
        insert_png(ws, row, col, str(temp_path), scale=scale, move_with_cells=move_with_cells)

        logger.info(f"Full-res image embedded at ({row}, {col}): {temp_path}")
        return str(temp_path)

    except Exception as e:
        logger.error(f"render_and_embed_svg failed for {base_name}: {e}")
        return ""


def insert_radar(ws, row: int, col: int, svg_text: str, tmp_dir: str,
                 base_name: str, *, out_w: int = RADAR_PNG_W, out_h: int = RADAR_PNG_H,
                 scale: float = 1.0, move_with_cells: bool = True) -> str:
    """
    Render high-res radar (144 DPI) and insert at full resolution into the sheet.
    Returns path to the final PNG (useful for exporting a copy).
    """
    return render_and_embed_svg(
        ws, row, col, svg_text, tmp_dir, base_name,
        out_w=out_w, out_h=out_h, scale=scale, move_with_cells=move_with_cells
    )