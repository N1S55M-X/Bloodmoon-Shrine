"""AI-directed forest events. Optional local GGUF; never executes model-generated code."""
import json
import math
import random
import threading
import queue
from pathlib import Path
import pygame

ACTIONS = ('ambient', 'light', 'fog', 'flames', 'message', 'shake', 'pulse', 'guardian')

class ForestDirector:
    def __init__(self, root, world_size):
        self.root = Path(root)
        self.world_size = world_size
        self.rng = random.Random()
        self.events = []
        self.flames = []
        self.messages = []
        self.time = 0.0
        self.next_decision = 4.0
        self.darkness = 35
        self.fog = 0
        self.tint = (45, 105, 220)
        self.shake = 0.0
        self.active = False
        self._requests = queue.Queue(maxsize=1)
        self._responses = queue.Queue(maxsize=2)
        self._worker = None
        self._model_status = 'not loaded'
        self.history = []
        self.guardian_commands = []
        self._last_player = None

    def _start_worker(self):
        if self._worker is not None:
            return
        self._worker = threading.Thread(target=self._model_loop, daemon=True)
        self._worker.start()

    def _model_loop(self):
        try:
            from llama_cpp import Llama
            models = list((self.root / 'models').rglob('*.gguf'))
            if not models:
                raise FileNotFoundError('No .gguf found under models/')
            chosen = next((p for p in models if 'Qwen3-4B-Instruct-2507-Q4_K_M' in p.name), models[0])
            self._model_status = 'loading'
            llm = Llama(model_path=str(chosen), n_ctx=2048, n_threads=4, verbose=False)
            self._model_status = 'ready'
            while True:
                snapshot = self._requests.get()
                prompt = ('You direct a dark fantasy forest. Output ONLY one JSON object with keys '
                          '"actions" (list of 1 to 4 actions). Valid actions: '
                          '{"type":"ambient","darkness":0..160}, '
                          '{"type":"fog","density":0..160}, '
                          '{"type":"light","color":"blue|red|violet|green"}, '
                          '{"type":"flames","count":1..8,"behavior":"orbit|follow|scatter|gather"}, '
                          '{"type":"message","text":"short eerie phrase"}, '
                          '{"type":"shake","intensity":0..8}, '
                          '{"type":"pulse"}, '
                          '{"type":"guardian","move":"teleport|charge|grow|jumpscare|vanish|stalk"}. No extra keys or markdown. '
                          'Create atmospheric surprises, not random noise. Avoid repeating previous events. '
                          'Never block the exit or obscure the entire screen. '
                          'World state: ' + json.dumps(snapshot))
                try:
                    result = llm.create_chat_completion(
                        messages=[{'role':'system','content':'You are the ancient Forest Guardian, a creative cinematic director. Return valid JSON only.'},
                                  {'role':'user','content':prompt}],
                        max_tokens=220, temperature=0.85)
                    raw = result['choices'][0]['message']['content']
                    parsed = json.loads(raw[raw.find('{'):raw.rfind('}')+1])
                    self._responses.put_nowait(parsed)
                except Exception:
                    try:
                        self._responses.put_nowait(None)
                    except queue.Full:
                        pass
        except Exception as exc:
            self._model_status = 'fallback: ' + str(exc)[:70]

    def _fallback(self, distance):
        options = [
            [{'type':'flames','count':4,'behavior':'orbit'}, {'type':'message','text':'The roots remember your footsteps.'}],
            [{'type':'fog','density':85}, {'type':'light','color':'violet'}, {'type':'message','text':'Something watches from the mist.'}],
            [{'type':'light','color':'red'}, {'type':'pulse'}, {'type':'message','text':'Do not wake what sleeps below.'}],
            [{'type':'flames','count':6,'behavior':'scatter'}, {'type':'shake','intensity':3}],
            [{'type':'ambient','darkness':95}, {'type':'flames','count':3,'behavior':'follow'}, {'type':'message','text':'We see you.'}],
            [{'type':'ambient','darkness':35}, {'type':'fog','density':25}, {'type':'light','color':'blue'}],
            [{'type':'guardian','move':self.rng.choice(('teleport','charge','grow','jumpscare','vanish','stalk'))}, {'type':'message','text':'The forest is alive.'}],
        ]
        return self.rng.choice(options)

    def _apply(self, actions, player):
        if not isinstance(actions, list):
            return
        for action in actions[:4]:
            if not isinstance(action, dict):
                continue
            kind = action.get('type')
            if kind not in ACTIONS:
                continue
            if kind == 'ambient':
                self.darkness = max(0, min(145, int(action.get('darkness', 40))))
            elif kind == 'fog':
                self.fog = max(0, min(135, int(action.get('density', 35))))
            elif kind == 'light':
                self.tint = {'blue':(40,120,255),'red':(240,45,65),
                             'violet':(160,65,245),'green':(55,225,155)}.get(action.get('color'), (45,105,220))
            elif kind == 'flames':
                count = max(1, min(8, int(action.get('count', 3))))
                behavior = action.get('behavior')
                if behavior not in ('orbit','follow','scatter','gather'):
                    behavior = 'orbit'
                self.flames = [{'phase':self.rng.uniform(0,math.tau), 'radius':self.rng.uniform(60,135),
                                'behavior':behavior, 'age':0.0, 'duration':self.rng.uniform(9,15),
                                'origin':pygame.Vector2(player)} for _ in range(count)]
            elif kind == 'message':
                msg = str(action.get('text', ''))[:85].strip()
                if msg:
                    self.messages.append([msg, 5.5])
                    self.messages = self.messages[-3:]
            elif kind == 'shake':
                self.shake = max(self.shake, min(8, max(0, float(action.get('intensity', 2)))))
            elif kind == 'guardian':
                move = action.get('move')
                if move in ('teleport','charge','grow','jumpscare','vanish','stalk'):
                    self.guardian_commands.append(move)
                    self.guardian_commands = self.guardian_commands[-3:]
            elif kind == 'pulse':
                self.events.append(['pulse', 1.4])
        self.history.append(','.join(str(a.get('type')) for a in actions[:4] if isinstance(a,dict)))
        self.history = self.history[-6:]

    def update(self, dt, player, guardian, scene_active, paused=False):
        self.active = scene_active
        if not scene_active:
            return
        self.time += dt
        self.next_decision -= dt
        self.shake = max(0, self.shake - dt * 5)
        for m in self.messages:
            m[1] -= dt
        self.messages = [m for m in self.messages if m[1] > 0]
        for e in self.events:
            e[1] -= dt
        self.events = [e for e in self.events if e[1] > 0]
        for flame in self.flames:
            flame['age'] += dt
        self.flames = [f for f in self.flames if f['age'] < f['duration']]
        if paused:
            return
        try:
            result = self._responses.get_nowait()
            if result and isinstance(result,dict):
                self._apply(result.get('actions', []), player)
            else:
                self._apply(self._fallback(0), player)
        except queue.Empty:
            pass
        if self.next_decision <= 0:
            distance = int(pygame.Vector2(player).distance_to(guardian))
            snapshot = {'player_distance':distance, 'player_x':int(player[0]),
                        'player_y':int(player[1]), 'guardian_x':int(guardian[0]),
                        'guardian_y':int(guardian[1]), 'recent_events':self.history}
            self._start_worker()
            if self._model_status == 'ready':
                try:
                    self._requests.put_nowait(snapshot)
                except queue.Full:
                    pass
            else:
                self._apply(self._fallback(distance), player)
            self.next_decision = self.rng.uniform(8, 13)

    def draw(self, screen, camera, player):
        if not self.active:
            return
        w,h = screen.get_size()
        if self.darkness:
            shade = pygame.Surface((w,h), pygame.SRCALPHA)
            shade.fill((2,4,14,self.darkness))
            screen.blit(shade,(0,0))
        if self.fog:
            fog = pygame.Surface((w,h), pygame.SRCALPHA)
            fog.fill((38,58,92,min(85,self.fog//2)))
            screen.blit(fog,(0,0))
        for f in self.flames:
            age = f['age']; phase = f['phase']; mode = f['behavior']
            origin = pygame.Vector2(player) if mode in ('follow','orbit') else f['origin']
            r = f['radius']
            if mode == 'scatter':
                r += age*20
            elif mode == 'gather':
                r = max(22,r-age*12)
            x = origin.x + math.cos(self.time*0.9+phase)*r - camera.x
            y = origin.y + math.sin(self.time*0.75+phase)*r*.5 - camera.y - 35
            x += math.sin(self.time*2+phase)*7
            y += math.sin(self.time*3+phase)*9
            if not (-70<x<w+70 and -70<y<h+70):
                continue
            glow = pygame.Surface((110,110),pygame.SRCALPHA)
            for radius,alpha in [(47,9),(32,16),(20,30),(10,70)]:
                pygame.draw.circle(glow,(*self.tint,alpha),(55,55),radius)
            screen.blit(glow,(int(x)-55,int(y)-55),special_flags=pygame.BLEND_RGBA_ADD)
            pygame.draw.circle(screen,self.tint,(int(x),int(y)),6)
            pygame.draw.circle(screen,(215,245,255),(int(x),int(y)),2)
        if self.events:
            alpha = int((math.sin(self.time*8)+1)*15)
            flash = pygame.Surface((w,h),pygame.SRCALPHA)
            flash.fill((*self.tint,alpha))
            screen.blit(flash,(0,0))
        if self.messages:
            text,ttl = self.messages[-1]
            font = pygame.font.SysFont('georgia', 26, bold=True)
            rendered = font.render(text,True,(225,205,230))
            if rendered.get_width() > w-40:
                rendered = pygame.transform.smoothscale(rendered,(w-40,max(16,int(rendered.get_height()*(w-40)/rendered.get_width()))))
            panel = pygame.Surface((rendered.get_width()+34,rendered.get_height()+22),pygame.SRCALPHA)
            panel.fill((5,6,18,160))
            px=(w-panel.get_width())//2; py=int(h*.22)
            screen.blit(panel,(px,py))
            screen.blit(rendered,(px+17,py+11))

