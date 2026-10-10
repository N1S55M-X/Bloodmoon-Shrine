 <p align="center">
  <img src="https://github.com/user-attachments/assets/6b3d80f8-ba54-41c5-aab6-9628f928da65" alt="Bloodmoon Shrine" width="550">
</p>

### An AI-Powered Dark Fantasy RPG

**Bloodmoon Shrine** is an open-source, experimental dark fantasy role-playing game developed using **Python, pygame-ce, local Qwen3 AI, and computer vision-based sprite automation**.

Explore mysterious shrines, haunted forests, and mystical valleys. Encounter ancient wizards, supernatural guardians, and characters capable of responding dynamically through artificial intelligence.

The project combines **AI-driven character interactions, autonomous world events, automated sprite segmentation, and richly illustrated fantasy environments**.

The central idea:

**What if fantasy game worlds could react, remember, and evolve instead of following only predefined scripts?**

---

## 🎮 Gameplay Screenshots

### 🏰 Bloodmoon Shrine

A gothic sanctuary filled with ancient magic, mysterious characters, and hidden pathways.

<img width="1367" height="877" alt="Bloodmoon Shrine gameplay" src="https://github.com/user-attachments/assets/cce5caf0-2a0e-4168-a2e6-8f6f7edbaa2c" />

### 🌲 Haunted Forest

A supernatural forest inhabited by an ancient guardian, magical portals, and mysterious environmental phenomena.

<img width="1362" height="875" alt="Haunted Forest gameplay" src="https://github.com/user-attachments/assets/6fa049d4-ec24-4f3a-8420-a5bca5bf8fd8" />

### 🧙 AI-Powered Wizard Dialogue

Speak with Vael, an ancient wizard powered by a locally running language model.

Unlike conventional NPCs with fixed dialogue trees, Vael generates responses dynamically.

<img width="1371" height="887" alt="Vael AI dialogue" src="https://github.com/user-attachments/assets/11bde409-5e4b-4c26-9cdf-682310a9db62" />

### 🏔️ Mystic Valley

Explore a mountainous fantasy environment with ancient ruins, waterfalls, and magical pathways.

<img width="1365" height="862" alt="Mystic Valley gameplay" src="https://github.com/user-attachments/assets/ccbe6816-3e14-47ac-90a2-e435382acb5a" />

---

## ✨ Features

### 🧠 Local AI-Powered Characters

- AI-driven conversations using Qwen3.
- Local inference through `llama-cpp-python`.
- Dynamic dialogue instead of exclusively predefined responses.
- NPC conversation memory.
- Experimental AI-directed environmental events.
- Local AI inference without requiring a paid cloud API.

### 👹 Supernatural Guardian

The Haunted Forest contains an animated guardian with supernatural abilities:

- Teleportation
- Charging toward the player
- Giant transformations
- Jumpscare sequences
- Vanishing and reappearing
- Stalking behavior

These actions are supported by the experimental Guardian Horror controller and can be selected through the AI World Director.

### 🌍 Explorable Fantasy Environments

Three environments are currently implemented:

1. **Bloodmoon Shrine** — The starting sanctuary.
2. **Mystic Valley** — A mountainous landscape with ancient ruins.
3. **Haunted Forest** — A supernatural forest inhabited by an ancient guardian.

### 🌫️ Dynamic Atmosphere

- Fog and atmospheric effects.
- Magical lighting overlays.
- Animated character sprites.
- Smoke and supernatural visual effects.
- Environmental event generation.
- Magical portals and scene transitions.

### 🗺️ Custom Path and Collision System

The game includes a path-editing system for defining walkable areas across illustrated environments.

This allows detailed fantasy backgrounds to become explorable game worlds without requiring fully modeled 3D environments.

---

## 🤖 AI-Powered Sprite Segmentation and Animation Automation

One of the project's major technical components is an **automated sprite-processing pipeline** designed to transform AI-generated character artwork into usable game sprites.

AI-generated sprite sheets often contain inconsistent spacing, overlapping poses, background artifacts, and character details that are difficult to extract manually.

Bloodmoon Shrine explores the use of **computer vision, SAM 2.1 segmentation, and automated image processing** to simplify this workflow.

