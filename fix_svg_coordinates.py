#!/usr/bin/env python3
"""
Fix SVG icon positioning by removing transform wrappers and adjusting path coordinates.

Problem: Icons have <g transform="translate(x,y)"> wrappers that misalign artwork.
Solution: Remove wrappers and adjust all path coordinates to center artwork in square viewBoxes.
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class PathData:
    """Stores SVG path element data."""
    full_tag: str  # Complete <path .../>  or <path>...</path>
    d_attribute: str  # Just the path data from d="..."
    other_attributes: str  # fill, stroke, etc.


def extract_transform(svg_content: str) -> Optional[Tuple[float, float]]:
    """Extract translate(x,y) values from <g transform> tag."""
    match = re.search(r'<g\s+transform=["\']translate\(([^,]+),([^)]+)\)["\']>', svg_content)
    if match:
        return (float(match.group(1)), float(match.group(2)))
    return None


def extract_viewbox(svg_content: str) -> Optional[Tuple[float, float, float, float]]:
    """Extract viewBox="x y width height"."""
    match = re.search(r'viewBox=["\']([^"\']+)["\']', svg_content)
    if not match:
        return None

    parts = match.group(1).split()
    if len(parts) != 4:
        return None

    return tuple(float(p) for p in parts)


def extract_paths(svg_content: str) -> List[PathData]:
    """Extract all <path> elements with their attributes."""
    paths = []

    # Match both self-closing and paired tags
    pattern = r'<path\s+([^>]+?)(?:/>|>)'

    for match in re.finditer(pattern, svg_content):
        full_tag = match.group(0)
        attributes = match.group(1)

        # Extract d attribute
        d_match = re.search(r'd=["\']([^"\']+)["\']', attributes)
        if not d_match:
            continue

        d_data = d_match.group(1)

        # Extract other attributes (fill, stroke, etc.)
        other_attrs = re.sub(r'd=["\'][^"\']+["\']', '', attributes).strip()

        paths.append(PathData(full_tag=full_tag, d_attribute=d_data, other_attributes=other_attrs))

    return paths


def parse_path_coordinates(path_d: str) -> List[Tuple[float, float]]:
    """
    Extract all coordinate pairs from SVG path data.
    Handles M, L, C, Q, A, H, V commands (both absolute and relative).
    """
    coords = []

    # Remove path commands, keeping only numbers
    # Split on commands (letters) while keeping delimiters
    parts = re.split(r'([MLHVCSQTAZmlhvcsqtaz])', path_d)

    current_x, current_y = 0.0, 0.0
    last_command = None

    for i, part in enumerate(parts):
        if not part.strip():
            continue

        # If it's a command letter
        if part in 'MLHVCSQTAZmlhvcsqtaz':
            last_command = part
            continue

        # It's numeric data
        numbers = re.findall(r'-?\d+\.?\d*', part)
        if not numbers:
            continue

        # Process based on last command
        if last_command in ['M', 'L', 'T']:  # Absolute moveto/lineto
            for j in range(0, len(numbers) - 1, 2):
                x, y = float(numbers[j]), float(numbers[j+1])
                coords.append((x, y))
                current_x, current_y = x, y

        elif last_command in ['m', 'l', 't']:  # Relative moveto/lineto
            for j in range(0, len(numbers) - 1, 2):
                dx, dy = float(numbers[j]), float(numbers[j+1])
                current_x += dx
                current_y += dy
                coords.append((current_x, current_y))

        elif last_command == 'H':  # Absolute horizontal line
            for num in numbers:
                x = float(num)
                coords.append((x, current_y))
                current_x = x

        elif last_command == 'h':  # Relative horizontal line
            for num in numbers:
                current_x += float(num)
                coords.append((current_x, current_y))

        elif last_command == 'V':  # Absolute vertical line
            for num in numbers:
                y = float(num)
                coords.append((current_x, y))
                current_y = y

        elif last_command == 'v':  # Relative vertical line
            for num in numbers:
                current_y += float(num)
                coords.append((current_x, current_y))

        elif last_command in ['C', 'S', 'Q']:  # Absolute curves
            for j in range(0, len(numbers) - 1, 2):
                x, y = float(numbers[j]), float(numbers[j+1])
                coords.append((x, y))
                if j == len(numbers) - 2:  # Last pair is end point
                    current_x, current_y = x, y

        elif last_command in ['c', 's', 'q']:  # Relative curves
            for j in range(0, len(numbers) - 1, 2):
                dx, dy = float(numbers[j]), float(numbers[j+1])
                x = current_x + dx
                y = current_y + dy
                coords.append((x, y))
                if j == len(numbers) - 2:  # Last pair is end point
                    current_x, current_y = x, y

        elif last_command == 'A':  # Absolute arc
            # Arc: rx ry x-axis-rotation large-arc-flag sweep-flag x y
            for j in range(0, len(numbers), 7):
                if j + 6 < len(numbers):
                    x, y = float(numbers[j+5]), float(numbers[j+6])
                    coords.append((x, y))
                    current_x, current_y = x, y

        elif last_command == 'a':  # Relative arc
            for j in range(0, len(numbers), 7):
                if j + 6 < len(numbers):
                    dx, dy = float(numbers[j+5]), float(numbers[j+6])
                    current_x += dx
                    current_y += dy
                    coords.append((current_x, current_y))

    return coords


def calculate_bounds(paths: List[PathData]) -> Tuple[float, float, float, float]:
    """Calculate bounding box of all paths combined."""
    all_coords = []

    for path in paths:
        coords = parse_path_coordinates(path.d_attribute)
        all_coords.extend(coords)

    if not all_coords:
        return (0, 0, 0, 0)

    x_coords = [c[0] for c in all_coords]
    y_coords = [c[1] for c in all_coords]

    return (min(x_coords), min(y_coords), max(x_coords), max(y_coords))


def adjust_path_d(path_d: str, dx: float, dy: float) -> str:
    """
    Adjust all absolute coordinates in path data by (dx, dy).
    Only adjusts absolute coordinates (M, L, C, etc.), not relative (m, l, c).
    """
    result = []
    parts = re.split(r'([MLHVCSQTAZmlhvcsqtaz])', path_d)

    last_command = None

    for part in parts:
        if not part.strip():
            continue

        # If it's a command letter
        if part in 'MLHVCSQTAZmlhvcsqtaz':
            last_command = part
            result.append(part)
            continue

        # It's numeric data - adjust based on command type
        numbers = re.findall(r'-?\d+\.?\d*', part)
        if not numbers:
            result.append(part)
            continue

        # Adjust absolute coordinates only
        if last_command in ['M', 'L', 'C', 'S', 'Q', 'T']:
            # Adjust x,y pairs
            adjusted = []
            for i, num in enumerate(numbers):
                val = float(num)
                if i % 2 == 0:  # X coordinate
                    adjusted.append(f"{val + dx:.3f}")
                else:  # Y coordinate
                    adjusted.append(f"{val + dy:.3f}")
            result.append(' '.join(adjusted))

        elif last_command == 'H':
            # Horizontal line - adjust X only
            adjusted = [f"{float(num) + dx:.3f}" for num in numbers]
            result.append(' '.join(adjusted))

        elif last_command == 'V':
            # Vertical line - adjust Y only
            adjusted = [f"{float(num) + dy:.3f}" for num in numbers]
            result.append(' '.join(adjusted))

        elif last_command == 'A':
            # Arc: rx ry rotation large-arc sweep x y
            adjusted = []
            for i, num in enumerate(numbers):
                val = float(num)
                # Only adjust final x,y (indices 5,6 in each 7-number group)
                if i % 7 == 5:  # X coordinate
                    adjusted.append(f"{val + dx:.3f}")
                elif i % 7 == 6:  # Y coordinate
                    adjusted.append(f"{val + dy:.3f}")
                else:
                    adjusted.append(num)  # Keep others unchanged
            result.append(' '.join(adjusted))

        else:
            # Relative commands or Z - don't adjust
            result.append(part)

    return ''.join(result)


def fix_icon_svg(svg_content: str, icon_name: str) -> str:
    """
    Fix a single icon's SVG:
    1. Extract transform translate values
    2. Remove <g transform> wrapper
    3. Calculate artwork bounds
    4. Determine square viewBox size
    5. Adjust path coordinates to center artwork
    6. Return fixed SVG
    """
    # Check for transform
    transform = extract_transform(svg_content)
    if not transform:
        print(f"  {icon_name}: No transform found - already fixed or no issue")
        return svg_content

    tx, ty = transform
    print(f"  {icon_name}:")
    print(f"    Current transform: translate({tx:.2f}, {ty:.2f})")

    # Extract paths
    paths = extract_paths(svg_content)
    if not paths:
        print(f"    WARNING: No paths found")
        return svg_content

    # Calculate bounds (coordinates are already in transformed space)
    min_x, min_y, max_x, max_y = calculate_bounds(paths)
    artwork_w = max_x - min_x
    artwork_h = max_y - min_y

    print(f"    Artwork bounds: ({min_x:.1f}, {min_y:.1f}) to ({max_x:.1f}, {max_y:.1f})")
    print(f"    Artwork size: {artwork_w:.1f}×{artwork_h:.1f}")

    # Determine square size (maximize artwork)
    square_size = max(artwork_w, artwork_h)

    # Calculate centering offsets
    offset_x = (square_size - artwork_w) / 2
    offset_y = (square_size - artwork_h) / 2

    # Total adjustment = remove min offset + add centering
    adj_x = -min_x + offset_x
    adj_y = -min_y + offset_y

    print(f"    New viewBox: {square_size:.0f}×{square_size:.0f}")
    print(f"    Coordinate adjustment: ({adj_x:.2f}, {adj_y:.2f})")

    # Adjust all paths
    fixed_svg = svg_content
    for path in paths:
        new_d = adjust_path_d(path.d_attribute, adj_x, adj_y)
        old_path = re.escape(path.full_tag)
        new_path = f'<path {path.other_attributes} d="{new_d}"/>'
        fixed_svg = re.sub(old_path, new_path, fixed_svg, count=1)

    # Remove <g transform> wrapper
    fixed_svg = re.sub(r'<g\s+transform=["\']translate\([^)]+\)["\']>', '', fixed_svg)
    fixed_svg = re.sub(r'</g>\s*</svg>', '</svg>', fixed_svg)

    # Update viewBox
    fixed_svg = re.sub(
        r'viewBox=["\'][^"\']+["\']',
        f'viewBox="0 0 {square_size:.0f} {square_size:.0f}"',
        fixed_svg
    )

    return fixed_svg


def fix_all_icons():
    """Fix all icons in svg_icons_radar.py."""
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
    fixed_count = 0

    for match in icon_pattern.finditer(content):
        full_func = match.group(1)
        func_name = match.group(2)
        svg_content = match.group(3)

        # Skip line icon
        if 'line' in func_name.lower():
            print(f"SKIPPING {func_name} (intentionally non-square)")
            continue

        # Fix the SVG
        fixed_svg = fix_icon_svg(svg_content, func_name)

        if fixed_svg != svg_content:
            # Replace in content
            new_func = full_func.replace(svg_content, fixed_svg)
            new_content = new_content.replace(full_func, new_func)
            fixed_count += 1

    # Write back
    icon_file.write_text(new_content)

    print(f"\n✓ Fixed {fixed_count} icons")
    print(f"✓ Updated file: {icon_file}")
    return True


if __name__ == "__main__":
    print("=" * 80)
    print("SVG ICON COORDINATE FIX")
    print("=" * 80)
    print()

    success = fix_all_icons()
    sys.exit(0 if success else 1)
