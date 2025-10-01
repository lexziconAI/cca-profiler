#!/usr/bin/env python3
"""
Normalize SVG icons to square viewBoxes with maximally-sized, centered artwork.

This script:
1. Parses SVG icon functions from svg_icons_radar.py
2. Normalizes non-square icons to square viewBoxes
3. Centers artwork with appropriate padding
4. Preserves original aspect ratios
5. Excludes radar/line icons (intentionally non-square)
"""

import re
import sys
from pathlib import Path
from typing import Optional, Tuple
import xml.etree.ElementTree as ET


def parse_svg_viewbox(svg_content: str) -> Optional[Tuple[float, float, float, float]]:
    """Extract viewBox as (x, y, width, height)."""
    match = re.search(r'viewBox=["\']([^"\']+)["\']', svg_content)
    if not match:
        return None

    parts = match.group(1).split()
    if len(parts) != 4:
        return None

    try:
        return tuple(float(p) for p in parts)
    except ValueError:
        return None


def extract_path_bounds(svg_content: str) -> Optional[Tuple[float, float, float, float]]:
    """
    Extract bounding box from all path elements.
    Returns (min_x, min_y, max_x, max_y).
    """
    paths = re.findall(r'd=["\']([^"\']+)["\']', svg_content)
    if not paths:
        return None

    all_coords = []
    for path in paths:
        # Extract numeric coordinates
        coords = re.findall(r'-?\d+\.?\d*', path)
        all_coords.extend([float(c) for c in coords])

    if len(all_coords) < 2:
        return None

    x_coords = all_coords[0::2]
    y_coords = all_coords[1::2]

    return (min(x_coords), min(y_coords), max(x_coords), max(y_coords))


def normalize_svg_icon(svg_content: str, func_name: str) -> str:
    """
    Normalize SVG to square viewBox with centered artwork.

    Algorithm:
    1. Extract current viewBox and artwork bounds
    2. Calculate target square size = max(artwork_width, artwork_height)
    3. Calculate padding to center artwork
    4. Adjust viewBox to "0 0 square_size square_size"
    5. Transform all paths to shift artwork by padding offsets
    """
    # Parse current viewBox
    viewbox = parse_svg_viewbox(svg_content)
    if not viewbox:
        print(f"  WARNING: {func_name} - No viewBox found, skipping")
        return svg_content

    vb_x, vb_y, vb_w, vb_h = viewbox

    # Extract artwork bounds
    bounds = extract_path_bounds(svg_content)
    if not bounds:
        print(f"  WARNING: {func_name} - Could not extract path bounds, skipping")
        return svg_content

    min_x, min_y, max_x, max_y = bounds
    artwork_w = max_x - min_x
    artwork_h = max_y - min_y

    # Calculate target square size (maximize artwork)
    target_size = max(artwork_w, artwork_h)

    # Calculate padding needed to center artwork
    padding_x = (target_size - artwork_w) / 2
    padding_y = (target_size - artwork_h) / 2

    # Calculate translation needed
    # We want artwork to start at (padding_x, padding_y) instead of (min_x, min_y)
    translate_x = padding_x - min_x
    translate_y = padding_y - min_y

    print(f"  {func_name}:")
    print(f"    Old viewBox: {vb_w:.0f}×{vb_h:.0f}")
    print(f"    Artwork: {artwork_w:.0f}×{artwork_h:.0f}")
    print(f"    New viewBox: {target_size:.0f}×{target_size:.0f}")
    print(f"    Translation: ({translate_x:.1f}, {translate_y:.1f})")

    # Update viewBox
    new_viewbox = f'0 0 {target_size:.0f} {target_size:.0f}'
    svg_content = re.sub(
        r'viewBox=["\'][^"\']+["\']',
        f'viewBox="{new_viewbox}"',
        svg_content
    )

    # Add transform to all path elements
    # Find all <path> tags and add transform attribute
    def add_transform(match):
        path_tag = match.group(0)
        # Check if transform already exists
        if 'transform=' in path_tag:
            # Update existing transform
            return re.sub(
                r'transform=["\']([^"\']*)["\']',
                f'transform="translate({translate_x:.2f},{translate_y:.2f}) \\1"',
                path_tag
            )
        else:
            # Add new transform before the closing >
            return path_tag.replace(
                '/>',
                f' transform="translate({translate_x:.2f},{translate_y:.2f})"/>'
            ).replace(
                '>',
                f' transform="translate({translate_x:.2f},{translate_y:.2f})">',
                1
            )

    svg_content = re.sub(r'<path[^>]*>', add_transform, svg_content)

    return svg_content


def normalize_all_icons():
    """Normalize all icons in svg_icons_radar.py."""
    icon_file = Path(__file__).parent / "ccip" / "svg_icons_radar.py"

    if not icon_file.exists():
        print(f"ERROR: Icon file not found: {icon_file}")
        sys.exit(1)

    content = icon_file.read_text()

    # Extract all icon functions
    icon_pattern = re.compile(
        r'(def (svg_\w+)\(\):\s+"""[^"]+"""\s+return\s+\'\'\'([^\']+)\'\'\')',
        re.MULTILINE | re.DOTALL
    )

    new_content = content
    normalized_count = 0

    for match in icon_pattern.finditer(content):
        full_match = match.group(1)
        func_name = match.group(2)
        svg_content = match.group(3)

        # Skip radar and line icons
        if 'radar' in func_name.lower() or 'line' in func_name.lower():
            print(f"SKIPPING {func_name} (radar/line icon - intentionally non-square)")
            continue

        # Normalize the SVG
        normalized_svg = normalize_svg_icon(svg_content, func_name)

        # Replace in content
        new_func = full_match.replace(svg_content, normalized_svg)
        new_content = new_content.replace(full_match, new_func)
        normalized_count += 1

    # Write back to file
    icon_file.write_text(new_content)

    print(f"\n✓ Normalized {normalized_count} icons")
    print(f"✓ Updated file: {icon_file}")
    return True


if __name__ == "__main__":
    print("=" * 80)
    print("SVG ICON NORMALIZATION")
    print("=" * 80)
    print()

    success = normalize_all_icons()
    sys.exit(0 if success else 1)
