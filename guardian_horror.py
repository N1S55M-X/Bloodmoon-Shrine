"""Nonblocking cinematic movement for existing AnimatedCharacter sprites."""
import math
import random
import pygame

class GuardianHorror:
    ACTIONS = ('teleport', 'charge', 'grow', 'jumpscare', 'vanish', 'stalk')
    def __init__(self, guardian, can_walk=None):
        self.guardian = guardian
        self.can_walk = can_walk or (lambda x, y: True)
        self.rng = random.Random()
        self.mode = 'idle'
        self.elapsed = 0.0
        self.duration = 1.0
        self.scale = 1.0
        self.opacity = 255
        self.shake = 0.0
        self.flash = 0.0
        self.cooldown = 0.0
        self.smoke = []
        self.afterimages = []
        self.start = guardian.position.copy()
        self.target = guardian.position.copy()

    @property
    def busy(self):
        return self.mode != 'idle'

    def nearby_point(self, player, near, far):
        player = pygame.Vector2(player)
        for _ in range(48):
            angle = self.rng.uniform(0, math.tau)
            r = self.rng.uniform(near, far)
            p = player + pygame.Vector2(math.cos(angle), math.sin(angle)) * r
            if self.can_walk(p.x, p.y):
                return p
        return self.guardian.position.copy()

    def burst(self, point, count=22):
        for _ in range(count):
            a = self.rng.uniform(0, math.tau)
            speed = self.rng.uniform(15, 95)
            life = self.rng.uniform(.45, 1.1)
            self.smoke.append([pygame.Vector2(point), pygame.Vector2(math.cos(a)*speed, math.sin(a)*speed-20), life, life, self.rng.uniform(4, 14)])
        self.smoke = self.smoke[-180:]

    def trigger(self, action, player):
        if action not in self.ACTIONS or self.busy or self.cooldown > 0:
            return False
        self.mode = action
        self.elapsed = 0.0
        self.start = self.guardian.position.copy()
        self.target = pygame.Vector2(player)
        self.scale = 1.0
        self.opacity = 255
        self.cooldown = 5.0
        self.duration = {'teleport':1.25,'charge':1.2,'grow':3.4,'jumpscare':1.6,'vanish':2.5,'stalk':3.0}[action]
        if action == 'teleport':
            self.target = self.nearby_point(player, 100, 175)
            self.burst(self.start, 32)
        elif action == 'jumpscare':
            self.target = self.nearby_point(player, 65, 95)
            self.burst(self.start, 36)
        elif action == 'stalk':
            self.target = self.nearby_point(player, 115, 180)
        elif action == 'charge':
            delta = self.target - self.start
            if delta.length() > 70:
                self.target -= delta.normalize()*65
        elif action == 'vanish':
            self.burst(self.start, 28)
        return True

    def update(self, dt, player):
        dt = min(max(0.0, dt), .05)
        self.cooldown = max(0.0, self.cooldown-dt)
        self.shake = max(0.0, self.shake-15*dt)
        self.flash = max(0.0, self.flash-2.6*dt)
        for p in self.smoke:
            p[0] += p[1]*dt
            p[1] *= max(0, 1-dt*1.5)
            p[2] -= dt
        self.smoke = [p for p in self.smoke if p[2] > 0]
        for p in self.afterimages:
            p[2] -= dt
        self.afterimages = [p for p in self.afterimages if p[2] > 0]
        if not self.busy:
            return
        self.elapsed += dt
        t = min(1, self.elapsed/self.duration)
        g = self.guardian
        if self.mode == 'teleport':
            if t < .38:
                self.opacity = int(255*(1-t/.38))
            elif t < .53:
                self.opacity = 0
                g.position = self.target.copy()
            else:
                self.opacity = int(255*min(1,(t-.53)/.24))
                if .53 <= t < .57:
                    self.burst(g.position, 2)
            g.set_animation('idle')
        elif self.mode == 'charge':
            g.face_point(player)
            g.set_animation('run', g.facing)
            u = min(1, t/.78)
            eased = u*u*(3-2*u)
            candidate = self.start.lerp(self.target, eased)
            if self.can_walk(candidate.x, candidate.y):
                g.position = candidate
            if self.rng.random() < .6:
                self.afterimages.append([g.position.copy(), g.frame().copy(), .25])
            if t > .76:
                self.shake = max(self.shake, 2.0)
        elif self.mode == 'grow':
            self.scale = 1 + 2.0*(t/.42 if t < .42 else 1 if t < .72 else (1-t)/.28)
            self.shake = max(self.shake, 1.5)
            g.face_point(player)
        elif self.mode == 'jumpscare':
            if t < .27:
                self.opacity = int(255*(1-t/.27))
            elif t < .4:
                self.opacity = 0
                g.position = self.target.copy()
            elif t < .7:
                self.opacity = 255
                self.scale = 1+1.4*(1-(t-.4)/.3)
                self.shake = 7
                self.flash = .65
            else:
                self.opacity = 255
                self.scale = 1
            g.face_point(player)
        elif self.mode == 'vanish':
            self.opacity = int(255*(1-t/.25)) if t < .25 else 0 if t < .78 else int(255*(t-.78)/.22)
            if .78 <= t < .82:
                self.burst(g.position, 2)
        elif self.mode == 'stalk':
            candidate = self.start.lerp(self.target, t*t*(3-2*t))
            if self.can_walk(candidate.x, candidate.y):
                g.position = candidate
            g.face_point(player)
            g.set_animation('walk', g.facing)
        if t >= 1:
            self.mode = 'idle'
            self.scale = 1
            self.opacity = 255
            g.set_animation('idle')
            self.burst(g.position, 9)

    def draw(self, screen, camera):
        g = self.guardian
        for pos, frame, life in self.afterimages:
            image = frame.copy()
            image.set_alpha(int(100*life/.25))
            xy = pos-camera
            screen.blit(image, image.get_rect(midbottom=(round(xy.x),round(xy.y))))
        if self.opacity > 0:
            image = g.frame().copy()
            if abs(self.scale-1)>0.01:
                image = pygame.transform.smoothscale(image,(max(1,round(image.get_width()*self.scale)),max(1,round(image.get_height()*self.scale))))
            image.set_alpha(self.opacity)
            xy = g.position-camera
            if self.opacity > 100:
                pygame.draw.ellipse(screen,(9,8,17),(round(xy.x-g.size[0]*.25),round(xy.y-6),round(g.size[0]*.5),9))
            screen.blit(image,image.get_rect(midbottom=(round(xy.x),round(xy.y))))
        if self.smoke:
            layer = pygame.Surface(screen.get_size(),pygame.SRCALPHA)
            for pos,vel,life,maxlife,r in self.smoke:
                xy = pos-camera
                pygame.draw.circle(layer,(18,12,34,int(105*life/maxlife)),(round(xy.x),round(xy.y-25)),round(r))
            screen.blit(layer,(0,0))

    def draw_flash(self, screen):
        if self.flash > 0:
            layer = pygame.Surface(screen.get_size(),pygame.SRCALPHA)
            layer.fill((170,15,40,int(105*self.flash)))
            screen.blit(layer,(0,0))

