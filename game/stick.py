"""Stick-figure drawing for a third-person diagonal fight view."""

from __future__ import annotations

import math

import pygame

from game import settings as S
from game.fx import lerp, lerp_color


HORIZON_Y = 220
NEAR_X, NEAR_Y = 92.0, 655.0
FAR_X, FAR_Y = 392.0, 268.0


def fighter_screen(depth: float) -> tuple[float, float, float]:
    """depth 0 = far (top-right), 1 = near (bottom-left). Returns x, feet_y, scale."""
    d = max(0.0, min(1.2, depth))
    x = lerp(FAR_X, NEAR_X, d)
    y = lerp(FAR_Y, NEAR_Y, d)
    scale = lerp(0.40, 1.18, d)
    return x, y, scale


def draw_arena(surf: pygame.Surface, t: float) -> None:
    sky_top = (18, 22, 34)
    sky_bot = (28, 24, 36)
    for i in range(HORIZON_Y):
        col = lerp_color(sky_top, sky_bot, i / max(1, HORIZON_Y))
        pygame.draw.line(surf, col, (0, i), (S.WIDTH, i))
    ground = (20, 22, 30)
    pygame.draw.rect(surf, ground, (0, HORIZON_Y, S.WIDTH, S.HEIGHT - HORIZON_Y))
    pygame.draw.line(surf, (70, 76, 92), (0, HORIZON_Y), (S.WIDTH, HORIZON_Y), 2)

    vp = (S.WIDTH * 0.88, HORIZON_Y - 8)
    pulse = 0.35 + 0.15 * math.sin(t * 1.4)
    line_c = lerp_color((36, 40, 54), (58, 64, 82), pulse)
    pygame.draw.line(surf, line_c, (8, S.HEIGHT - 8), vp, 2)
    pygame.draw.line(surf, line_c, (S.WIDTH * 0.42, S.HEIGHT), vp, 2)
    pygame.draw.line(surf, line_c, (0, S.HEIGHT * 0.62), vp, 1)
    pygame.draw.line(surf, line_c, (S.WIDTH * 0.22, S.HEIGHT), vp, 1)

    for k in range(1, 9):
        u = (k / 9) ** 1.35
        y = lerp(HORIZON_Y + 12, S.HEIGHT - 30, u)
        left = lerp(vp[0] - 30, 8, u)
        right = lerp(vp[0] + 20, S.WIDTH * 0.62, u)
        pygame.draw.line(surf, line_c, (left, y), (right, y + 18), 1)

    pygame.draw.ellipse(surf, (48, 52, 68), (S.WIDTH * 0.42, 300, 160, 36), width=2)


def _pt(origin: tuple[float, float], ang: float, length: float) -> tuple[float, float]:
    return origin[0] + math.cos(ang) * length, origin[1] + math.sin(ang) * length


