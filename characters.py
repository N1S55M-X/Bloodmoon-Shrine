"""Reusable 4x12 character animations for Bloodmoon Shrine."""
from pathlib import Path
import pygame

DIRECTIONS = ('down', 'left', 'right', 'up')
FPS_BY_ACTION = {'idle': 1.0, 'walk': 4.0, 'run': 7.0}

class AnimatedCharacter:
    def __init__(self, atlas_path, x, y, size=(100, 105), facing='down'):
        path = Path(atlas_path)
        if not path.is_file():
            raise FileNotFoundError(f'Missing character atlas: {path}')
        sheet = pygame.image.load(str(path)).convert_alpha()
        self.position = pygame.Vector2(x, y)
        self.facing = facing
        self.action = 'idle'
        self.time = 0.0
        self.frame_index = 0
        self.animations = {}
        self.size = tuple(max(1, round(v)) for v in size)
        w, h = sheet.get_size()
        for row, direction in enumerate(DIRECTIONS):
            frames = []
            for col in range(12):
                x0, x1 = round(col*w/12), round((col+1)*w/12)
                y0, y1 = round(row*h/4), round((row+1)*h/4)
                frame = sheet.subsurface((x0, y0, x1-x0, y1-y0)).copy()
                frames.append(pygame.transform.smoothscale(frame, self.size))
            self.animations[f'idle_{direction}'] = frames[:4]
            self.animations[f'walk_{direction}'] = frames[4:8]
            self.animations[f'run_{direction}'] = frames[8:12]

    def set_animation(self, action, facing=None):
        facing = self.facing if facing is None else facing
        if action not in FPS_BY_ACTION or facing not in DIRECTIONS:
            raise ValueError(f'Unknown animation: {action}/{facing}')
        if (action, facing) != (self.action, self.facing):
            self.action, self.facing = action, facing
            self.time = 0.0
            self.frame_index = 0

    def update(self, dt):
        self.time += dt
        frames = self.animations[f'{self.action}_{self.facing}']
        self.frame_index = int(self.time * FPS_BY_ACTION[self.action]) % len(frames)

    def frame(self):
        return self.animations[f'{self.action}_{self.facing}'][self.frame_index]

    def draw(self, surface, camera):
        x, y = self.position - camera
        shadow_w = max(16, round(self.size[0] * .48))
        shadow_h = max(5, round(self.size[1] * .095))
        pygame.draw.ellipse(surface, (17, 13, 23),
                            (round(x-shadow_w/2), round(y-shadow_h*.6), shadow_w, shadow_h))
        sprite = self.frame()
        surface.blit(sprite, sprite.get_rect(midbottom=(round(x), round(y))))

    def face_point(self, point):
        delta = pygame.Vector2(point) - self.position
        if abs(delta.x) > abs(delta.y):
            direction = 'right' if delta.x > 0 else 'left'
        else:
            direction = 'down' if delta.y > 0 else 'up'
        self.set_animation('idle', direction)

