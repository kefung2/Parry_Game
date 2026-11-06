"""Player and enemy combatants."""

from __future__ import annotations

from dataclasses import dataclass

from game import settings as S
from game.waves import FightSpec


@dataclass
class Player:
    hp: int = S.PLAYER_MAX_HP
    max_hp: int = S.PLAYER_MAX_HP

    @property
    def alive(self) -> bool:
        return self.hp > 0


@dataclass
class Enemy:
    hp: int
    max_hp: int
    is_boss: bool
    telegraph: float
    parry_window: float
    recovery: float
    stun: float
    combo_hits: int
    combo_gap: float

    @property
    def alive(self) -> bool:
        return self.hp > 0

    @classmethod
    def from_spec(cls, spec: FightSpec) -> Enemy:
        return cls(
            hp=spec.hp,
            max_hp=spec.hp,
            is_boss=spec.is_boss,
            telegraph=spec.telegraph,
            parry_window=spec.parry_window,
            recovery=spec.recovery,
            stun=spec.stun,
            combo_hits=spec.combo_hits,
            combo_gap=spec.combo_gap,
        )
