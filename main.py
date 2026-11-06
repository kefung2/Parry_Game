"""Parry Game — tap to parry, swipe to attack.

Desktop: python main.py
Browser (WebAssembly): python -m pygbag --build .
"""

from __future__ import annotations

import asyncio

import pygame

from game import settings as S
from game.scenes import BattleScene, GameOverScene, MenuScene


async def main() -> None:
    pygame.init()
    pygame.display.set_caption(S.TITLE)
    screen = pygame.display.set_mode((S.WIDTH, S.HEIGHT))
    clock = pygame.time.Clock()
    scene: MenuScene | BattleScene | GameOverScene = MenuScene()
    running = True

    while running:
        dt = min(0.05, clock.tick(S.FPS) / 1000.0)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
                break
            nxt = scene.handle(event)
            if nxt == "battle":
                scene = BattleScene()
        if not running:
            break

        nxt = scene.update(dt)
        if nxt == "gameover":
            wave = scene.combat.wave if isinstance(scene, BattleScene) else 1
            scene = GameOverScene(wave)
        elif nxt == "battle":
            scene = BattleScene()

        scene.draw(screen)
        pygame.display.flip()
        await asyncio.sleep(0)

    pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())
