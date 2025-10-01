#!/usr/bin/env python3
"""Audit and normalize SVG icons for consistent viewBox dimensions."""

import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ArtworkBounds:
    """Bounding box of SVG artwork."""
    min_x: float
    max_x: float
    min_y: float
    max_y: float

    @property
    def width(self) -> float:
        return self.max_x - self.min_x

    @property
    def height(self) -> float:
        return self.max_y - self.min_y


@dataclass
class ViewBoxInfo:
    """ViewBox parameters."""
    x: float
    y: float
    width: float
    height: float

    @property
    def is_square(self) -> bool:
        return abs(self.width - self.height) < 0.01


@dataclass
class IconAudit:
    """Audit results for a single icon."""
    name: str
    viewbox: ViewBoxInfo
    bounds: Optional[ArtworkBounds]
    is_square: bool
    is_centered: bool
    is_maximized: bool
    utilization: float
    problems: List[str]


def extract_viewbox(svg_content: str) -> Optional[ViewBoxInfo]:
    """Extract viewBox from SVG content."""
    match = re.search(r'viewBox=["\']([^"\']+)["\']', svg_content)
    if not match:
        return None

    parts = match.group(1).split()
    if len(parts) != 4:
        return None

    try:
        return ViewBoxInfo(
            x=float(parts[0]),
            y=float(parts[1]),
            width=float(parts[2]),
            height=float(parts[3])
        )
    except ValueError:
        return None


def extract_path_bounds(svg_content: str) -> Optional[ArtworkBounds]:
    """
    Extract approximate bounding box from path data.
    This is a simplified approach - extracts M/L/C coordinates.
    """
    # Find all path elements
    paths = re.findall(r'd=["\']([^"\']+)["\']', svg_content)
    if not paths:
        return None

    all_coords = []

    for path in paths:
        # Extract numeric coordinates from path data
        # Look for numbers (including decimals and negatives)
        coords = re.findall(r'-?\d+\.?\d*', path)
        all_coords.extend([float(c) for c in coords])

    if len(all_coords) < 2:
        return None

    # Separate x and y coordinates (every other number)
    x_coords = all_coords[0::2]
    y_coords = all_coords[1::2]

    return ArtworkBounds(
        min_x=min(x_coords),
        max_x=max(x_coords),
        min_y=min(y_coords),
        max_y=max(y_coords)
    )


def audit_icon(name: str, svg_content: str, exclude_from_check: bool = False) -> IconAudit:
    """Audit a single SVG icon."""
    viewbox = extract_viewbox(svg_content)
    bounds = extract_path_bounds(svg_content)

    problems = []
    is_square = False
    is_centered = False
    is_maximized = False
    utilization = 0.0

    if viewbox is None:
        problems.append("No viewBox found")
        return IconAudit(name, viewbox, bounds, False, False, False, 0.0, problems)

    if bounds is None:
        problems.append("Could not extract path bounds")
        return IconAudit(name, viewbox, bounds, False, False, False, 0.0, problems)

    # Skip checks for excluded icons (radar graphs, line icons)
    if exclude_from_check:
        return IconAudit(name, viewbox, bounds, True, True, True, 100.0,
                        ["EXCLUDED: Radar/line icon - intentionally non-square"])

    # Check if viewBox is square
    is_square = viewbox.is_square
    if not is_square:
        problems.append(f"Non-square viewBox: {viewbox.width}×{viewbox.height}")

    # Calculate utilization (how much of viewBox is filled by artwork)
    artwork_area = bounds.width * bounds.height
    viewbox_area = viewbox.width * viewbox.height
    utilization = (artwork_area / viewbox_area * 100) if viewbox_area > 0 else 0

    # Check if artwork is maximally sized
    # Artwork should fill at least 90% of the available square
    target_size = max(viewbox.width, viewbox.height)
    max_artwork_dimension = max(bounds.width, bounds.height)

    # If the artwork could be scaled up significantly, it's not maximized
    scale_factor = target_size / max_artwork_dimension if max_artwork_dimension > 0 else 0
    is_maximized = scale_factor < 1.1  # Within 10% tolerance

    if not is_maximized:
        problems.append(f"Artwork not maximally sized: {bounds.width:.0f}×{bounds.height:.0f} "
                       f"in {viewbox.width:.0f}×{viewbox.height:.0f} viewBox "
                       f"(could scale up {scale_factor:.1f}x)")

    # Check if artwork is centered
    # Calculate expected centering
    expected_x = viewbox.x
    expected_y = viewbox.y
    actual_x = bounds.min_x
    actual_y = bounds.min_y

    # For non-square artwork in square viewBox, check centering
    if is_square:
        if bounds.width < bounds.height:  # Taller than wide
            expected_x = viewbox.x + (viewbox.width - bounds.width) / 2
        elif bounds.height < bounds.width:  # Wider than tall
            expected_y = viewbox.y + (viewbox.height - bounds.height) / 2

        x_offset = abs(actual_x - expected_x)
        y_offset = abs(actual_y - expected_y)

        # Allow 5% tolerance
        tolerance = max(viewbox.width, viewbox.height) * 0.05
        is_centered = x_offset < tolerance and y_offset < tolerance

        if not is_centered:
            problems.append(f"Artwork not centered: offset ({x_offset:.1f}, {y_offset:.1f})")

    return IconAudit(name, viewbox, bounds, is_square, is_centered, is_maximized,
                    utilization, problems)


