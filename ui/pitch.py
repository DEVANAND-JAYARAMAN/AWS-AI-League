"""
Football pitch visualization (Step 47).

Pure-Python SVG rendering - no plotting library, no frontend framework.
It consumes the *serialized* GameState snapshots that the analytics event
logger already produces (``event.state_before`` / ``event.state_after``)
and draws a static, tick-by-tick picture of the match.

    {
        "ball_position": {"x": .., "y": ..},
        "possession": "OUR_TEAM",
        "our_team":      {pid: {"player_id", "role", "position": {"x","y"}}},
        "opponent_team": {pid: {...}},
    }

Nothing here runs a simulation, mutates state, or calls AWS.
"""

from __future__ import annotations

from typing import Optional

# Model coordinate system used throughout the backend.
PITCH_X = 100.0
PITCH_Y = 100.0

ROLE_ABBR = {
    "GOALKEEPER": "GK",
    "DEFENDER": "DF",
    "MIDFIELDER": "MF",
    "STRIKER": "ST",
}

_OUR_FILL = "#2563eb"
_OPP_FILL = "#6b7280"
_GRASS = "#1f7a3d"
_GRASS_ALT = "#22823f"
_LINE = "#eef6ef"


def _xy(pos):
    """Accept a ``{"x":..,"y":..}`` dict or an ``(x, y)`` sequence."""
    if not pos:
        return None
    if isinstance(pos, dict):
        x, y = pos.get("x"), pos.get("y")
    else:
        x, y = pos[0], pos[1]
    if x is None or y is None:
        return None
    return float(x), float(y)


def _map(x: float, y: float, m: float, w: float, h: float):
    """Model coords -> SVG pixel coords (with a margin ``m``)."""
    px = m + (x / PITCH_X) * (w - 2 * m)
    py = m + (y / PITCH_Y) * (h - 2 * m)
    return px, py


def _player_marker(px: float, py: float, label: str, fill: str) -> str:
    return (
        f'<circle cx="{px:.1f}" cy="{py:.1f}" r="12" fill="{fill}" '
        f'stroke="#ffffff" stroke-width="1.5"/>'
        f'<text x="{px:.1f}" y="{py + 3.5:.1f}" text-anchor="middle" '
        f'font-size="10" font-family="sans-serif" fill="#ffffff" '
        f'font-weight="700">{label}</text>'
    )


def build_pitch_svg(
    state: dict,
    ball_movement: Optional[dict] = None,
    *,
    width: int = 820,
    height: int = 520,
) -> str:
    """Return a complete, self-contained ``<svg>`` string for one snapshot."""

    m = 26.0
    w, h = float(width), float(height)
    inner_l, inner_t = _map(0, 0, m, w, h)
    inner_r, inner_b = _map(PITCH_X, PITCH_Y, m, w, h)
    inner_w = inner_r - inner_l
    inner_h = inner_b - inner_t
    mid_x, _ = _map(50, 50, m, w, h)
    cx, cy = _map(50, 50, m, w, h)
    circle_r = (18 / PITCH_X) * inner_w

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="100%" style="max-width:{width}px;height:auto;'
        f'display:block;margin:0 auto;border-radius:8px">',
        '<defs><marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" '
        'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
        '<path d="M0,0 L10,5 L0,10 z" fill="#f5c518"/></marker></defs>',
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="{_GRASS}"/>',
    ]

    # Mowing stripes.
    stripes = 6
    for i in range(stripes):
        if i % 2:
            continue
        sx = inner_l + i * (inner_w / stripes)
        parts.append(
            f'<rect x="{sx:.1f}" y="{inner_t:.1f}" '
            f'width="{inner_w / stripes:.1f}" height="{inner_h:.1f}" fill="{_GRASS_ALT}"/>'
        )

    lw = 'stroke="%s" stroke-width="2" fill="none"' % _LINE

    # Boundary, halfway line, centre circle + spot.
    parts.append(
        f'<rect x="{inner_l:.1f}" y="{inner_t:.1f}" width="{inner_w:.1f}" '
        f'height="{inner_h:.1f}" {lw}/>'
    )
    parts.append(
        f'<line x1="{mid_x:.1f}" y1="{inner_t:.1f}" x2="{mid_x:.1f}" '
        f'y2="{inner_b:.1f}" {lw}/>'
    )
    parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{circle_r:.1f}" {lw}/>')
    parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="2.5" fill="{_LINE}"/>')

    # Penalty boxes + goals at x=0 (our goal) and x=100 (opponent goal).
    box_w = (16 / PITCH_X) * inner_w
    box_h = (58 / PITCH_Y) * inner_h
    box_y = inner_t + (inner_h - box_h) / 2
    goal_h = (18 / PITCH_Y) * inner_h
    goal_y = inner_t + (inner_h - goal_h) / 2
    goal_d = 7.0

    parts.append(
        f'<rect x="{inner_l:.1f}" y="{box_y:.1f}" width="{box_w:.1f}" '
        f'height="{box_h:.1f}" {lw}/>'
    )
    parts.append(
        f'<rect x="{inner_r - box_w:.1f}" y="{box_y:.1f}" width="{box_w:.1f}" '
        f'height="{box_h:.1f}" {lw}/>'
    )
    parts.append(
        f'<rect x="{inner_l - goal_d:.1f}" y="{goal_y:.1f}" width="{goal_d:.1f}" '
        f'height="{goal_h:.1f}" fill="{_LINE}" opacity="0.85"/>'
    )
    parts.append(
        f'<rect x="{inner_r:.1f}" y="{goal_y:.1f}" width="{goal_d:.1f}" '
        f'height="{goal_h:.1f}" fill="{_LINE}" opacity="0.85"/>'
    )

    # Opponents first (drawn under our team).
    for pid, player in (state.get("opponent_team") or {}).items():
        pos = _xy(player.get("position"))
        if pos is None:
            continue
        px, py = _map(pos[0], pos[1], m, w, h)
        parts.append(_player_marker(px, py, "OPP", _OPP_FILL))

    for pid, player in (state.get("our_team") or {}).items():
        pos = _xy(player.get("position"))
        if pos is None:
            continue
        px, py = _map(pos[0], pos[1], m, w, h)
        label = ROLE_ABBR.get(str(player.get("role", "")).upper(), pid[:2].upper())
        parts.append(_player_marker(px, py, label, _OUR_FILL))

    # Ball movement arrow (before -> after) then the ball itself.
    before = _xy(ball_movement.get("before")) if ball_movement else None
    after = _xy(ball_movement.get("after")) if ball_movement else None
    if (
        before
        and after
        and None not in before
        and None not in after
        and (abs(before[0] - after[0]) + abs(before[1] - after[1])) > 0.5
    ):
        bx1, by1 = _map(before[0], before[1], m, w, h)
        bx2, by2 = _map(after[0], after[1], m, w, h)
        parts.append(
            f'<line x1="{bx1:.1f}" y1="{by1:.1f}" x2="{bx2:.1f}" y2="{by2:.1f}" '
            f'stroke="#f5c518" stroke-width="3" stroke-dasharray="6 4" '
            f'marker-end="url(#arrow)"/>'
        )

    ball = _xy(state.get("ball_position"))
    if ball is not None:
        bx, by = _map(ball[0], ball[1], m, w, h)
        parts.append(
            f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="6" fill="#ffffff" '
            f'stroke="#111111" stroke-width="1.5"/>'
        )

    parts.append("</svg>")
    return "".join(parts)
