"""Pointer input: tap to parry, swipe to attack."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

import pygame

from game import settings as S


class Gesture(Enum):
    NONE = auto()
    TAP = auto()
    SWIPE = auto()


@dataclass
class PointerState:
    down: bool = False
    start: tuple[float, float] = (0.0, 0.0)
    current: tuple[float, float] = (0.0, 0.0)
    swiped: bool = False


def _pos(event: pygame.event.Event) -> tuple[float, float]:
    if hasattr(event, "x") and event.type in (pygame.FINGERDOWN, pygame.FINGERUP, pygame.FINGERMOTION):
        return event.x * S.WIDTH, event.y * S.HEIGHT
    return float(event.pos[0]), float(event.pos[1])


class PointerInput:
    def __init__(self) -> None:
        self._p = PointerState()

    def handle(self, event: pygame.event.Event) -> Gesture:
        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.FINGERDOWN):
            if event.type == pygame.MOUSEBUTTONDOWN and getattr(event, "button", 1) != 1:
                return Gesture.NONE
            pos = _pos(event)
            self._p = PointerState(down=True, start=pos, current=pos, swiped=False)
            return Gesture.NONE

        if event.type in (pygame.MOUSEMOTION, pygame.FINGERMOTION):
            if not self._p.down or self._p.swiped:
                return Gesture.NONE
            self._p.current = _pos(event)
            dx = self._p.current[0] - self._p.start[0]
            dy = self._p.current[1] - self._p.start[1]
            if (dx * dx + dy * dy) ** 0.5 >= S.SWIPE_THRESHOLD:
                self._p.swiped = True
                return Gesture.SWIPE
            return Gesture.NONE

        if event.type in (pygame.MOUSEBUTTONUP, pygame.FINGERUP):
            if event.type == pygame.MOUSEBUTTONUP and getattr(event, "button", 1) != 1:
                return Gesture.NONE
            if not self._p.down:
                return Gesture.NONE
            was_swipe = self._p.swiped
            self._p.down = False
            if was_swipe:
                return Gesture.NONE
            return Gesture.TAP

        return Gesture.NONE
