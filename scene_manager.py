"""Scene backgrounds, scene visual settings, compact HUD, and animated portals."""
from pathlib import Path
import math
import random
import pygame


class SceneManager:
    # All visual sizing lives here. These are multipliers of the original art sizes.
    VISUALS = {
        'shrine': {
            'character_scale': {'player': .70, 'wizard': .75, 'shrine_master': .75},
            'portal_scale': .70,
            'hud_height': 64,
        },
        'mystic_valley': {
            'character_scale': {'player': .70, 'wizard': .75, 'shrine_master': .75},
            'portal_scale': .70,
            'hud_height': 64,
        },
        'haunted_forest': {
            'character_scale': {'player': .66, 'wizard': .75, 'shrine_master': .75, 'forest_guardian': .86},
            'portal_scale': .65,
            'hud_height': 64,
        },
    }
    BASE_CHARACTER_SIZES = {
        'player': (100, 105),
        'wizard': (100, 105),
        'shrine_master': (110, 125),
        'forest_guardian': (135, 155),
    }

    def __init__(self, root, village_surface, world_size):
        self.root = Path(root)
        self.world_size = world_size
        self.scene = 'shrine'
        self.backgrounds = {'shrine': village_surface}
        valley_path = self.root / 'scenes' / 'mystic_valley.png'
        if not valley_path.exists():
            raise FileNotFoundError(f'Place Mystic Valley artwork at: {valley_path}')
        valley = pygame.image.load(str(valley_path)).convert()
        self.backgrounds['mystic_valley'] = pygame.transform.smoothscale(valley, world_size)
        forest_path = self.root / 'scenes' / 'haunted_forest.png'
        if not forest_path.exists():
            raise FileNotFoundError(f'Place Haunted Forest artwork at: {forest_path}')
        forest = pygame.image.load(str(forest_path)).convert()
        self.backgrounds['haunted_forest'] = pygame.transform.smoothscale(forest, world_size)
        self.phase = 'none'
        self.timer = 0.0
        self.clock = 0.0
        self.portal_strength = 0.0
        self.rng = random.Random(28)
        self.particles = [(self.rng.random()*math.tau, self.rng.uniform(.6, 1.5), self.rng.random()*math.tau) for _ in range(42)]
        self.return_hint = False
        self.shrine_portal = pygame.Vector2(world_size[0]*.77, world_size[1]*.84)
        self.valley_portal = pygame.Vector2(world_size[0]*.20, world_size[1]*.84)
        self.destination_changed = False
        self.portal_destination = 'mystic_valley'
        self.forest_portal = pygame.Vector2(world_size[0]*.19, world_size[1]*.85)
        self.scene_titles = {'shrine': 'BLOODMOON SHRINE', 'mystic_valley': 'MYSTIC VALLEY', 'haunted_forest': 'HAUNTED FOREST'}

    @property
    def background(self):
        return self.backgrounds[self.scene]

    @property
    def cinematic(self):
        return self.phase in ('speaking', 'opening', 'transporting', 'arrival')

    def character_size(self, name, scene='shrine'):
        base = self.BASE_CHARACTER_SIZES[name]
        factor = self.VISUALS[scene]['character_scale'].get(name, 1.0)
        return tuple(max(1, round(v * factor)) for v in base)

    def draw_hud(self, screen, title_font, small_font, player, wizard, fps, detailed=False):
        """Small HUD by default; show all controls and diagnostics with detailed=True."""
        width = screen.get_width()
        height = 105 if detailed else self.VISUALS[self.scene]['hud_height']
        panel = pygame.Surface((width - 24, height), pygame.SRCALPHA)
        panel.fill((10, 10, 18, 178))
        screen.blit(panel, (12, 10))
        title = self.scene_titles[self.scene]
        screen.blit(title_font.render(title, True, (245, 211, 166)), (23, 13))
        if detailed:
            controls = ('WASD Move | Shift Run | E Talk | R Rain | G Effects | '
                        'F Fog | C Clouds | L Lights | V Fireflies | F2 Editor | F5 Save | F3 Debug')
            screen.blit(small_font.render(controls, True, (225, 225, 215)), (24, 50))
            status = (f'Warlock: {player.action.upper()} / {player.facing.upper()} | '
                      f'Wizard: {wizard.action.upper()} | FPS: {fps:.0f}')
            screen.blit(small_font.render(status, True, (255, 194, 154)), (24, 78))
        else:
            hint = 'WASD Move  |  Shift Run  |  E Interact  |  F2 Paths  |  F3 Debug'
            screen.blit(small_font.render(hint, True, (218, 211, 203)), (24, 46))

    def start_shrine_portal(self, destination='mystic_valley'):
        if destination not in ('mystic_valley', 'haunted_forest'):
            return False
        if self.scene != 'shrine' or self.cinematic:
            return False
        self.portal_destination = destination
        self.phase = 'speaking'
        self.timer = 0.0
        self.portal_strength = 0.0
        return True

    def start_return(self):
        if self.scene not in ('mystic_valley', 'haunted_forest') or self.cinematic:
            return False
        self.phase = 'transporting'
        self.timer = 0.0
        return True

    def update(self, dt, player):
        self.clock += dt
        self.destination_changed = False
        if self.phase == 'none':
            self.portal_strength = 1.0 if self.scene != 'shrine' else 0.0
            return
        self.timer += dt
        if self.phase == 'speaking' and self.timer >= 2.8:
            self.phase, self.timer = 'opening', 0.0
        elif self.phase == 'opening':
            self.portal_strength = min(1.0, self.timer/2.4)
            if self.timer >= 3.2:
                self.phase, self.timer = 'transporting', 0.0
        elif self.phase == 'transporting' and self.timer >= 1.15:
            if self.scene == 'shrine':
                self.scene = self.portal_destination
                if self.scene == 'haunted_forest':
                    player.position.update(self.world_size[0]*.31, self.world_size[1]*.86)
                else:
                    player.position.update(self.world_size[0]*.32, self.world_size[1]*.87)
            else:
                self.scene = 'shrine'
                player.position.update(self.world_size[0]*.69, self.world_size[1]*.87)
            player.set_animation('idle', 'down')
            self.destination_changed = True
            self.phase, self.timer = 'arrival', 0.0
        elif self.phase == 'arrival' and self.timer >= 1.15:
            self.phase, self.timer = 'none', 0.0

    def draw_portal(self, screen, camera):
        if self.scene == 'shrine':
            if self.portal_strength <= 0:
                return
            center = self.shrine_portal
            power = self.portal_strength
        elif self.scene == 'mystic_valley':
            center = self.valley_portal
            power = 1.0
        else:
            center = self.forest_portal
            power = 1.0
        sx, sy = center - camera
        sx, sy = round(sx), round(sy)
        scale = self.VISUALS[self.scene]['portal_scale']
        if not (-140 < sx < screen.get_width()+140 and -180 < sy < screen.get_height()+180):
            return
        w = max(2, round(48*power*scale))
        h = max(2, round(84*power*scale))
        layer = pygame.Surface((w*4+90, h*3+90), pygame.SRCALPHA)
        cx, cy = layer.get_width()//2, layer.get_height()//2
        for factor, alpha in [(1.45, 8), (1.22, 15), (1.08, 30)]:
            pygame.draw.ellipse(layer, (171, 42, 235, round(alpha*power)),
                                pygame.Rect(cx-w*factor, cy-h*factor, 2*w*factor, 2*h*factor))
        pygame.draw.ellipse(layer, (18, 3, 40, round(220*power)),
                            pygame.Rect(cx-w*.79, cy-h*.89, w*1.58, h*1.78))
        pygame.draw.ellipse(layer, (100, 23, 180, round(95*power)),
                            pygame.Rect(cx-w*.65, cy-h*.8, w*1.3, h*1.6))
        t = self.clock
        for ring in range(4):
            wobble = math.sin(t*2.3+ring*1.7)*3*scale
            rect = pygame.Rect(round(cx-w*(.88+ring*.09)+wobble), round(cy-h*(.94+ring*.05)),
                               round(w*(1.76+ring*.18)), round(h*(1.88+ring*.1)))
            pygame.draw.arc(layer, (225, 60+ring*30, 255, round(210*power)), rect,
                            t*(.7 if ring%2 else -.65)+ring, t*(.7 if ring%2 else -.65)+ring+math.pi*1.5,
                            max(1, round(3*power*scale)))
        for angle, speed, phase in self.particles:
            a = angle + t*speed
            rr = w*(1.15+.35*math.sin(t*1.7+phase))
            px = round(cx+math.cos(a)*rr)
            py = round(cy+math.sin(a)*h*.95)
            pygame.draw.circle(layer, (255, 145, 240, round(200*power)), (px, py), max(1, round(2*power*scale)))
        pygame.draw.ellipse(layer, (190, 75, 230, round(55*power)),
                            pygame.Rect(cx-w*1.25, cy+h*.83, w*2.5, h*.35))
        # Keep the portal's original world-space centre and interaction coordinates.
        screen.blit(layer, (sx-cx, sy-cy))

    def draw_transition(self, screen, font):
        if self.phase not in ('speaking', 'opening', 'transporting', 'arrival'):
            return
        if self.phase == 'speaking':
            dest = 'the Haunted Forest' if self.portal_destination == 'haunted_forest' else 'Mystic Valley'
            msg = f'Shrine Master: Beyond the veil lies {dest}. Beware what waits beyond.'
        elif self.phase == 'opening':
            msg = 'Shrine Master: By the blood moon, let the ancient gateway awaken!'
        elif self.phase == 'transporting':
            msg = 'The portal pulls you between worlds...'
        else:
            msg = self.scene_titles[self.scene]
        if self.phase in ('speaking', 'opening'):
            panel = pygame.Surface((screen.get_width()-100, 72), pygame.SRCALPHA)
            panel.fill((15, 9, 27, 225))
            screen.blit(panel, (50, screen.get_height()-112))
            label = font.render(msg, True, (248, 215, 182))
            if label.get_width() > screen.get_width()-140:
                label = pygame.transform.smoothscale(label, (screen.get_width()-140, label.get_height()))
            screen.blit(label, (70, screen.get_height()-92))
        if self.phase == 'transporting':
            alpha = min(255, int(255*self.timer/1.15))
        elif self.phase == 'arrival':
            alpha = max(0, int(255*(1-self.timer/1.15)))
        else:
            alpha = 0
        if alpha:
            cover = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            cover.fill((22, 3, 40, alpha))
            screen.blit(cover, (0, 0))
            if self.phase == 'arrival':
                title = font.render(msg, True, (255, 222, 200))
                title.set_alpha(max(0, 255-alpha))
                screen.blit(title, title.get_rect(center=(screen.get_width()//2, screen.get_height()//3)))

