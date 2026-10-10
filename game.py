import json
import math
import random
import textwrap
from pathlib import Path
import pygame
from characters import AnimatedCharacter
from environment import ShrineEnvironment
from scene_manager import SceneManager
from npc_ai import WizardAI
from world_ai import ForestDirector
from guardian_horror import GuardianHorror
# ============================================================
# GAME SETUP
# ============================================================
pygame.init()
ROOT = Path(__file__).resolve().parent
SCREEN_W, SCREEN_H = 1100, 700
FPS = 60
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("Bloodmoon Shrine")
clock = pygame.time.Clock()
font = pygame.font.SysFont("georgia", 22)
small_font = pygame.font.SysFont("arial", 16)
tiny_font = pygame.font.SysFont("consolas", 15)
rng = random.Random(42)
village_file = ROOT / "assets" / "village.png"
world = pygame.image.load(str(village_file)).convert()
scale = max(
    1,
    SCREEN_W / world.get_width(),
    SCREEN_H / world.get_height()
)
if scale > 1:
    world = pygame.transform.smoothscale(
        world,
        (
            round(world.get_width() * scale),
            round(world.get_height() * scale)
        )
    )
WORLD_W, WORLD_H = world.get_size()
scene_manager = SceneManager(
    ROOT,
    world,
    (WORLD_W, WORLD_H)
)
# ============================================================
# CHARACTERS
# ============================================================
player = AnimatedCharacter(
    ROOT / "sprite_auto_output" / "atlas.png",
    WORLD_W * 0.50,
    WORLD_H * 0.88,
    size=scene_manager.character_size("player")
)
wizard = AnimatedCharacter(
    ROOT / "sprite_auto_output" / "wizard_v4" / "atlas.png",
    WORLD_W * 0.57,
    WORLD_H * 0.88,
    size=scene_manager.character_size("wizard"),
    facing="left"
)
shrine_master = AnimatedCharacter(
    ROOT / "sprite_auto_output" / "shm_v4" / "atlas.png",
    WORLD_W * 0.66,
    WORLD_H * 0.88,
    size=scene_manager.character_size("shrine_master"),
    facing="down"
)

# Forest monster uses the same 4-row x 12-column animation engine.
forest_guardian = AnimatedCharacter(
    ROOT / "assets" / "forest_guardian.png",
    WORLD_W * .64, WORLD_H * .79,
    size=scene_manager.character_size("forest_guardian", "haunted_forest"),
    facing="left"
)
forest_guardian_home = forest_guardian.position.copy()
forest_guardian_target = forest_guardian.position.copy()
forest_guardian_wait = 1.0
portal_choice_open = False
forest_director = ForestDirector(ROOT, (WORLD_W, WORLD_H))


# ============================================================
# COLLISION MASK
# ============================================================
DEFAULT_PATHS = [[
    [0, .88], [.12, .82], [.25, .84],
    [.39, .80], [.44, .72], [.49, .70],
    [.53, .77], [.63, .81], [.79, .83],
    [1, .85], [1, 1], [0, 1]
]]
collision_surface = pygame.Surface(
    (WORLD_W, WORLD_H),
    pygame.SRCALPHA
)
collision_surface.fill((0, 0, 0, 0))
collision_mask = pygame.mask.from_surface(collision_surface)
def mask_filename(scene):
    if scene == "shrine":
        return ROOT / "walkable_mask.png"
    return ROOT / "scenes" / f"{scene}_mask.png"
def legacy_filename(scene):
    if scene == "shrine":
        return ROOT / "walkable.json"
    return ROOT / "scenes" / f"{scene}_walkable.json"
def polygon_points(poly):
    return [
        (round(x * WORLD_W), round(y * WORLD_H))
        for x, y in poly
    ]
def update_collision_mask():
    global collision_mask
    collision_mask = pygame.mask.from_surface(collision_surface)
