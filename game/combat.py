"""Telegraph, parry window, damage, and riposte."""

from __future__ import annotations

from enum import Enum, auto

from game import settings as S
from game.entities import Enemy, Player
from game.input import Gesture
from game.waves import spec_for_wave


class Phase(Enum):
    SPAWN = auto()
    TELEGRAPH = auto()
    WINDOW = auto()
    HIT = auto()
    STUN = auto()
    RECOVERY = auto()
    COMBO_GAP = auto()
    DEAD = auto()


class Combat:
    def __init__(self) -> None:
        self.player = Player()
        self.wave = 1
        self.enemy = Enemy.from_spec(spec_for_wave(self.wave))
        self.phase = Phase.SPAWN
        self.timer = 0.0
        self.combo_left = self.enemy.combo_hits
        self.riposte_ready = False
        self.attack_cd = 0.0
        self.feedback = ""
        self.feedback_t = 0.0
        self.lunge = 0.0
        self.parried_this_hit = False
        self.events: list[str] = ["SPAWN"]

    def _set_feedback(self, text: str) -> None:
        self.feedback = text
        self.feedback_t = S.FEEDBACK_TIME
        self.events.append(text)

    def _begin_telegraph(self) -> None:
        self.phase = Phase.TELEGRAPH
        self.timer = self.enemy.telegraph
        self.parried_this_hit = False
        self.lunge = 0.0

    def _next_fight(self) -> None:
        if self.enemy.is_boss:
            self.player.hp = min(self.player.max_hp, self.player.hp + S.BOSS_HEAL)
            self._set_feedback("+1 HP")
        self.wave += 1
        self.enemy = Enemy.from_spec(spec_for_wave(self.wave))
        self.combo_left = self.enemy.combo_hits
        self.riposte_ready = False
        self.phase = Phase.SPAWN
        self.timer = S.SPAWN_DELAY
        self.lunge = 0.0
        self.events.append("SPAWN")

    def apply_gesture(self, gesture: Gesture) -> None:
        if not self.player.alive or self.phase == Phase.DEAD:
            return
        if gesture == Gesture.TAP:
            self._try_parry()
        elif gesture == Gesture.SWIPE:
            self._try_attack()

    def _try_parry(self) -> None:
        if self.phase == Phase.WINDOW and not self.parried_this_hit:
            self.parried_this_hit = True
            self.riposte_ready = True
            self.combo_left -= 1
            self._set_feedback("PARRY")
            if self.combo_left <= 0:
                self.phase = Phase.STUN
                self.timer = self.enemy.stun
            else:
                self.phase = Phase.COMBO_GAP
                self.timer = self.enemy.combo_gap
            return
        if self.phase in (Phase.TELEGRAPH, Phase.HIT, Phase.RECOVERY, Phase.COMBO_GAP):
            self._set_feedback("MISS")

    def _try_attack(self) -> None:
        if self.attack_cd > 0 or self.phase in (Phase.SPAWN, Phase.DEAD):
            return
        if not self.enemy.alive:
            return
        self.attack_cd = S.ATTACK_COOLDOWN
        if self.riposte_ready:
            dmg = S.RIPOSTE_DAMAGE
            self.riposte_ready = False
            self._set_feedback("RIPOSTE")
        else:
            dmg = S.REGULAR_DAMAGE
            self._set_feedback("HIT")
        self.enemy.hp = max(0, self.enemy.hp - dmg)
        if not self.enemy.alive:
            self.phase = Phase.DEAD
            self.timer = 0.55
            self._set_feedback("DOWN")

    def update(self, dt: float) -> None:
        if self.attack_cd > 0:
            self.attack_cd = max(0.0, self.attack_cd - dt)
        if self.feedback_t > 0:
            self.feedback_t = max(0.0, self.feedback_t - dt)
        else:
            self.feedback = ""

        if not self.player.alive:
            return

        self.timer -= dt
        if self.phase == Phase.TELEGRAPH:
            t = 1.0 - max(0.0, self.timer / max(0.001, self.enemy.telegraph))
            self.lunge = t * 0.55
        elif self.phase == Phase.WINDOW:
            self.lunge = 0.85
        elif self.phase == Phase.HIT:
            self.lunge = 1.0
        else:
            self.lunge *= max(0.0, 1.0 - dt * 6)

        if self.timer > 0:
            return

        if self.phase == Phase.SPAWN:
            self.combo_left = self.enemy.combo_hits
            self._begin_telegraph()
        elif self.phase == Phase.TELEGRAPH:
            self.phase = Phase.WINDOW
            self.timer = self.enemy.parry_window
            self.events.append("WINDOW")
        elif self.phase == Phase.WINDOW:
            if not self.parried_this_hit:
                self.phase = Phase.HIT
                self.timer = 0.18
                self.player.hp = max(0, self.player.hp - 1)
                self.riposte_ready = False
                self._set_feedback("STRUCK")
        elif self.phase == Phase.HIT:
            if not self.player.alive:
                return
            self.combo_left -= 1
            if self.combo_left > 0:
                self.phase = Phase.COMBO_GAP
                self.timer = self.enemy.combo_gap
            else:
                self.phase = Phase.RECOVERY
                self.timer = self.enemy.recovery
        elif self.phase == Phase.STUN:
            self.combo_left = self.enemy.combo_hits
            self._begin_telegraph()
        elif self.phase == Phase.RECOVERY:
            self.combo_left = self.enemy.combo_hits
            self._begin_telegraph()
        elif self.phase == Phase.COMBO_GAP:
            self._begin_telegraph()
        elif self.phase == Phase.DEAD:
            self._next_fight()
