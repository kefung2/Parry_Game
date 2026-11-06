"""Wave / fight progression. Every 5th fight is a boss."""

from __future__ import annotations

from dataclasses import dataclass

from game import settings as S


@dataclass(frozen=True)
class FightSpec:
    wave: int
    is_boss: bool
    hp: int
    telegraph: float
    parry_window: float
    recovery: float
    stun: float
    combo_hits: int
    combo_gap: float


def spec_for_wave(wave: int) -> FightSpec:
    is_boss = wave > 0 and wave % S.BOSS_EVERY == 0
    if is_boss:
        extra = (wave // S.BOSS_EVERY - 1)
        return FightSpec(
            wave=wave,
            is_boss=True,
            hp=S.BOSS_HP + extra * 2,
            telegraph=max(0.36, S.BOSS_TELEGRAPH - extra * 0.02),
            parry_window=max(0.09, S.BOSS_PARRY - extra * 0.01),
            recovery=S.BOSS_RECOVERY,
            stun=S.BOSS_STUN,
            combo_hits=S.BOSS_COMBO,
            combo_gap=S.BOSS_COMBO_GAP,
        )
    extra = (wave - 1) // S.BOSS_EVERY
    return FightSpec(
        wave=wave,
        is_boss=False,
        hp=S.REGULAR_HP + extra,
        telegraph=max(0.42, S.REGULAR_TELEGRAPH - extra * 0.03),
        parry_window=max(0.12, S.REGULAR_PARRY - extra * 0.01),
        recovery=S.REGULAR_RECOVERY,
        stun=S.REGULAR_STUN,
        combo_hits=S.REGULAR_COMBO,
        combo_gap=0.0,
    )