def load_collision(scene):
    global collision_surface
    collision_surface = pygame.Surface(
        (WORLD_W, WORLD_H),
        pygame.SRCALPHA
    )
    collision_surface.fill((0, 0, 0, 0))
    filename = mask_filename(scene)
    if filename.exists():
        loaded = pygame.image.load(
            str(filename)
        ).convert_alpha()
        if loaded.get_size() != (WORLD_W, WORLD_H):
            loaded = pygame.transform.scale(
                loaded, (WORLD_W, WORLD_H)
            )
        collision_surface.blit(loaded, (0, 0))
    else:
        old_file = legacy_filename(scene)
        if scene == "shrine":
            walkable = DEFAULT_PATHS
        elif scene == "mystic_valley":
            walkable = [[
                [.03, .73], [.25, .73],
                [.46, .80], [.46, .98],
                [.03, .98]
            ]]
        else:
            # Broad initial path for the new forest; paint precise areas with F2.
            walkable = [[
                [.03, .94], [.13, .76], [.27, .72], [.42, .69],
                [.52, .60], [.64, .61], [.73, .72], [.86, .79],
                [.98, .85], [.98, 1.0], [.03, 1.0]
            ]]
        blocked = []
        if old_file.exists():
            try:
                data = json.loads(
                    old_file.read_text(encoding="utf-8")
                )
                if isinstance(data, dict):
                    walkable = data.get(
                        "walkable",
                        data.get("paths", walkable)
                    )
                    blocked = data.get("blocked", [])
                elif isinstance(data, list):
                    walkable = data
            except (OSError, ValueError) as error:
                print("Collision import error:", error)
        for poly in walkable:
            if len(poly) >= 3:
                pygame.draw.polygon(
                    collision_surface,
                    (255, 255, 255, 255),
                    polygon_points(poly)
                )
        for poly in blocked:
            if len(poly) >= 3:
                pygame.draw.polygon(
                    collision_surface,
                    (0, 0, 0, 0),
                    polygon_points(poly)
                )
    update_collision_mask()
    print("Loaded collision:", scene)
def save_collision():
    filename = mask_filename(scene_manager.scene)
    try:
        filename.parent.mkdir(
            parents=True, exist_ok=True
        )
        pygame.image.save(
            collision_surface, str(filename)
        )
        if not filename.is_file():
            raise OSError("Saved file was not created")
        print("PATH SAVED:", filename)
        return True
    except Exception as error:
        print("PATH SAVE FAILED:", error)
        return False
def can_walk(x, y):
    ix, iy = int(x), int(y)
    if not (0 <= ix < WORLD_W and 0 <= iy < WORLD_H):
        return False
    return bool(collision_mask.get_at((ix, iy)))
load_collision(scene_manager.scene)
guardian_horror = GuardianHorror(forest_guardian, can_walk=can_walk)
# ============================================================
# PATH EDITOR
# ============================================================
editing = False
show_paths = False
edit_mode = "draw"
editor_camera = pygame.Vector2(0, 0)
draft = []
BRUSH_RADIUS = 22
save_message = ""
save_message_until = 0.0
collision_dirty = False
def save_editor():
    global save_message, save_message_until, collision_dirty
    success = save_collision()
    if success:
        save_message = "PATH SAVED SUCCESSFULLY"
        collision_dirty = False
    else:
        save_message = "SAVE FAILED - CHECK TERMINAL"
    save_message_until = pygame.time.get_ticks() / 1000 + 3
def screen_to_world(pos, camera):
    return pygame.Vector2(
        pos[0] + camera.x,
        pos[1] + camera.y
    )