def audit_all_icons():
    """Audit all icons in svg_icons_radar.py."""
    # Read the icon file
    icon_file = Path(__file__).parent / "ccip" / "svg_icons_radar.py"

    if not icon_file.exists():
        print(f"ERROR: Icon file not found: {icon_file}")
        sys.exit(1)

    content = icon_file.read_text()

    # Extract all icon functions
    icon_pattern = re.compile(r'def (svg_\w+)\(\):\s+"""([^"]+)"""\s+return\s+\'\'\'([^\']+)\'\'\'',
                             re.MULTILINE | re.DOTALL)

    icons = {}
    for match in icon_pattern.finditer(content):
        func_name = match.group(1)
        description = match.group(2)
        svg_content = match.group(3)
        icons[func_name] = (description, svg_content)

    print(f"Found {len(icons)} icon functions\n")

    # Audit each icon
    audits = []
    for func_name, (description, svg_content) in icons.items():
        # Exclude radar and line icons
        exclude = "radar" in func_name.lower() or "line" in func_name.lower()
        audit = audit_icon(func_name, svg_content, exclude)
        audits.append(audit)

    # Generate report
    print("=" * 80)
    print("SVG ICON AUDIT RESULTS")
    print("=" * 80)
    print()

    passing = [a for a in audits if not a.problems or
              any("EXCLUDED" in p for p in a.problems)]
    failing = [a for a in audits if a.problems and
              not any("EXCLUDED" in p for p in a.problems)]

    print(f"Total icons checked: {len(audits)}")
    print(f"Passing: {len(passing)}")
    print(f"Failing: {len(failing)}")
    print()

    if failing:
        print("FAILING ICONS:")
        print("-" * 80)
        for audit in failing:
            print(f"\n{audit.name}")
            if audit.viewbox:
                print(f"  Current viewBox: {audit.viewbox.width}×{audit.viewbox.height}")
            if audit.bounds:
                print(f"  Artwork bounds: ({audit.bounds.min_x:.1f}, {audit.bounds.min_y:.1f}) "
                      f"to ({audit.bounds.max_x:.1f}, {audit.bounds.max_y:.1f})")
                print(f"  Artwork size: {audit.bounds.width:.1f}×{audit.bounds.height:.1f}")
            print(f"  Utilization: {audit.utilization:.1f}%")
            print(f"  Problems:")
            for problem in audit.problems:
                print(f"    - {problem}")

            # Suggest fix
            if audit.viewbox and audit.bounds:
                target_size = max(audit.bounds.width, audit.bounds.height)
                padding_x = (target_size - audit.bounds.width) / 2 if audit.bounds.width < target_size else 0
                padding_y = (target_size - audit.bounds.height) / 2 if audit.bounds.height < target_size else 0

                print(f"  Suggested fix:")
                print(f"    - Target square: {target_size:.0f}×{target_size:.0f}")
                if padding_x > 0:
                    print(f"    - Add {padding_x:.1f}px padding left/right to center")
                if padding_y > 0:
                    print(f"    - Add {padding_y:.1f}px padding top/bottom to center")
                print(f"    - New viewBox: \"0 0 {target_size:.0f} {target_size:.0f}\"")

    print("\n" + "=" * 80)
    print("EXCLUDED ICONS (radar graphs & line icons):")
    print("-" * 80)
    for audit in passing:
        if any("EXCLUDED" in p for p in audit.problems):
            print(f"{audit.name}: {audit.problems[0]}")

    return audits, passing, failing


if __name__ == "__main__":
    audits, passing, failing = audit_all_icons()
    sys.exit(0 if not failing else 1)
