"""Title, battle, and game-over scenes."""

from __future__ import annotations

import math

import pygame

from game import settings as S
from game.combat import Combat, Phase
from game.fx import FX, ease_in_out, lerp, lerp_color
from game.input import Gesture, PointerInput
from game.stick import draw_arena, draw_stick, fighter_screen


def _font(size: int) -> pygame.font.Font:
    # Default bitmap font. System fonts are not available in the WebAssembly build.
    return pygame.font.Font(None, size)


def _center_text(surf: pygame.Surface, text: str, y: int, size: int, color: tuple[int, int, int]) -> None:
    img = _font(size).render(text, True, color)
    rect = img.get_rect(center=(S.WIDTH // 2, y))
    surf.blit(img, rect)


def _hp_bar(
    surf: pygame.Surface,
    x: int,
    y: int,
    w: int,
    h: int,
    frac: float,
    fill: tuple[int, int, int],
) -> None:
    pygame.draw.rect(surf, (40, 44, 56), (x, y, w, h), border_radius=6)
    frac = max(0.0, min(1.0, frac))
    if frac > 0:
        pygame.draw.rect(surf, fill, (x, y, int(w * frac), h), border_radius=6)
    pygame.draw.rect(surf, S.WHITE, (x, y, w, h), width=2, border_radius=6)


class MenuScene:
    def __init__(self) -> None:
        self.t = 0.0

    def handle(self, event: pygame.event.Event) -> str | None:
        if event.type in (pygame.MOUSEBUTTONUP, pygame.FINGERUP, pygame.KEYDOWN):
            if event.type == pygame.MOUSEBUTTONUP and getattr(event, "button", 1) != 1:
                return None
            return "battle"
        return None

    def update(self, dt: float) -> str | None:
        self.t += dt
        return None

    def draw(self, surf: pygame.Surface) -> None:
        draw_arena(surf, self.t)
        pulse = 0.5 + 0.5 * math.sin(self.t * 2.2)
        ex, ey, es = fighter_screen(0.22)
        px, py, ps = fighter_screen(0.92)
        draw_stick(
            surf, ex, ey, es, S.ENEMY,
            view="front",
            sword_ang=2.35 + math.sin(self.t * 1.3) * 0.18,
            walk=self.t * 2.1, lean=0.05, idle_t=self.t,
        )
        draw_stick(
            surf, px, py, ps, S.PLAYER,
            view="back",
            sword_ang=-0.55 + math.sin(self.t * 1.6) * 0.16,
            walk=self.t * 2.1, lean=0.08, idle_t=self.t, thickness=3.4,
        )
        title = _font(int(56 + 3 * math.sin(self.t * 2))).render(
            "PARRY", True, lerp_color(S.GOLD, S.WHITE, pulse * 0.25)
        )
        surf.blit(title, title.get_rect(center=(S.WIDTH // 2, 56)))
        _center_text(surf, "Tap to parry  ·  Swipe to attack", 92, 18, S.MUTED)
        _center_text(surf, "Every 5th fight is a boss", 118, 16, S.MUTED)
        _center_text(surf, "Tap to start", 760, 24, lerp_color(S.MUTED, S.WHITE, 0.45 + 0.55 * pulse))


class GameOverScene:
    def __init__(self, wave: int) -> None:
        self.wave = wave
        self.t = 0.0

    def handle(self, event: pygame.event.Event) -> str | None:
        if event.type in (pygame.MOUSEBUTTONUP, pygame.FINGERUP, pygame.KEYDOWN):
            if event.type == pygame.MOUSEBUTTONUP and getattr(event, "button", 1) != 1:
                return None
            return "battle"
        return None

    def update(self, dt: float) -> str | None:
        self.t += dt
        return None

    def draw(self, surf: pygame.Surface) -> None:
        draw_arena(surf, self.t)
        fall = min(1.0, self.t * 1.4)
        px, py, ps = fighter_screen(0.92)
        draw_stick(
            surf, px, py, ps, S.PLAYER,
            view="back", sword_ang=1.4, walk=0.0, lean=0.0,
            fallen=fall, thickness=3.4, idle_t=self.t,
        )
        _center_text(surf, "DEFEATED", 200, 48, S.RED)
        _center_text(surf, f"Reached wave {self.wave}", 250, 22, S.MUTED)
        pulse = 0.45 + 0.55 * (0.5 + 0.5 * math.sin(self.t * 2.4))
        _center_text(surf, "Tap to retry", 760, 24, lerp_color(S.MUTED, S.WHITE, pulse))


class BattleScene:
    def __init__(self) -> None:
        self.combat = Combat()
        self.pointer = PointerInput()
        self.fx = FX()
        self._death_t = 0.0
        self._spawn_t = 0.0
        self._disp_e = 0.22
        self._disp_p = 0.92
        self._ghosts: list[tuple[float, float, float, float, float, tuple[int, int, int]]] = []
        e = self.combat.enemy
        p = self.combat.player
        self.fx.hp_enemy = e.hp / e.max_hp
        self.fx.hp_player = p.hp / p.max_hp

    def handle(self, event: pygame.event.Event) -> str | None:
        gesture = self.pointer.handle(event)
        if gesture != Gesture.NONE:
            self.combat.apply_gesture(gesture)
        return None

    def update(self, dt: float) -> str | None:
        prev_phase = self.combat.phase
        self.combat.update(dt)
        if self.combat.phase == Phase.SPAWN and prev_phase != Phase.SPAWN:
            self._spawn_t = 0.0
        self._spawn_t += dt
        for name in self.combat.events:
            self.fx.trigger(name)
        self.combat.events.clear()
        e = self.combat.enemy
        p = self.combat.player
        self.fx.update(dt, e.hp / max(1, e.max_hp), p.hp / max(1, p.max_hp))

        ed, _, _, _, _, _ = self._enemy_depth_pose()
        pd, _, _, _, _, _ = self._player_depth_pose()
        follow = 10.0 if self.combat.phase in (Phase.WINDOW, Phase.HIT) else 7.0
        self._disp_e = lerp(self._disp_e, ed, min(1.0, dt * follow))
        self._disp_p = lerp(self._disp_p, pd, min(1.0, dt * 8.0))

        if self.combat.phase in (Phase.WINDOW, Phase.HIT) and self.combat.lunge > 0.35:
            ex, ey, es = fighter_screen(self._disp_e)
            color = S.ENEMY_BOSS if e.is_boss else S.ENEMY
            self._ghosts.append((ex, ey, es * (1.22 if e.is_boss else 1.0), 1.35, 0.18, color))
        self._ghosts = [(x, y, s, a, life - dt, c) for x, y, s, a, life, c in self._ghosts if life - dt > 0]

        if not p.alive:
            self._death_t += dt
            if self._death_t >= 0.85:
                return "gameover"
        return None

    def _enemy_depth_pose(self) -> tuple[float, float, float, float, float, float]:
        """depth, sword_ang, lean, fallen, walk, crouch."""
        c = self.combat
        t = self.fx.time
        walk = t * 2.6
        depth = 0.22
        ang = 2.35
        lean = 0.05
        fallen = 0.0
        crouch = 0.0
        if c.phase == Phase.SPAWN:
            k = ease_in_out(min(1.0, self._spawn_t / 0.55))
            depth = lerp(0.02, 0.22, k)
            walk = self._spawn_t * 14
            lean = 0.2
        elif c.phase == Phase.TELEGRAPH:
            wind = 1.0 - max(0.0, c.timer / max(0.001, c.enemy.telegraph))
            depth = lerp(0.22, 0.14, wind)
            lean = -0.65 * wind
            crouch = 0.85 * wind
            walk = t * 1.2
            ang = lerp(2.35, 3.6, ease_in_out(wind))
        elif c.phase == Phase.WINDOW:
            depth = 0.22 + c.lunge * 0.48
            lean = 0.95
            crouch = 0.15
            ang = 2.0
            walk = t * 18
        elif c.phase == Phase.HIT:
            depth = 0.72
            lean = 1.15
            ang = 1.85
            walk = t * 10
        elif c.phase == Phase.STUN:
            depth = 0.26
            lean = 0.1
            ang = 2.9 + math.sin(t * 18) * 0.25
            walk = math.sin(t * 16) * 0.8
        elif c.phase == Phase.DEAD:
            fall = 1.0 - max(0.0, min(1.0, c.timer / 0.55))
            depth = 0.30
            fallen = fall
            ang = 3.2
            walk = 0.0
        else:
            depth = 0.22 + c.lunge * 0.18
            walk = t * 2.4
        if self.fx.enemy_hurt_t > 0:
            depth -= 0.08 * (self.fx.enemy_hurt_t / 0.28)
            lean -= 0.4
        if c.enemy.is_boss:
            depth = min(1.05, depth + 0.03)
        return depth, ang, lean, fallen, walk, crouch

    def _player_depth_pose(self) -> tuple[float, float, float, float, float, float]:
        t = self.fx.time
        depth = 0.92
        ang = -0.55
        lean = 0.1
        fallen = 0.0
        walk = t * 2.2
        crouch = 0.05 + 0.04 * math.sin(t * 3.1)
        if self.fx.player_slash_t > 0:
            k = 1.0 - self.fx.player_slash_t / 0.32
            depth = lerp(0.92, 0.74, math.sin(k * math.pi))
            lean = 0.7
            crouch = 0.2
            ang = lerp(-0.2, -1.15, ease_in_out(min(1.0, k * 1.3)))
            walk = 8 + k * 10
        if self.fx.player_parry_t > 0:
            k = self.fx.player_parry_t / 0.35
            ang = -1.85
            lean = -0.15
            crouch = 0.45 * k
            depth = 0.90
            walk = 0.4
        if self.fx.player_hurt_t > 0:
            k = self.fx.player_hurt_t / 0.4
            depth = 0.97
            lean = -0.55
            fallen = 0.12 * k
            crouch = 0.3
        if not self.combat.player.alive:
            fallen = min(1.0, self._death_t * 1.8)
            depth = 0.94
            walk = 0.0
        return depth, ang, lean, fallen, walk, crouch

    def _draw_fighter_at(
        self,
        surf: pygame.Surface,
        depth: float,
        view: str,
        color: tuple[int, int, int],
        ang: float,
        lean: float,
        fallen: float,
        walk: float,
        crouch: float,
        thickness: float,
        alpha: float,
        scale_mul: float = 1.0,
    ) -> tuple[float, float]:
        x, y, sc = fighter_screen(depth)
        return draw_stick(
            surf, x, y, sc * scale_mul, color,
            view=view, sword_ang=ang, walk=walk, lean=lean, fallen=fallen,
            thickness=thickness, alpha=alpha, idle_t=self.fx.time, crouch=crouch,
        )

    def draw(self, surf: pygame.Surface) -> None:
        c = self.combat
        e = c.enemy
        ox, oy = self.fx.offset()
        layer = pygame.Surface((S.WIDTH, S.HEIGHT))
        draw_arena(layer, self.fx.time)

        label = "BOSS" if e.is_boss else "ENEMY"
        _center_text(layer, f"WAVE {c.wave}  ·  {label}", 28, 20, S.GOLD if e.is_boss else S.MUTED)
        fill = S.ENEMY_BOSS if e.is_boss else S.RED
        _hp_bar(layer, 40, 48, S.WIDTH - 80, 14, self.fx.hp_enemy, fill)

        self.fx.draw_under(layer)

        enemy_color = S.ENEMY_BOSS if e.is_boss else S.ENEMY
        if c.phase == Phase.TELEGRAPH:
            enemy_color = lerp_color(enemy_color, S.TELEGRAPH, 0.75)
        elif c.phase == Phase.WINDOW:
            enemy_color = S.PARRY_FLASH
        elif c.phase == Phase.STUN:
            enemy_color = S.STUN
        elif c.phase == Phase.DEAD:
            enemy_color = S.MUTED

        _, eang, elean, efallen, ewalk, ecrouch = self._enemy_depth_pose()
        for gx, gy, gs, ga, glife, gcol in self._ghosts:
            a = max(0.12, glife / 0.18 * 0.45)
            draw_stick(
                layer, gx, gy, gs, gcol,
                view="front", sword_ang=ga, walk=ewalk, lean=elean,
                thickness=3.0, alpha=a, idle_t=self.fx.time, crouch=0.1,
            )

        e_alpha = 1.0
        if c.phase == Phase.DEAD:
            e_alpha = max(0.35, 1.0 - efallen * 0.5)
        elif c.phase == Phase.SPAWN:
            e_alpha = min(1.0, self._spawn_t / 0.35)
        self._draw_fighter_at(
            layer, self._disp_e, "front", enemy_color,
            eang, elean, efallen, ewalk, ecrouch,
            4.0 if e.is_boss else 3.0, e_alpha,
            1.22 if e.is_boss else 1.0,
        )

        if c.phase == Phase.WINDOW:
            glow = 0.55 + 0.45 * math.sin(self.fx.time * 28)
            bar_c = lerp_color(S.PARRY_FLASH, S.WHITE, glow)
            pygame.draw.rect(layer, bar_c, (40, 70, S.WIDTH - 80, 6), border_radius=4)
            _center_text(layer, "NOW", 92, 22, bar_c)
        elif c.phase == Phase.TELEGRAPH:
            _center_text(layer, "WATCH", 92, 18, S.TELEGRAPH)
        elif c.phase == Phase.STUN:
            _center_text(layer, "OPEN", 92, 18, S.STUN)

        _, pang, plean, pfallen, pwalk, pcrouch = self._player_depth_pose()
        pcol = S.PLAYER
        if self.fx.player_hurt_t > 0:
            pcol = lerp_color(S.PLAYER, S.RED, min(1.0, self.fx.player_hurt_t / 0.25))
        elif self.fx.player_parry_t > 0:
            pcol = lerp_color(S.PLAYER, S.CYAN, 0.55)
        hand = self._draw_fighter_at(
            layer, self._disp_p, "back", pcol,
            pang, plean, pfallen, pwalk, pcrouch,
            3.5, 1.0 if c.player.alive else 0.7,
        )

        _hp_bar(layer, 40, 700, S.WIDTH - 80, 16, self.fx.hp_player, S.GREEN)
        hearts = " ".join("♥" if i < c.player.hp else "♡" for i in range(c.player.max_hp))
        _center_text(layer, hearts, 732, 18, S.GREEN)
        _center_text(layer, "TAP to parry  ·  SWIPE to attack", 768, 15, S.MUTED)

        self.fx.draw_over(layer, _font(28), hand)
        surf.blit(layer, (ox, oy))
