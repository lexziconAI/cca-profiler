"""Radar chart generation for CCIP dimensions."""

import html
import math
import logging
from typing import Iterable, Dict

import numpy as np

logger = logging.getLogger(__name__)

# Global dimension labels
DIMENSION_LABELS = {
    "DT": "Directness & Transparency",
    "TR": "Task vs Relational Accountability",
    "CO": "Conflict Orientation",
    "CA": "Cultural Adaptability",
    "EP": "Empathy & Perspective-Taking"
}

DIMENSION_SHORT = {
    "DT": "DT",
    "TR": "TR",
    "CO": "CO",
    "CA": "CA",
    "EP": "EP"
}


def generate_radar_chart_svg_scaled(
    scores: Iterable[float],
    target_w: int = 2160,
    target_h: int = 1680,
    padding_px_base: int = 2,  # Will be overridden by dynamic padding
    label_mode: str = "full"  # "short" or "full"; default to "full"
) -> str:
    """
    Generate SVG radar chart with exactly 5 scores for [DT, TR, CO, CA, EP].
    Vertex order (clockwise starting top): DT, TR, CO, CA, EP.
    Angles (deg): [-90, -18, 54, 126, 198].
    """

    # Convert scores to list and validate exactly 5 scores
    score_list = list(scores)
    if len(score_list) != 5:
        logger.warning(f"Expected exactly 5 scores, got {len(score_list)}. Padding/truncating to 5.")
        # Pad with 0.0 or truncate to exactly 5
        if len(score_list) < 5:
            score_list.extend([0.0] * (5 - len(score_list)))
        else:
            score_list = score_list[:5]

    # Clamp each score to [0.0, 5.0], invalid → 0.0 with warning
    clamped_scores = []
    for i, score in enumerate(score_list):
        try:
            s = float(score)
            if not (0.0 <= s <= 5.0):
                logger.warning(f"Score {i} value {s} out of range [0.0, 5.0], clamping")
                s = max(0.0, min(5.0, s))
            clamped_scores.append(s)
        except (ValueError, TypeError):
            logger.warning(f"Score {i} value {score} invalid, using 0.0")
            clamped_scores.append(0.0)

    # Dimension keys and angles (degrees)
    dim_keys = ["DT", "TR", "CO", "CA", "EP"]
    angles_deg = [-90, -18, 54, 126, 198]
    angles_rad = [math.radians(a) for a in angles_deg]

    # Base dimensions for scaling
    BASE_W, BASE_H = 540.0, 420.0  # Base size to scale from
    scale = min(target_w / BASE_W, target_h / BASE_H)

    # Typography & sizing (scale to target at 2160x1680)
    # Target: Label font ≈ 42px, Tick font ≈ 34px at 2160x1680
    label_font_base = 10.5  # Will scale to ~42px at 2160x1680
    tick_font_base = 8.5    # Will scale to ~34px at 2160x1680

    label_font = label_font_base * scale
    tick_font = tick_font_base * scale

    # Grid and geometry
    grid_radius_base = 120.0  # Base radius
    grid_radius = grid_radius_base * scale

    # Stroke widths
    grid_stroke = 1.6 * scale
    axis_stroke = 1.6 * scale
    data_stroke = 3.0 * scale
    point_stroke = 1.8 * scale
    point_radius = 5.0 * scale

    # Colors
    text_color = "#1f2937"
    grid_fill = "#c6c6c6"
    grid_stroke_color = "#9ea3a8"
    axis_color = "#9ea3a8"
    data_fill = "#0099CC"
    data_stroke_color = "#0099CC"

    # Get dimension labels
    if label_mode == "short":
        label_source = DIMENSION_SHORT
    else:
        label_source = DIMENSION_LABELS

    labels = []
    for key in dim_keys:
        label_text = label_source.get(key, key)
        # XML escape the label
        escaped_label = html.escape(label_text)
        labels.append(escaped_label)

    # Helper functions
    def polar_to_cart(r: float, angle_rad: float) -> tuple:
        x = r * math.cos(angle_rad)
        y = r * math.sin(angle_rad)
        return x, y

    def estimate_text_width(text: str, font_size: float) -> float:
        return len(text) * font_size * 0.58

    # Calculate label positions and bounding boxes
    label_offset = 28.0 * scale
    label_positions = []
    label_boxes = []

    for i, (label, angle) in enumerate(zip(labels, angles_rad)):
        lx, ly = polar_to_cart(grid_radius + label_offset, angle)

        # Text width estimation
        text_width = estimate_text_width(label, label_font)
        text_height = label_font * 1.2

        # Anchor by cosine of angle
        cos_angle = math.cos(angle)
        if abs(cos_angle) < 0.25:  # Near vertical
            anchor = "middle"
            left = lx - text_width / 2
            right = lx + text_width / 2
        elif cos_angle > 0:  # Right side
            anchor = "start"
            left = lx
            right = lx + text_width
        else:  # Left side
            anchor = "end"
            left = lx - text_width
            right = lx

        top = ly - text_height / 2
        bottom = ly + text_height / 2

        label_positions.append((lx, ly, anchor))
        label_boxes.append((left, top, right, bottom))

    # Calculate bounding box of all labels and polygon
    all_lefts = [box[0] for box in label_boxes] + [-grid_radius]
    all_tops = [box[1] for box in label_boxes] + [-grid_radius]
    all_rights = [box[2] for box in label_boxes] + [grid_radius]
    all_bottoms = [box[3] for box in label_boxes] + [grid_radius]

    content_left = min(all_lefts)
    content_top = min(all_tops)
    content_right = max(all_rights)
    content_bottom = max(all_bottoms)

    # Dynamic padding calculation
    base_padding = 24.0 * scale

    # Ensure top padding ≥ 140px extra so top label never overlaps "5" tick
    min_top_padding = 140.0 * scale

    # Calculate needed padding
    padding_left = max(base_padding, -content_left)
    padding_right = max(base_padding, content_right)
    padding_top = max(base_padding, -content_top, min_top_padding)
    padding_bottom = max(base_padding, content_bottom)

    # ViewBox calculation
    viewbox_width = padding_left + padding_right
    viewbox_height = padding_top + padding_bottom
    viewbox_x = -padding_left
    viewbox_y = -padding_top

    # Grid rings (5 rings for scores 1-5)
    grid_levels = [1, 2, 3, 4, 5]
    ring_polygons = []

    for level in reversed(grid_levels):  # Draw from 5 to 1 for stacking
        ring_radius = (level / 5.0) * grid_radius
        ring_points = []
        for angle in angles_rad:
            x, y = polar_to_cart(ring_radius, angle)
            ring_points.append(f"{x:.2f},{y:.2f}")

        points_str = " ".join(ring_points)
        ring_polygons.append(f'<polygon points="{points_str}" fill="{grid_fill}" fill-opacity="0.15" stroke="none"/>')

    # Grid ring outlines
    ring_strokes = []
    for level in grid_levels:
        ring_radius = (level / 5.0) * grid_radius
        ring_points = []
        for angle in angles_rad:
            x, y = polar_to_cart(ring_radius, angle)
            ring_points.append(f"{x:.2f},{y:.2f}")

        points_str = " ".join(ring_points)
        ring_strokes.append(f'<polygon points="{points_str}" fill="none" stroke="{grid_stroke_color}" stroke-width="{grid_stroke:.2f}"/>')

    # Axis spokes
    axes = []
    for angle in angles_rad:
        x, y = polar_to_cart(grid_radius, angle)
        axes.append(f'<line x1="0" y1="0" x2="{x:.2f}" y2="{y:.2f}" stroke="{axis_color}" stroke-width="{axis_stroke:.2f}"/>')

    # Tick labels (1-5) on vertical axis only
    tick_elements = []
    vertical_angle = angles_rad[0]  # DT at -90 degrees (top)
    for level in grid_levels:
        tick_radius = (level / 5.0) * grid_radius
        tx, ty = polar_to_cart(tick_radius, vertical_angle)
        tick_elements.append(f'<text x="{tx:.2f}" y="{ty:.2f}" text-anchor="middle" dominant-baseline="central" font-size="{tick_font:.2f}" font-weight="700" fill="{text_color}">{level}</text>')

    # Data polygon
    data_points = []
    for i, score in enumerate(clamped_scores):
        data_radius = (score / 5.0) * grid_radius
        x, y = polar_to_cart(data_radius, angles_rad[i])
        data_points.append((x, y))

    data_points_str = " ".join([f"{x:.2f},{y:.2f}" for x, y in data_points])
    data_polygon = f'<polygon points="{data_points_str}" fill="{data_fill}" fill-opacity="0.32" stroke="{data_stroke_color}" stroke-width="{data_stroke:.2f}"/>'

    # Data points (circles)
    data_circles = []
    for x, y in data_points:
        data_circles.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{point_radius:.2f}" fill="{data_fill}" stroke="#ffffff" stroke-width="{point_stroke:.2f}"/>')

    # Labels
    label_elements = []
    for i, (label, (lx, ly, anchor)) in enumerate(zip(labels, label_positions)):
        label_elements.append(f'<text x="{lx:.2f}" y="{ly:.2f}" text-anchor="{anchor}" dominant-baseline="central" font-size="{label_font:.2f}" fill="{text_color}">{label}</text>')

    # Assemble SVG
    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{target_w}" height="{target_h}" viewBox="{viewbox_x:.2f} {viewbox_y:.2f} {viewbox_width:.2f} {viewbox_height:.2f}">
  <rect width="100%" height="100%" fill="white"/>
  <g>
    {''.join(ring_polygons)}
    {''.join(ring_strokes)}
    {''.join(axes)}
    {data_polygon}
    {''.join(data_circles)}
  </g>
  <g font-family="Arial, sans-serif">
    {''.join(tick_elements)}
    {''.join(label_elements)}
  </g>
</svg>'''

    return svg_content