def draw_stick(
    surf: pygame.Surface,
    cx: float,
    feet_y: float,
    scale: float,
    color: tuple[int, int, int],
    *,
    view: str,
    sword_ang: float,
    walk: float = 0.0,
    lean: float = 0.0,
    fallen: float = 0.0,
    thickness: float = 3.0,
    alpha: float = 1.0,
    idle_t: float = 0.0,
    crouch: float = 0.0,
) -> tuple[float, float]:
    """Draw an articulated stick fighter along the lower-left / upper-right lane.

    view 'back' = player (facing top-right). view 'front' = enemy (facing bottom-left).
    Returns sword-hand position for VFX.
    """
    col = lerp_color(S.BG, color, alpha)
    s = max(0.15, scale)
    thick = max(2, int(thickness * s))
    head_r = max(4, int(11 * s))
    toward = 1.0 if view == "back" else -1.0

    breathe = math.sin(idle_t * 3.2) * 2.2 * s
    hip_drop = 8 * s * crouch
    bob = math.sin(walk) * 2.0 * s * (0.35 if abs(math.sin(walk)) < 0.2 else 1.0)

    hip = (cx + toward * lean * 12 * s, feet_y - (38 - hip_drop) * s + breathe * 0.25 + bob)
    shoulder = (
        hip[0] + toward * (6 + lean * 10) * s,
        hip[1] - (34 - crouch * 4) * s - breathe,
    )
    head = (
        shoulder[0] + toward * 3 * s,
        shoulder[1] - 16 * s - head_r * 0.2 - breathe * 0.4,
    )

    if fallen > 0:
        hip = (lerp(hip[0], cx + toward * 36 * s, fallen), lerp(hip[1], feet_y - 6, fallen))
        shoulder = (lerp(shoulder[0], hip[0] + toward * 30 * s, fallen), lerp(shoulder[1], feet_y - 8, fallen))
        head = (lerp(head[0], hip[0] + toward * 52 * s, fallen), lerp(head[1], feet_y - 10, fallen))

    stride = math.sin(walk)
    # Knees so a run/charge reads instead of sliding
    thigh = 22 * s
    shin = 20 * s
    l_hip_ang = 1.15 + toward * 0.08 - stride * 0.55 - crouch * 0.25
    r_hip_ang = 1.15 - toward * 0.08 + stride * 0.55 - crouch * 0.25
    l_knee_bend = 0.55 + max(0.0, -stride) * 0.7 + crouch * 0.4
    r_knee_bend = 0.55 + max(0.0, stride) * 0.7 + crouch * 0.4
    l_knee = _pt(hip, l_hip_ang, thigh)
    r_knee = _pt(hip, r_hip_ang, thigh)
    l_foot = _pt(l_knee, l_hip_ang + l_knee_bend, shin)
    r_foot = _pt(r_knee, r_hip_ang + r_knee_bend, shin)
    # Plant near the ground line
    l_foot = (l_foot[0], lerp(l_foot[1], feet_y, 0.55))
    r_foot = (r_foot[0], lerp(r_foot[1], feet_y, 0.55))

    pygame.draw.line(surf, col, hip, l_knee, thick)
    pygame.draw.line(surf, col, l_knee, l_foot, thick)
    pygame.draw.line(surf, col, hip, r_knee, thick)
    pygame.draw.line(surf, col, r_knee, r_foot, thick)
    pygame.draw.circle(surf, col, (int(l_foot[0]), int(l_foot[1])), max(2, int(2.5 * s)))
    pygame.draw.circle(surf, col, (int(r_foot[0]), int(r_foot[1])), max(2, int(2.5 * s)))

    pygame.draw.line(surf, col, hip, shoulder, thick)
    pygame.draw.circle(surf, col, (int(head[0]), int(head[1])), head_r, width=max(2, thick - 1))
    pygame.draw.circle(surf, col, (int(head[0]), int(head[1])), max(2, int(head_r * 0.22)))

    off_ang = 0.85 + toward * 0.35
    l_hand = _pt(shoulder, off_ang + math.sin(walk) * 0.25 + math.sin(idle_t * 2.4) * 0.08, 24 * s)
    r_hand = _pt(shoulder, sword_ang, 26 * s)
    pygame.draw.line(surf, col, shoulder, l_hand, thick)
    pygame.draw.line(surf, col, shoulder, r_hand, thick)

    sword_len = 44 * s
    tip = _pt(r_hand, sword_ang, sword_len)
    blade = lerp_color(S.BG, S.WHITE, 0.4 + 0.6 * alpha)
    pygame.draw.line(surf, blade, r_hand, tip, max(2, thick - 1))
    guard = _pt(r_hand, sword_ang, 8 * s)
    px, py = -math.sin(sword_ang) * 7 * s, math.cos(sword_ang) * 7 * s
    pygame.draw.line(surf, blade, (guard[0] - px, guard[1] - py), (guard[0] + px, guard[1] + py), 2)
    pygame.draw.circle(surf, blade, (int(tip[0]), int(tip[1])), max(2, int(2.4 * s)))
    return r_hand