### How the Pipeline Works

```text
AI-Generated Character Artwork
              |
              v
Computer Vision / SAM 2.1
              |
              v
Character Segmentation
              |
              v
Individual Sprite Extraction
              |
              v
Background Removal and Cleanup
              |
              v
Frame Alignment and Normalization
              |
              v
Animation Atlas Generation
              |
              v
pygame-ce AnimatedCharacter
              |
              v
Animated Game Character
```

### Sprite Automation Features

- AI-assisted character segmentation.
- Extraction of individual sprites from generated artwork.
- Background removal and transparency processing.
- Sprite alignment and normalization.
- Animation atlas generation.
- Sprite inspection and diagnostic outputs.
- Integration with the game's character animation system.

The project includes several sprite-processing utilities:

| File | Purpose |
|---|---|
| `sprite_auto.py` | Sprite automation |
| `sprite_auto_v4.py` | Updated sprite automation pipeline |
| `sprite_processor.py` | Sprite processing utilities |
| `inspect_hero.py` | Character inspection and debugging |
| `sprite_auto_output/` | Generated atlases and previews |
| `sprite_diagnostics/` | Diagnostic outputs |

The SAM 2.1 model weights are not included in the repository and must be obtained separately if required by the sprite-processing workflow.

### ML-Aware Character Design

The project also explores generating artwork specifically for machine-learning-based sprite extraction.

Characters are designed with clear silhouettes, consistent proportions, and sufficient separation between poses to improve segmentation quality.

This reduces manual cleanup and helps maintain consistent animation assets.

### Long-Term Goal

The goal is to create a reusable pipeline capable of converting newly generated fantasy characters into game-ready assets with minimal manual intervention.

**Character Concept → AI Artwork → Segmentation → Animation Atlas → Game Entity**

Existing processing tools support parts of this workflow. Fully automatic character generation and game integration remain development goals.

---

## 🌌 Experimental AI World Director

Beyond character dialogue, Bloodmoon Shrine experiments with an AI system capable of selecting events and actions within the game world.

The World Director receives game context and selects from a predefined set of supported actions.

Examples include:

- Triggering supernatural Guardian behavior.
- Modifying atmospheric effects.
- Generating mysterious environmental messages.
- Initiating magical visual effects.
- Influencing the timing of horror encounters.

### Architecture

```text
Player and Environment State
             |
             v
      Qwen3 AI Director
             |
             v
       Action Selection
             |
             v
      Action Validation
             |
             v
       pygame-ce Engine
             |
             v
     Visible World Changes
```

The language model proposes supported actions while the game engine remains responsible for executing animations and updating the world.

This is an experimental system, not yet a complete autonomous-world simulation.

---

## 🎮 Controls

| Key | Action |
|---|---|
| W / A / S / D | Move |
| Shift | Run |
| E | Interact / Talk |
| Enter | Send dialogue |
| Escape | Close dialogue |
| F2 | Path editor |
| F3 | Debug mode |
| F5 | Save path edits |

---

## 🛠️ Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core programming language |
| pygame-ce | Game engine and rendering |
| Qwen3 | Local language model |
| llama-cpp-python | Local AI inference |
| SAM 2.1 | Computer vision-based segmentation |
| Image-processing utilities | Sprite extraction and atlas generation |
| JSON | Game configuration and NPC memory |
| AI-generated artwork | Fantasy environments and character assets |

---

## 🚀 Installation

### Requirements

- Python 3.12 recommended.
- Windows (current development platform).
- pygame-ce.
- llama-cpp-python.
- A compatible locally downloaded Qwen3 GGUF model for AI features.

Optional sprite-processing utilities may require additional dependencies and separately downloaded segmentation model weights.

### 1. Clone the Repository

```bash
git clone https://github.com/N1S55M-X/Bloodmoon-Shrine.git
cd Bloodmoon-Shrine
```

### 2. Install Core Dependencies

```bash
python -m pip install pygame-ce llama-cpp-python
```

Additional dependencies may be needed for sprite automation.

### 3. Configure the AI Model

Qwen3 model weights are not included in this repository because of their size.

Download a compatible GGUF model separately and configure its local path according to `npc_ai.py` and `world_ai.py`.

