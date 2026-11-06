"""Lightweight combat VFX: particles, slashes, screen shake."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

import pygame

from game import settings as S


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def lerp_color(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    t = max(0.0, min(1.0, t))
    return (int(lerp(a[0], b[0], t)), int(lerp(a[1], b[1], t)), int(lerp(a[2], b[2], t)))


def ease_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) ** 3


def ease_in_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    max_life: float
    size: float
    color: tuple[int, int, int]
    gravity: float = 420.0

    def update(self, dt: float) -> None:
        self.life -= dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += self.gravity * dt

    def draw(self, surf: pygame.Surface) -> None:
        if self.life <= 0:
            return
        a = max(0.0, self.life / self.max_life)
        col = tuple(int(c * a + S.BG[i] * (1 - a)) for i, c in enumerate(self.color))
        r = max(1, int(self.size * (0.4 + 0.6 * a)))
        pygame.draw.circle(surf, col, (int(self.x), int(self.y)), r)


@dataclass
class Ring:
    x: float
    y: float
    life: float
    max_life: float
    color: tuple[int, int, int]
    radius: float = 10.0
    grow: float = 180.0

    def update(self, dt: float) -> None:
        self.life -= dt
        self.radius += self.grow * dt

    def draw(self, surf: pygame.Surface) -> None:
        if self.life <= 0:
            return
        a = self.life / self.max_life
        col = tuple(int(c * a + S.BG[i] * (1 - a)) for i, c in enumerate(self.color))
        pygame.draw.circle(surf, col, (int(self.x), int(self.y)), int(self.radius), width=3)


@dataclass
class Slash:
    life: float
    max_life: float
    riposte: bool = False

    def update(self, dt: float) -> None:
        self.life -= dt

    def draw(self, surf: pygame.Surface, origin: tuple[float, float]) -> None:
        if self.life <= 0:
            return
        t = 1.0 - self.life / self.max_life
        start = 0.35
        end = -1.05
        ang = lerp(start, end, ease_out(t))
        length = 150 if self.riposte else 120
        color = S.GOLD if self.riposte else S.CYAN
        ox, oy = origin
        x2 = ox + math.cos(ang) * length
        y2 = oy + math.sin(ang) * length
        width = 8 if self.riposte else 5
        pygame.draw.line(surf, color, (ox, oy), (x2, y2), width)
        pygame.draw.circle(surf, color, (int(x2), int(y2)), 6)


@dataclass
class Floater:
    text: str
    y: float
    life: float
    max_life: float
    color: tuple[int, int, int]

    def update(self, dt: float) -> None:
        self.life -= dt
        self.y -= 42 * dt

    def draw(self, surf: pygame.Surface, font: pygame.font.Font) -> None:
        if self.life <= 0:
            return
        a = max(0.0, min(1.0, self.life / self.max_life))
        col = tuple(int(c * a + S.BG[i] * (1 - a)) for i, c in enumerate(self.color))
        img = font.render(self.text, True, col)
        rect = img.get_rect(center=(S.WIDTH // 2, int(self.y)))
        surf.blit(img, rect)


@dataclass
class FX:
    particles: list[Particle] = field(default_factory=list)
    rings: list[Ring] = field(default_factory=list)
    slashes: list[Slash] = field(default_factory=list)
    floaters: list[Floater] = field(default_factory=list)
    shake: float = 0.0
    flash: float = 0.0
    flash_color: tuple[int, int, int] = S.WHITE
    player_slash_t: float = 0.0
    player_hurt_t: float = 0.0
    player_parry_t: float = 0.0
    enemy_hurt_t: float = 0.0
    time: float = 0.0
    hp_enemy: float = 1.0
    hp_player: float = 1.0

    def burst(self, x: float, y: float, color: tuple[int, int, int], n: int = 14, speed: float = 220) -> None:
        for _ in range(n):
            ang = random.uniform(0, math.tau)
            spd = random.uniform(speed * 0.35, speed)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(ang) * spd,
                    vy=math.sin(ang) * spd - 40,
                    life=random.uniform(0.25, 0.55),
                    max_life=0.55,
                    size=random.uniform(3, 7),
                    color=color,
                )
            )

    def trigger(self, name: str) -> None:
        px, py = 110.0, 560.0
        ex, ey = 370.0, 290.0
        mx, my = 240.0, 420.0
        if name == "PARRY":
            self.player_parry_t = 0.35
            self.shake = max(self.shake, 6)
            self.flash = 0.18
            self.flash_color = S.CYAN
            self.rings.append(Ring(mx, my, 0.35, 0.35, S.CYAN, 20, 220))
            self.burst(px, py - 40, S.CYAN, 18, 280)
            self.floaters.append(Floater("PARRY", 360, 0.7, 0.7, S.CYAN))
        elif name == "RIPOSTE":
            self.player_slash_t = 0.32
            self.enemy_hurt_t = 0.28
            self.shake = max(self.shake, 10)
            self.flash = 0.16
            self.flash_color = S.GOLD
            self.slashes.append(Slash(0.28, 0.28, True))
            self.burst(ex, ey, S.GOLD, 22, 320)
            self.floaters.append(Floater("RIPOSTE", 340, 0.7, 0.7, S.GOLD))
        elif name == "HIT":
            self.player_slash_t = 0.28
            self.enemy_hurt_t = 0.22
            self.slashes.append(Slash(0.24, 0.24, False))
            self.burst(ex, ey, S.WHITE, 10, 200)
            self.floaters.append(Floater("HIT", 340, 0.55, 0.55, S.WHITE))
        elif name == "STRUCK":
            self.player_hurt_t = 0.4
            self.shake = max(self.shake, 14)
            self.flash = 0.22
            self.flash_color = S.RED
            self.burst(px, py, S.RED, 16, 240)
            self.floaters.append(Floater("STRUCK", 360, 0.7, 0.7, S.RED))
        elif name == "MISS":
            self.floaters.append(Floater("MISS", 360, 0.45, 0.45, S.MUTED))
        elif name == "DOWN":
            self.shake = max(self.shake, 12)
            self.burst(ex, ey, S.GOLD, 28, 260)
            self.floaters.append(Floater("DOWN", 330, 0.8, 0.8, S.GOLD))
        elif name == "+1 HP":
            self.floaters.append(Floater("+1 HP", 380, 0.8, 0.8, S.GREEN))
            self.rings.append(Ring(px, py, 0.4, 0.4, S.GREEN, 16, 140))
        elif name == "WINDOW":
            self.rings.append(Ring(mx, my, 0.22, 0.22, S.PARRY_FLASH, 40, 200))
            self.burst(ex, ey + 20, S.PARRY_FLASH, 8, 140)
        elif name == "SPAWN":
            self.burst(ex, ey, S.MUTED, 8, 120)

    def update(self, dt: float, enemy_frac: float, player_frac: float) -> None:
        self.time += dt
        self.shake = max(0.0, self.shake - dt * 38)
        self.flash = max(0.0, self.flash - dt)
        self.player_slash_t = max(0.0, self.player_slash_t - dt)
        self.player_hurt_t = max(0.0, self.player_hurt_t - dt)
        self.player_parry_t = max(0.0, self.player_parry_t - dt)
        self.enemy_hurt_t = max(0.0, self.enemy_hurt_t - dt)
        self.hp_enemy = lerp(self.hp_enemy, enemy_frac, min(1.0, dt * 8))
        self.hp_player = lerp(self.hp_player, player_frac, min(1.0, dt * 8))
        for p in self.particles:
            p.update(dt)
        for r in self.rings:
            r.update(dt)
        for s in self.slashes:
            s.update(dt)
        for f in self.floaters:
            f.update(dt)
        self.particles = [p for p in self.particles if p.life > 0]
        self.rings = [r for r in self.rings if r.life > 0]
        self.slashes = [s for s in self.slashes if s.life > 0]
        self.floaters = [f for f in self.floaters if f.life > 0]

    def offset(self) -> tuple[int, int]:
        if self.shake <= 0.4:
            return 0, 0
        mag = self.shake
        return int(random.uniform(-mag, mag)), int(random.uniform(-mag, mag))

    def draw_under(self, surf: pygame.Surface) -> None:
        for r in self.rings:
            r.draw(surf)

    def draw_over(self, surf: pygame.Surface, font: pygame.font.Font, slash_origin: tuple[float, float]) -> None:
        for p in self.particles:
            p.draw(surf)
        for s in self.slashes:
            s.draw(surf, slash_origin)
        for f in self.floaters:
            f.draw(surf, font)
        if self.flash > 0:
            overlay = pygame.Surface((S.WIDTH, S.HEIGHT), pygame.SRCALPHA)
            a = int(70 * (self.flash / 0.22))
            overlay.fill((*self.flash_color, max(0, min(70, a))))
            surf.blit(overlay, (0, 0))
