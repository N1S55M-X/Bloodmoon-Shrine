"""Reusable procedural atmosphere for Bloodmoon Shrine. Requires pygame-ce only.

All positions are world coordinates except rain (screen-space weather).
No external art assets or shader/OpenGL dependencies are required.
"""
import math
import random
import pygame


class ShrineEnvironment:
    def __init__(self, world_size, screen_size, seed=42):
        self.world_w, self.world_h = world_size
        self.screen_w, self.screen_h = screen_size
        self.rng = random.Random(seed)
        self.time = 0.0
        self.wind = 0.30
        self.fog = True
        self.clouds = True
        self.fireflies = True
        self.torches = True
        self.runes = True
        self.rain = False
        self.fog_patches = [
            (self.rng.uniform(-150, self.world_w + 150),
             self.rng.uniform(self.world_h * .42, self.world_h * .98),
             self.rng.uniform(90, 210), self.rng.uniform(3, 12),
             self.rng.uniform(0, math.tau)) for _ in range(30)
        ]
        self.cloud_patches = [
            (self.rng.uniform(-300, self.world_w + 300),
             self.rng.uniform(0, self.world_h * .40),
             self.rng.uniform(115, 270), self.rng.uniform(3, 10)) for _ in range(13)
        ]
        self.firefly_points = [
            (self.rng.uniform(0, self.world_w),
             self.rng.uniform(self.world_h * .57, self.world_h * .96),
             self.rng.uniform(0, math.tau), self.rng.uniform(1.0, 3.0)) for _ in range(32)
        ]
        self.embers = [
            (self.rng.uniform(0, self.world_w),
             self.rng.uniform(self.world_h * .45, self.world_h * .95),
             self.rng.uniform(0, math.tau)) for _ in range(18)
        ]
        self.rain_drops = [
            [self.rng.uniform(0, self.screen_w),
             self.rng.uniform(0, self.screen_h),
             self.rng.uniform(350, 640)] for _ in range(175)
        ]
        # These positions are normalized to the original village background.
        # Adjust in the scene editor later to match the actual flame locations.
        self.torch_points = [(.075, .36), (.40, .45), (.78, .63), (.90, .53)]
        self.rune_point = (.735, .26)

    def update(self, dt):
        self.time += dt
        if self.rain:
            for drop in self.rain_drops:
                drop[0] -= (100 + 90 * self.wind) * dt
                drop[1] += drop[2] * dt
                if drop[1] > self.screen_h + 16 or drop[0] < -20:
                    drop[0] = self.rng.uniform(0, self.screen_w + 50)
                    drop[1] = self.rng.uniform(-90, -10)

    def _screen_point(self, nx, ny, camera):
        return round(nx * self.world_w - camera.x), round(ny * self.world_h - camera.y)

    @staticmethod
    def _glow(surface, pos, radius, color, strength=1.0):
        x, y = pos
        if x < -radius or x > surface.get_width() + radius or y < -radius or y > surface.get_height() + radius:
            return
        for factor, alpha in ((1.0, 9), (.72, 15), (.45, 22), (.20, 42)):
            pygame.draw.circle(surface, (*color, max(0, min(255, int(alpha * strength)))),
                               (x, y), max(1, round(radius * factor)))

    def draw_background(self, screen, camera):
        """Draw cloud shadows above the static scene but behind characters."""
        if not self.clouds:
            return
        layer = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        for x0, y0, width, speed in self.cloud_patches:
            x = ((x0 + self.time * speed * (1 + self.wind)) % (self.world_w + 2 * width)) - width - camera.x
            y = y0 - camera.y
            if -width < x < self.screen_w + width:
                pygame.draw.ellipse(layer, (12, 17, 34, 18),
                                    (round(x), round(y), round(width), round(width * .25)))
                pygame.draw.ellipse(layer, (100, 105, 140, 8),
                                    (round(x + width * .2), round(y - width * .06),
                                     round(width * .75), round(width * .20)))
        screen.blit(layer, (0, 0))

    def draw_world_lights(self, screen, camera):
        """Torches and shrine rune, drawn over scenery and characters."""
        layer = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        if self.torches:
            for i, point in enumerate(self.torch_points):
                x, y = self._screen_point(*point, camera)
                flicker = 1 + .13 * math.sin(self.time * 12 + i * 2.2) + .06 * math.sin(self.time * 19 + i)
                self._glow(layer, (x, y), round(60 * flicker), (255, 112, 30), 1.3)
                self._glow(layer, (x, y), round(21 * flicker), (255, 198, 80), 1.1)
                if 0 <= x < self.screen_w and 0 <= y < self.screen_h:
                    pygame.draw.circle(layer, (255, 205, 110, 95), (x, y), 3)
        if self.runes:
            x, y = self._screen_point(*self.rune_point, camera)
            pulse = (math.sin(self.time * 2.3) + 1) * .5
            self._glow(layer, (x, y), round(60 + pulse * 14), (230, 32, 72), .8 + pulse)
            if 0 <= x < self.screen_w and 0 <= y < self.screen_h:
                pygame.draw.circle(layer, (255, 70, 100, round(50 + 65 * pulse)),
                                   (x, y), 28, 2)
        screen.blit(layer, (0, 0))

    def draw_foreground(self, screen, camera):
        """Ground fog, drifting embers, fireflies, then optional rain."""
        layer = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        if self.fog:
            for x0, y0, radius, speed, phase in self.fog_patches:
                travel = self.time * speed * (1 + self.wind)
                x = ((x0 + travel) % (self.world_w + 2 * radius)) - radius - camera.x
                y = y0 - camera.y + math.sin(self.time * .35 + phase) * 8
                if -radius < x < self.screen_w + radius:
                    pygame.draw.ellipse(layer, (178, 188, 211, 12),
                                        (round(x - radius), round(y - radius * .22),
                                         round(2 * radius), round(radius * .46)))
        if self.fireflies:
            for x0, y0, phase, speed in self.firefly_points:
                x = x0 + math.sin(self.time * .8 + phase) * 15 - camera.x
                y = y0 + math.cos(self.time * speed + phase) * 12 - camera.y
                brightness = (math.sin(self.time * speed * 2 + phase) + 1) * .5
                if brightness > .28:
                    self._glow(layer, (round(x), round(y)), 10, (210, 225, 120), brightness * .8)
                    pygame.draw.circle(layer, (240, 240, 160, round(90 * brightness)),
                                       (round(x), round(y)), 2)
        if self.torches:
            for x0, y0, phase in self.embers:
                x = x0 + math.sin(self.time + phase) * 24 - camera.x
                y = ((y0 - self.time * 9) % self.world_h) - camera.y
                if 0 <= x < self.screen_w and 0 <= y < self.screen_h:
                    pygame.draw.circle(layer, (255, 137, 65, 65), (round(x), round(y)), 1)
        screen.blit(layer, (0, 0))
        if self.rain:
            rain_layer = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            for x, y, speed in self.rain_drops:
                pygame.draw.line(rain_layer, (160, 185, 225, 88),
                                 (round(x), round(y)), (round(x - 4), round(y + 12)), 1)
            screen.blit(rain_layer, (0, 0))