def paint_stroke(start, end, mode):
    global collision_dirty
    start = pygame.Vector2(start)
    end = pygame.Vector2(end)
    distance = start.distance_to(end)
    spacing = max(2, BRUSH_RADIUS // 3)
    steps = max(1, math.ceil(distance / spacing))
    if mode == "draw":
        color = (255, 255, 255, 255)
    elif mode == "erase":
        color = (0, 0, 0, 0)
    else:
        return
    for i in range(steps + 1):
        point = start.lerp(end, i / steps)
        pygame.draw.circle(
            collision_surface,
            color,
            (round(point.x), round(point.y)),
            BRUSH_RADIUS
        )
    update_collision_mask()
    collision_dirty = True
def finish_polygon():
    global collision_dirty
    if len(draft) >= 3 and edit_mode == "block":
        pygame.draw.polygon(
            collision_surface,
            (0, 0, 0, 0),
            draft
        )
        update_collision_mask()
        collision_dirty = True
    draft.clear()
def clear_all_paths():
    global collision_dirty
    collision_surface.fill((0, 0, 0, 0))
    update_collision_mask()
    draft.clear()
    collision_dirty = True
def draw_editor(camera):
    visible = pygame.Surface(
        (SCREEN_W, SCREEN_H),
        pygame.SRCALPHA
    )
    visible.blit(
        collision_surface,
        (-round(camera.x), -round(camera.y))
    )
    visible.fill(
        (45, 220, 95, 115),
        special_flags=pygame.BLEND_RGBA_MULT
    )
    screen.blit(visible, (0, 0))
    points = [
        (
            round(p[0] - camera.x),
            round(p[1] - camera.y)
        )
        for p in draft
    ]
    if len(points) >= 2:
        pygame.draw.lines(
            screen, (255, 220, 80), False, points, 3
        )
    for point in points:
        pygame.draw.circle(
            screen, (255, 220, 80), point, 5
        )
    if edit_mode in ("draw", "erase"):
        cursor_color = (
            (70, 255, 120)
            if edit_mode == "draw"
            else (255, 90, 90)
        )
        pygame.draw.circle(
            screen,
            cursor_color,
            pygame.mouse.get_pos(),
            BRUSH_RADIUS,
            2
        )
    panel = pygame.Surface(
        (SCREEN_W, 58),
        pygame.SRCALPHA
    )
    panel.fill((12, 12, 22, 225))
    screen.blit(panel, (0, SCREEN_H - 58))
    mode_text = {
        "draw": "DRAW - LEFT DRAG TO ADD GROUND",
        "erase": "ERASE - LEFT DRAG TO REMOVE GROUND",
        "block": "BLOCK - CLICK POINTS, ENTER TO FINISH"
    }
    text = (
        f"{mode_text[edit_mode]} | "
        "N Draw | E Erase | B Block | "
        "[ ] Brush | F5 Save | F2 Save & Close"
    )
    label = small_font.render(
        text, True, (255, 235, 165)
    )
    screen.blit(label, (12, SCREEN_H - 37))
# ============================================================
# CAMERA
# ============================================================
def get_camera():
    return pygame.Vector2(
        max(
            0,
            min(
                max(0, WORLD_W - SCREEN_W),
                player.position.x - SCREEN_W / 2
            )
        ),
        max(
            0,
            min(
                max(0, WORLD_H - SCREEN_H),
                player.position.y - SCREEN_H / 2
            )
        )
    )
# ============================================================
# ENVIRONMENT
# ============================================================
environment = ShrineEnvironment(
    (WORLD_W, WORLD_H),
    (SCREEN_W, SCREEN_H)
)
effects_enabled = True
# ============================================================
# WIZARD AI CHAT
# ============================================================
wizard_ai = WizardAI()
chat_open = False
chat_input = ""
chat_messages = []
def wizard_observations():
    distance = player.position.distance_to(
        wizard.position
    )
    return {
        "scene": scene_manager.scene,
        "wizard_position": (
            f"{int(wizard.position.x)}, "
            f"{int(wizard.position.y)}"
        ),
        "warlock_position": (
            f"{int(player.position.x)}, "
            f"{int(player.position.y)}"
        ),
        "distance_to_warlock": round(distance),
        "warlock_nearby": distance < 140,
        "wizard_action": wizard.action,
        "wizard_facing": wizard.facing,
        "warlock_action": player.action,
        "rain": environment.rain,
        "fog": environment.fog,
        "clouds": environment.clouds,
        "torches": environment.torches,
        "fireflies": environment.fireflies,
        "effects_enabled": effects_enabled,
        "shrine_master_nearby": (
            wizard.position.distance_to(
                shrine_master.position
            ) < 250
        ),
        "portal_transition_active": (
            scene_manager.cinematic
        ),
        "portal_destination": "Mystic Valley"
    }
def draw_wizard_chat():
    px, py = 60, 55
    pw, ph = SCREEN_W - 120, SCREEN_H - 110
    panel = pygame.Surface(
        (pw, ph),
        pygame.SRCALPHA
    )
    panel.fill((12, 10, 24, 240))
    screen.blit(panel, (px, py))
    pygame.draw.rect(
        screen,
        (155, 105, 205),
        (px, py, pw, ph),
        2,
        border_radius=12
    )
    title = font.render(
        "VAEL - THE ANCIENT WIZARD",
        True,
        (225, 175, 255)
    )
    screen.blit(title, (px + 24, py + 18))
    hint = small_font.render(
        "Type a message | ENTER Send | ESC Close",
        True,
        (175, 165, 195)
    )
    screen.blit(hint, (px + 24, py + 55))
    lines = []
    for role, message in chat_messages[-12:]:
        prefix = "YOU: " if role == "you" else "VAEL: "
        wrapped = textwrap.wrap(
            prefix + message,
            width=85
        ) or [""]
        for line in wrapped:
            lines.append((role, line))
        lines.append(("", ""))
    if wizard_ai.pending:
        lines.append(("wizard", "VAEL: Thinking..."))
    lines = lines[-19:]
    y = py + 105
    for role, line in lines:
        color = (
            (255, 220, 170)
            if role == "you"
            else (205, 190, 255)
        )
        rendered = small_font.render(
            line, True, color
        )
        screen.blit(
            rendered,
            (px + 25, y)
        )
        y += 22
    input_rect = pygame.Rect(
        px + 20,
        py + ph - 65,
        pw - 40,
        43
    )
    pygame.draw.rect(
        screen,
        (33, 27, 49),
        input_rect,
        border_radius=7
    )
    pygame.draw.rect(
        screen,
        (125, 91, 160),
        input_rect,
        2,
        border_radius=7
    )
    input_text = small_font.render(
        "> " + chat_input[-100:] + "_",
        True,
        (255, 255, 255)
    )
    screen.blit(
        input_text,
        (input_rect.x + 12, input_rect.y + 12)
    )
# ============================================================
# DIALOGUE
# ============================================================
def draw_dialogue(message):
    box = pygame.Rect(
        100,
        SCREEN_H - 120,
        SCREEN_W - 200,
        94
    )
    pygame.draw.rect(
        screen,
        (20, 17, 29),
        box,
        border_radius=10
    )
    pygame.draw.rect(
        screen,
        (146, 101, 131),
        box,
        2,
        border_radius=10
    )
    label = font.render(
        message,
        True,
        (255, 220, 175)
    )
    screen.blit(
        label,
        (box.x + 22, box.y + 32)
    )
# ============================================================
# WIZARD AI MOVEMENT
# ============================================================
wizard_home = wizard.position.copy()
wizard_target = wizard.position.copy()
wizard_wait = 2.0
wizard_talk_until = 0.0
wizard_dialogue_index = 0
wizard_lines = [
    "Wizard: The moon remembers forgotten spells.",
    "Wizard: Strange magic flows beneath this village.",
    "Wizard: Even shadows have stories to tell.",
    "Wizard: Beware the ruins beyond the forest."
]
def update_wizard(dt, elapsed):
    global wizard_wait, wizard_target
    if (
        scene_manager.scene != "shrine"
        or scene_manager.cinematic
    ):
        wizard.set_animation("idle")
        wizard.update(dt)
        return
    if chat_open or elapsed < wizard_talk_until:
        wizard.set_animation("idle")
        wizard.update(dt)
        return
    delta = wizard_target - wizard.position
    distance = delta.length()
    if distance < 5:
        wizard_wait -= dt
        wizard.set_animation("idle")
        if wizard_wait <= 0:
            wizard_wait = rng.uniform(1.5, 4.0)
            for _ in range(25):
                angle = rng.uniform(0, math.tau)
                radius = rng.uniform(15, 105)
                candidate = (
                    wizard_home
                    + pygame.Vector2(
                        math.cos(angle),
                        math.sin(angle)
                    ) * radius
                )
                if can_walk(candidate.x, candidate.y):
                    wizard_target = candidate
                    break
    else:
        direction = delta / distance
        if abs(direction.x) > abs(direction.y):
            facing = (
                "right" if direction.x > 0 else "left"
            )
        else:
            facing = (
                "down" if direction.y > 0 else "up"
            )
        step = direction * min(
            distance, 48 * dt
        )
        candidate = wizard.position + step
        if can_walk(candidate.x, candidate.y):
            wizard.position = candidate
            wizard.set_animation("walk", facing)
        else:
            wizard_target = wizard.position.copy()
            wizard_wait = 2.0
            wizard.set_animation("idle")
    wizard.update(dt)
def update_forest_guardian(dt):
    global forest_guardian_target, forest_guardian_wait
    if scene_manager.scene != "haunted_forest" or scene_manager.cinematic:
        forest_guardian.set_animation("idle")
        forest_guardian.update(dt)
        return
    guardian_horror.update(dt, player.position)
    if guardian_horror.busy:
        forest_guardian.update(dt)
        return
    if forest_guardian.position.distance_to(player.position) < 175:
        forest_guardian.face_point(player.position)
        forest_guardian.update(dt)
        return
    delta = forest_guardian_target - forest_guardian.position
    if delta.length() < 6:
        forest_guardian.set_animation("idle")
        forest_guardian_wait -= dt
        if forest_guardian_wait <= 0:
            forest_guardian_wait = rng.uniform(1.2, 3.5)
            for _ in range(25):
                candidate = forest_guardian_home + pygame.Vector2(
                    rng.uniform(-90, 90), rng.uniform(-35, 35))
                if can_walk(candidate.x, candidate.y):
                    forest_guardian_target = candidate
                    break
    else:
        step = delta.normalize() * min(delta.length(), 32 * dt)
        candidate = forest_guardian.position + step
        if can_walk(candidate.x, candidate.y):
            forest_guardian.position = candidate
            facing = ('right' if delta.x > 0 else 'left') if abs(delta.x) > abs(delta.y) else ('down' if delta.y > 0 else 'up')
            forest_guardian.set_animation('walk', facing)
        else:
            forest_guardian_target = forest_guardian.position.copy()
            forest_guardian_wait = 2.0
    forest_guardian.update(dt)


# ============================================================
# DEBUGGER
# ============================================================
debug_enabled = False
debug_paused = False
debug_character = player
debug_direction = "left"
debug_action = "walk"
debug_frame = 0
debug_time = 0.0
debug_speed = 4.0
def debug_frames():
    return debug_character.animations[
        f"{debug_action}_{debug_direction}"
    ]
def draw_debugger(dt):
    global debug_frame, debug_time
    layer = pygame.Surface(
        (SCREEN_W, SCREEN_H),
        pygame.SRCALPHA
    )
    layer.fill((8, 9, 15, 238))
    screen.blit(layer, (0, 0))
    frames = debug_frames()
    if not debug_paused:
        debug_time += dt
        debug_frame = (
            int(debug_time * debug_speed)
            % len(frames)
        )
    if debug_character is player:
        name = "WARLOCK"
    elif debug_character is wizard:
        name = "WIZARD"
    else:
        name = "SHRINE MASTER"
    title = font.render(
        name + " ANIMATION INSPECTOR",
        True,
        (255, 220, 170)
    )
    screen.blit(
        title,
        (
            SCREEN_W // 2 - title.get_width() // 2,
            35
        )
    )
    big = pygame.transform.smoothscale(
        frames[debug_frame],
        (300, 315)
    )
    screen.blit(
        big,
        big.get_rect(
            midbottom=(SCREEN_W // 2, 480)
        )
    )
    tw, th, gap = 95, 100, 20
    start = (
        SCREEN_W
        - (
            len(frames) * tw
            + (len(frames) - 1) * gap
        )
    ) // 2
    for i, frame in enumerate(frames):
        x = start + i * (tw + gap)
        y = 505
        scaled = pygame.transform.smoothscale(
            frame, (tw, th)
        )
        screen.blit(scaled, (x, y))
        color = (
            (255, 200, 85)
            if i == debug_frame
            else (90, 90, 110)
        )
        pygame.draw.rect(
            screen,
            color,
            (x, y, tw, th),
            2
        )
    status = (
        f"{debug_direction.upper()} / "
        f"{debug_action.upper()} | "
        f"Frame {debug_frame + 1}/{len(frames)} | "
        f"{debug_speed:.1f} FPS | "
        f"{'PAUSED' if debug_paused else 'PLAYING'}"
    )
    label = small_font.render(
        status, True, (245, 220, 180)
    )
    screen.blit(
        label,
        (
            SCREEN_W // 2 - label.get_width() // 2,
            635
        )
    )
    controls = tiny_font.render(
        "F3 Close | TAB Character | Arrows Direction | "
        "1 Idle 2 Walk 3 Run | SPACE Pause | , . Step",
        True,
        (200, 205, 220)
    )
    screen.blit(
        controls,
        (
            SCREEN_W // 2 - controls.get_width() // 2,
            672
        )
    )
# ============================================================
# MAIN GAME LOOP
# ============================================================
elapsed = 0.0
running = True
print(
    "Bloodmoon Shrine: WASD move, Shift run, E talk, "
    "F2 editor, F5 save, F3 debugger"
)
while running:
    dt = min(clock.tick(FPS) / 1000, 0.05)
    elapsed += dt
    camera = (
        editor_camera.copy()
        if editing
        else get_camera()
    )
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            if editing and collision_dirty:
                save_editor()
            running = False
        elif event.type == pygame.TEXTINPUT and chat_open:
            chat_input = (
                chat_input + event.text
            )[:250]
        elif event.type == pygame.KEYDOWN:
            k = event.key
            if portal_choice_open:
                if k in (pygame.K_1, pygame.K_KP1):
                    portal_choice_open = False
                    scene_manager.start_shrine_portal('mystic_valley')
                elif k in (pygame.K_2, pygame.K_KP2):
                    portal_choice_open = False
                    scene_manager.start_shrine_portal('haunted_forest')
                elif k == pygame.K_ESCAPE:
                    portal_choice_open = False
                continue

            # =================================================
            # WIZARD CHAT KEYBOARD INPUT
            # =================================================
            if chat_open:
                if k == pygame.K_ESCAPE:
                    chat_open = False
                elif k == pygame.K_RETURN:
                    message = chat_input.strip()
                    if message and not wizard_ai.pending:
                        accepted = wizard_ai.ask(
                            message,
                            wizard_observations()
                        )
                        if accepted:
                            chat_messages.append(
                                ("you", message)
                            )
                            chat_input = ""
                elif k == pygame.K_BACKSPACE:
                    chat_input = chat_input[:-1]
                continue
            # Haunted Forest animation test keys (not active in editor or debugger).
            if scene_manager.scene == "haunted_forest" and not editing and not debug_enabled:
                horror_keys = {
                    pygame.K_1: "teleport", pygame.K_2: "charge",
                    pygame.K_3: "grow", pygame.K_4: "jumpscare",
                    pygame.K_5: "vanish", pygame.K_6: "stalk",
                }
                if k in horror_keys:
                    guardian_horror.trigger(horror_keys[k], player.position)
                    continue
            # =================================================
            # NORMAL GAME KEYS
            # =================================================
            if k == pygame.K_ESCAPE:
                if editing and collision_dirty:
                    save_editor()
                running = False
            elif k == pygame.K_F3:
                debug_enabled = not debug_enabled
                debug_time = 0
                debug_frame = 0
            elif debug_enabled:
                if k == pygame.K_TAB:
                    if debug_character is player:
                        debug_character = wizard
                    elif debug_character is wizard:
                        debug_character = shrine_master
                    else:
                        debug_character = player
                    debug_time = 0
                    debug_frame = 0
                elif k == pygame.K_SPACE:
                    debug_paused = not debug_paused
                elif k in (
                    pygame.K_LEFT,
                    pygame.K_RIGHT,
                    pygame.K_UP,
                    pygame.K_DOWN
                ):
                    debug_direction = {
                        pygame.K_LEFT: "left",
                        pygame.K_RIGHT: "right",
                        pygame.K_UP: "up",
                        pygame.K_DOWN: "down"
                    }[k]
                    debug_time = 0
                    debug_frame = 0
                elif k in (
                    pygame.K_1,
                    pygame.K_2,
                    pygame.K_3
                ):
                    debug_action = {
                        pygame.K_1: "idle",
                        pygame.K_2: "walk",
                        pygame.K_3: "run"
                    }[k]
                    debug_time = 0
                    debug_frame = 0
                elif k == pygame.K_COMMA:
                    debug_paused = True
                    debug_frame = (
                        debug_frame - 1
                    ) % len(debug_frames())
                elif k == pygame.K_PERIOD:
                    debug_paused = True
                    debug_frame = (
                        debug_frame + 1
                    ) % len(debug_frames())
                elif k in (
                    pygame.K_MINUS,
                    pygame.K_KP_MINUS
                ):
                    debug_speed = max(
                        0.5, debug_speed - 0.5
                    )
                elif k in (
                    pygame.K_EQUALS,
                    pygame.K_PLUS,
                    pygame.K_KP_PLUS
                ):
                    debug_speed = min(
                        30, debug_speed + 0.5
                    )
            # =================================================
            # SAVE ANYTIME
            # =================================================
            elif k == pygame.K_F5:
                save_editor()
            elif (
                k == pygame.K_s
                and event.mod & pygame.KMOD_CTRL
            ):
                save_editor()
            # =================================================
            # OPEN / CLOSE PATH EDITOR
            # =================================================
            elif k == pygame.K_F2:
                if editing:
                    save_editor()
                editing = not editing
                show_paths = editing
                draft.clear()
                if editing:
                    editor_camera = get_camera()
            # =================================================
            # PATH EDITOR CONTROLS
            # =================================================
            elif editing:
                if k == pygame.K_n:
                    edit_mode = "draw"
                    draft.clear()
                elif k == pygame.K_e:
                    edit_mode = "erase"
                    draft.clear()
                elif k == pygame.K_b:
                    edit_mode = "block"
                    draft.clear()
                elif k == pygame.K_LEFTBRACKET:
                    BRUSH_RADIUS = max(
                        3, BRUSH_RADIUS - 5
                    )
                elif k == pygame.K_RIGHTBRACKET:
                    BRUSH_RADIUS = min(
                        150, BRUSH_RADIUS + 5
                    )
                elif k == pygame.K_RETURN:
                    finish_polygon()
                elif k == pygame.K_BACKSPACE:
                    if draft:
                        draft.pop()
                elif k == pygame.K_x:
                    clear_all_paths()
            # =================================================
            # GAME CONTROLS
            # =================================================
            elif k == pygame.K_TAB:
                show_paths = not show_paths
            elif k == pygame.K_r:
                environment.rain = not environment.rain
            elif k == pygame.K_g:
                effects_enabled = not effects_enabled
            elif k == pygame.K_f:
                environment.fog = not environment.fog
            elif k == pygame.K_c:
                environment.clouds = not environment.clouds
            elif k == pygame.K_l:
                environment.torches = not environment.torches
            elif k == pygame.K_v:
                environment.fireflies = (
                    not environment.fireflies
                )
            elif (
                k == pygame.K_e
                and not scene_manager.cinematic
            ):
                if scene_manager.scene in ("mystic_valley", "haunted_forest"):
                    return_portal = (scene_manager.valley_portal
                                     if scene_manager.scene == "mystic_valley"
                                     else scene_manager.forest_portal)
                    distance = player.position.distance_to(return_portal)
                    if distance < 145:
                        scene_manager.start_return()
                else:
                    dw = player.position.distance_to(
                        wizard.position
                    )
                    dm = player.position.distance_to(
                        shrine_master.position
                    )
                    if dw < 105 and dw <= dm:
                        chat_open = True
                        chat_input = ""
                        wizard.face_point(player.position)
                        wizard_talk_until = elapsed + 3600
                        if not chat_messages:
                            chat_messages.append((
                                "wizard",
                                "Ah, Warlock. What brings you to me?"
                            ))
                    elif dm < 110:
                        shrine_master.face_point(
                            player.position
                        )
                        portal_choice_open = True
        # =====================================================
        # MOUSE DRAW / ERASE / BLOCK
        # =====================================================
        elif (
            editing
            and not debug_enabled
            and event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
        ):
            position = screen_to_world(
                event.pos, editor_camera
            )
            if edit_mode in ("draw", "erase"):
                paint_stroke(
                    position, position, edit_mode
                )
            elif edit_mode == "block":
                draft.append(
                    (round(position.x), round(position.y))
                )
        elif (
            editing
            and not debug_enabled
            and event.type == pygame.MOUSEMOTION
            and event.buttons[0]
            and edit_mode in ("draw", "erase")
        ):
            current = screen_to_world(
                event.pos, editor_camera
            )
            previous = screen_to_world(
                (
                    event.pos[0] - event.rel[0],
                    event.pos[1] - event.rel[1]
                ),
                editor_camera
            )
            paint_stroke(
                previous, current, edit_mode
            )
    if not running:
        break
    keys = pygame.key.get_pressed()
    # ========================================================
    # PLAYER MOVEMENT
    # ========================================================
    move = pygame.Vector2(0, 0)
    if (
        not editing
        and not debug_enabled
        and not chat_open
        and not portal_choice_open
        and not scene_manager.cinematic
    ):
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            move.x -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            move.x += 1
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            move.y -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            move.y += 1
    if move.length_squared():
        move.normalize_ip()
        if abs(move.x) > abs(move.y):
            facing = (
                "right" if move.x > 0 else "left"
            )
        else:
            facing = (
                "down" if move.y > 0 else "up"
            )
        sprint = (
            keys[pygame.K_LSHIFT]
            or keys[pygame.K_RSHIFT]
        )
        speed = 250 if sprint else 145
        step = move * speed * dt
        moved = False
        if can_walk(
            player.position.x + step.x,
            player.position.y
        ):
            player.position.x += step.x
            moved = True
        if can_walk(
            player.position.x,
            player.position.y + step.y
        ):
            player.position.y += step.y
            moved = True
        player.set_animation(
            (
                "run" if sprint else "walk"
            ) if moved else "idle",
            facing
        )
    else:
        player.set_animation("idle")
    player.update(dt)
    # ========================================================
    # SCENE TRANSITIONS
    # ========================================================
    scene_manager.update(dt, player)
    if scene_manager.destination_changed:
        if editing and collision_dirty:
            save_editor()
        load_collision(scene_manager.scene)
        collision_dirty = False
        editing = False
        show_paths = False
        draft.clear()
        chat_open = False
    update_wizard(dt, elapsed)
    update_forest_guardian(dt)
    forest_director.update(
        dt, player.position, forest_guardian.position,
        scene_manager.scene == "haunted_forest",
        paused=editing or scene_manager.cinematic or chat_open
    )
    if scene_manager.scene == "haunted_forest" and not (editing or scene_manager.cinematic or chat_open):
        if forest_director.guardian_commands and not guardian_horror.busy and guardian_horror.cooldown <= 0:
            guardian_horror.trigger(forest_director.guardian_commands.pop(0), player.position)
    shrine_master.set_animation("idle")
    shrine_master.update(dt)
    environment.update(dt)
    # ========================================================
    # COLLECT AI RESPONSE
    # ========================================================
    ai_result = wizard_ai.poll()
    if ai_result is not None:
        status, answer = ai_result
        chat_messages.append(("wizard", answer))
    # ========================================================
    # EDITOR CAMERA
    # ========================================================
    camera = get_camera()
    if editing:
        pan = pygame.Vector2(
            int(
                keys[pygame.K_RIGHT]
                or keys[pygame.K_d]
            ) - int(
                keys[pygame.K_LEFT]
                or keys[pygame.K_a]
            ),
            int(
                keys[pygame.K_DOWN]
                or keys[pygame.K_s]
            ) - int(
                keys[pygame.K_UP]
                or keys[pygame.K_w]
            )
        )
        if pan.length_squared():
            pan.normalize_ip()
            editor_camera += pan * 550 * dt
        editor_camera.x = max(
            0,
            min(
                max(0, WORLD_W - SCREEN_W),
                editor_camera.x
            )
        )
        editor_camera.y = max(
            0,
            min(
                max(0, WORLD_H - SCREEN_H),
                editor_camera.y
            )
        )
        camera = editor_camera.copy()
    # ========================================================
    # RENDER
    # ========================================================
    screen.blit(
        scene_manager.background,
        (-round(camera.x), -round(camera.y))
    )
    if (
        effects_enabled
        and scene_manager.scene == "shrine"
    ):
        environment.draw_background(screen, camera)
    if scene_manager.scene == "shrine":
        visible_characters = (
            player, wizard, shrine_master
        )
    elif scene_manager.scene == "haunted_forest":
        visible_characters = (player, forest_guardian)
    else:
        visible_characters = (player,)
    for character in sorted(
        visible_characters,
        key=lambda c: c.position.y
    ):
        if character is forest_guardian:
            guardian_horror.draw(screen, camera)
        else:
            character.draw(screen, camera)
    if (
        effects_enabled
        and scene_manager.scene == "shrine"
    ):
        environment.draw_world_lights(screen, camera)
        environment.draw_foreground(screen, camera)
    scene_manager.draw_portal(screen, camera)
    # Guardian-directed atmosphere and floating spirits.
    # Screen-space effects are rendered before editor and HUD.
    forest_director.draw(screen, camera, player.position)
    if scene_manager.scene == "haunted_forest":
        guardian_horror.draw_flash(screen)
    if editing or show_paths:
        draw_editor(camera)
    # ========================================================
    # HUD
    # ========================================================
    scene_manager.draw_hud(
        screen, font, small_font, player, wizard,
        clock.get_fps(), detailed=editing
    )
    dw = player.position.distance_to(wizard.position)
    dm = player.position.distance_to(shrine_master.position)
    if (
        scene_manager.scene == "shrine"
        and not scene_manager.cinematic
    ):
        if dw < 105:
            label = small_font.render(
                "E - Talk to Wizard",
                True,
                (255, 220, 170)
            )
            screen.blit(
                label,
                (
                    round(
                        wizard.position.x
                        - camera.x
                        - label.get_width() / 2
                    ),
                    round(
                        wizard.position.y
                        - camera.y
                        - wizard.size[1] - 20
                    )
                )
            )
        elif dm < 110:
            label = small_font.render(
                "E - Speak to Shrine Master",
                True,
                (255, 220, 170)
            )
            screen.blit(
                label,
                (
                    round(
                        shrine_master.position.x
                        - camera.x
                        - label.get_width() / 2
                    ),
                    round(
                        shrine_master.position.y
                        - camera.y
                        - shrine_master.size[1] - 20
                    )
                )
            )
    if (
        scene_manager.scene in ("mystic_valley", "haunted_forest")
        and not scene_manager.cinematic
        and player.position.distance_to(
            scene_manager.valley_portal if scene_manager.scene == "mystic_valley"
            else scene_manager.forest_portal
        ) < 145
    ):
        draw_dialogue(
            "E - Return through the portal to Bloodmoon Shrine"
        )
    # ========================================================
    # SAVE CONFIRMATION
    # ========================================================
    now = pygame.time.get_ticks() / 1000
    if now < save_message_until:
        color = (
            (110, 255, 150)
            if "SUCCESSFULLY" in save_message
            else (255, 110, 110)
        )
        confirmation = font.render(
            save_message,
            True,
            color
        )
        screen.blit(
            confirmation,
            (
                SCREEN_W // 2
                - confirmation.get_width() // 2,
                180
            )
        )
    if debug_enabled:
        draw_debugger(dt)
    # AI chat renders over the game, but below transitions.
    if chat_open:
        draw_wizard_chat()
    if portal_choice_open:
        veil = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        veil.fill((9, 5, 17, 190))
        screen.blit(veil, (0, 0))
        box = pygame.Rect(SCREEN_W // 2 - 350, SCREEN_H // 2 - 115, 700, 230)
        pygame.draw.rect(screen, (24, 16, 36), box, border_radius=14)
        pygame.draw.rect(screen, (170, 110, 220), box, 2, border_radius=14)
        lines = [
            'SHRINE MASTER - CHOOSE A DESTINATION',
            '1  -  Mystic Valley',
            '2  -  Haunted Forest (Forest Guardian)',
            'ESC  -  Cancel'
        ]
        for i, line in enumerate(lines):
            txt = (font if i == 0 else small_font).render(line, True, (240, 214, 190))
            screen.blit(txt, (box.x + 30, box.y + 24 + i * 47))

    scene_manager.draw_transition(screen, font)
    pygame.display.flip()
pygame.quit()