### 4. Start the Game

```bash
python game.py
```

**Note:** This is an experimental alpha release. Some features depend on local model configuration and may require additional setup.

---

## 🧩 Project Architecture

```text
Bloodmoon-Shrine/
│
├── game.py
├── characters.py
├── scene_manager.py
├── environment.py
│
├── npc_ai.py
├── world_ai.py
├── guardian_horror.py
│
├── sprite_auto.py
├── sprite_auto_v4.py
├── sprite_processor.py
├── inspect_hero.py
│
├── assets/
├── scenes/
├── sprite_auto_output/
│
└── README.md
```

### Core Systems

**Game Engine:** Handles movement, rendering, interaction, collision, and game updates.

**Scene Manager:** Controls environments, transitions, portals, and visual scaling.

**NPC AI:** Provides locally generated conversations through Qwen3.

**World AI:** Experiments with AI-directed environmental and supernatural events.

**Guardian Horror:** Executes supernatural Guardian animations and visual effects.

**Sprite Automation:** Uses computer vision and image processing to transform generated artwork into animation assets.

**Character System:** Loads processed sprite atlases and handles animation, movement, and character rendering.

---

## 🔮 Development Roadmap

### Phase 1 — Intelligent Horror Encounters

- Improved Guardian behavior.
- Player awareness and tracking.
- Context-sensitive jumpscares.
- Environmental reactions.
- Dynamic horror sequences.

### Phase 2 — Advanced Sprite Automation

- Improved automatic pose detection.
- Segmentation confidence checks.
- Automatic sprite alignment.
- Animation consistency validation.
- Batch character processing.
- Automatic animation atlas export.
- Streamlined integration of processed characters into the game.

### Phase 3 — Living Magical Entities

- Autonomous magical flames.
- Interactive supernatural objects.
- Individual entity states and memories.
- AI-directed magical interactions.

### Phase 4 — Autonomous Creatures

- Ghouls and spectral servants.
- Guardian-controlled creature groups.
- Coordinated movement and actions.
- Creature interactions and relationships.

### Phase 5 — Living Environments

- Animated trees and vegetation.
- Interactive roots and vines.
- Dynamic environmental obstacles.
- Magical environmental transformations.

### Phase 6 — AI-Directed World Generation

- Expandable fantasy asset library.
- AI-controlled object placement.
- Dynamic encounters and events.
- Persistent world changes.
- Automated asset-processing integration.

### Phase 7 — Emergent Fantasy Intelligence

The long-term vision is a persistent fantasy world where characters possess goals, memories, relationships, and the ability to influence their surroundings.

The proposed architecture is:

**Perception → Goals → Planning → Actions → Consequences → Memory**

The objective is to investigate how local AI agents, computer vision, asset automation, and traditional game systems can work together to produce believable, unpredictable fantasy experiences.

---

## ⚠️ Development Status

**Experimental Alpha — Active Development**

Bloodmoon Shrine is currently a research-oriented indie game prototype.

The game is playable locally, with implemented exploration, character rendering, collision, AI-powered dialogue, and experimental supernatural behavior systems.

The automated sprite-processing pipeline is under active development, and several planned autonomous-world systems are not yet implemented.

The project is not yet a complete RPG and does not currently provide a packaged Windows executable or browser-playable release.

---

## 🤝 Contributions

Contributions, suggestions, bug reports, and discussions are welcome.

Areas of interest include:

- Game AI and autonomous agents.
- Python game development.
- Computer vision and image segmentation.
- Automated sprite generation and animation.
- Procedural world interactions.
- NPC memory and behavior.
- Fantasy animation.
- Environmental simulation.
- Game optimization.

---

## 👨‍💻 Developer

**N1S55M-X**

GitHub: https://github.com/N1S55M-X

Project: https://github.com/N1S55M-X/Bloodmoon-Shrine

---

*Bloodmoon Shrine — A fantasy world that doesn't just tell stories, but learns to create them.*

<p align="center">
  <img src="https://github.com/user-attachments/assets/6b3d80f8-ba54-41c5-aab6-9628f928da65" alt="Bloodmoon Shrine Gothic Cathedral Valley" width="700">
</p>
