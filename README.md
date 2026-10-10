### An AI-Powered Dark Fantasy RPG

**Bloodmoon Shrine** is an open-source, experimental dark fantasy role-playing game developed using **Python, pygame-ce, and local Qwen3 AI**.

Explore mysterious shrines, haunted forests, and mystical valleys. Encounter ancient wizards, supernatural guardians, and characters capable of responding dynamically through artificial intelligence.

The project explores a central idea:

**What if fantasy game worlds could react, remember, and evolve instead of following only predefined scripts?**

---

## 🎮 Gameplay Screenshots

### 🏰 Bloodmoon Shrine

A gothic sanctuary filled with ancient magic, mysterious characters, and hidden pathways.
<img width="1367" height="877" alt="WhatsApp Image 2026-10-10 at 4 40 45 PM" src="https://github.com/user-attachments/assets/cce5caf0-2a0e-4168-a2e6-8f6f7edbaa2c" />


### 🌲 Haunted Forest
A supernatural forest inhabited by an ancient guardian, magical portals, and mysterious environmental phenomena.
<img width="1362" height="875" alt="WhatsApp Image 2026-10-10 at 4 41 24 PM" src="https://github.com/user-attachments/assets/6fa049d4-ec24-4f3a-8420-a5bca5bf8fd8" />

### 🧙 AI-Powered Wizard Dialogue

Speak with Vael, an ancient wizard powered by a locally running language model.

Unlike conventional NPCs with fixed dialogue trees, Vael generates responses dynamically.

<img width="1371" height="887" alt="WhatsApp Image 2026-10-10 at 4 43 44 PM" src="https://github.com/user-attachments/assets/11bde409-5e4b-4c26-9cdf-682310a9db62" />


### 🏔️ Mystic Valley

Explore a mountainous fantasy environment with ancient ruins, waterfalls, and magical pathways.
<img width="1365" height="862" alt="ChatGPT Image Oct 10, 2026, 05_11_20 PM" src="https://github.com/user-attachments/assets/ccbe6816-3e14-47ac-90a2-e435382acb5a" />


---

## ✨ Features

### 🧠 Local AI-Powered Characters

- AI-driven conversations using Qwen3.
- Local inference through `llama-cpp-python`.
- Dynamic dialogue rather than exclusively predefined responses.
- NPC conversation memory.
- Experimental AI-directed environmental events.

### 👹 Supernatural Guardian

The Haunted Forest contains an animated guardian with supernatural abilities:

- Teleportation
- Charging toward the player
- Giant transformations
- Jumpscare sequences
- Vanishing and reappearing
- Stalking behavior

The Guardian's supernatural actions can be triggered through the game's horror controller and selected by the experimental AI director.

### 🌍 Explorable Fantasy Environments

Three environments are currently implemented:

1. **Bloodmoon Shrine** — The starting sanctuary.
2. **Mystic Valley** — A mountainous landscape with ancient ruins.
3. **Haunted Forest** — A supernatural forest inhabited by an ancient guardian.

### 🌫️ Dynamic Atmosphere

- Fog and atmospheric effects
- Magical lighting overlays
- Animated character sprites
- Smoke and supernatural visual effects
- Environmental event generation
- Magical portals and scene transitions

### 🗺️ Custom Path and Collision System

The game includes a path-editing system for defining walkable areas across illustrated environments.

This allows detailed fantasy backgrounds to become explorable game worlds.

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
| JSON | Game configuration and NPC memory |
| AI-generated artwork | Fantasy environments and character assets |

---

## 🚀 Installation

### Requirements

- Python 3.12 recommended
- Windows (current development platform)
- pygame-ce
- llama-cpp-python
- A compatible locally downloaded Qwen3 GGUF model for AI features

### 1. Clone the repository

```bash
git clone https://github.com/N1S55M-X/Bloodmoon-Shrine.git
cd Bloodmoon-Shrine
```

### 2. Install dependencies

```bash
python -m pip install pygame-ce llama-cpp-python
```

Additional dependencies may be required for optional sprite-processing utilities.

### 3. Configure the AI model

The Qwen3 model weights are not included in this repository because of their size.

Download a compatible GGUF model separately and configure its local path according to `npc_ai.py` and `world_ai.py`.

### 4. Start the game

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
├── npc_ai.py
├── world_ai.py
├── guardian_horror.py
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

---

## 🔮 Development Roadmap

### Phase 1 — Intelligent Horror Encounters

- Improved Guardian behavior
- Player awareness and tracking
- Context-sensitive jumpscares
- Environmental reactions
- Dynamic horror sequences

### Phase 2 — Living Magical Entities

- Autonomous magical flames
- Interactive supernatural objects
- Individual entity states and memories
- AI-directed magical interactions

### Phase 3 — Autonomous Creatures

- Ghouls and spectral servants
- Guardian-controlled creature groups
- Coordinated movement and actions
- Creature interactions and relationships

### Phase 4 — Living Environments

- Animated trees and vegetation
- Interactive roots and vines
- Dynamic environmental obstacles
- Magical environmental transformations

### Phase 5 — AI-Directed World Generation

- Expandable fantasy asset library
- AI-controlled object placement
- Dynamic encounters and events
- Persistent world changes

### Phase 6 — Emergent Fantasy Intelligence

The long-term vision is a persistent fantasy world where characters possess goals, memories, relationships, and the ability to influence their surroundings.

The proposed architecture is:

**Perception → Goals → Planning → Actions → Consequences → Memory**

The objective is to investigate how local AI agents and traditional game systems can work together to produce believable, unpredictable fantasy experiences.

---

## ⚠️ Development Status

**Experimental Alpha — Active Development**

Bloodmoon Shrine is currently a research-oriented indie game prototype.

The game is playable locally, but several planned AI systems are experimental or not yet implemented.

The project is not yet a complete RPG and does not currently provide a packaged Windows executable or browser-playable release.

---

## 🤝 Contributions

Contributions, suggestions, bug reports, and discussions are welcome.

Areas of interest include:

- Game AI and autonomous agents
- Python game development
- Procedural world interactions
- NPC memory and behavior
- Fantasy animation
- Environmental simulation
- Game optimization

---

## 👨‍💻 Developer

**N1S55M-X**

GitHub: https://github.com/N1S55M-X

Project: https://github.com/N1S55M-X/Bloodmoon-Shrine

---

*Bloodmoon Shrine — A fantasy world that doesn't just tell stories, but learns to create them.*

<img width="1916" height="821" alt="Bloodmoon Shrine_ Gothic Cathedral Valley" src="https://github.com/user-attachments/assets/6b3d80f8-ba54-41c5-aab6-9628f928da65" />
