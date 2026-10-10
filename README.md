<p align="center">
  <img src="https://github.com/user-attachments/assets/6b3d80f8-ba54-41c5-aab6-9628f928da65" alt="Bloodmoon Shrine" width="550">
</p>

### An Experimental Dark Fantasy RPG Built with Python and Local AI

**Bloodmoon Shrine** is an open-source 2D dark fantasy RPG prototype developed using **Python, pygame-ce, and Qwen3**.

The project combines illustrated fantasy environments, animated characters, exploration, locally generated NPC dialogue, and experimental AI-directed environmental events.

It also includes a **computer vision-based sprite automation workflow** developed to simplify the process of converting AI-generated character artwork into usable game animations.

The project explores two practical applications of AI in game development: using language models for character interactions and using computer vision to automate repetitive asset-processing tasks.

---

## 🎮 Gameplay Screenshots

### 🏰 Bloodmoon Shrine

The starting area, containing the Warlock, Vael the Wizard, and the Shrine Master.

<img width="1367" height="877" alt="Bloodmoon Shrine gameplay" src="https://github.com/user-attachments/assets/cce5caf0-2a0e-4168-a2e6-8f6f7edbaa2c" />

### 🌲 Haunted Forest

A forest environment containing an animated Guardian, environmental effects, and a portal.

<img width="1362" height="875" alt="Haunted Forest gameplay" src="https://github.com/user-attachments/assets/6fa049d4-ec24-4f3a-8420-a5bca5bf8fd8" />

### 🧙 AI-Powered NPC Dialogue

Vael uses a locally running Qwen3 model to generate responses to player messages.

<img width="1371" height="887" alt="Vael AI dialogue" src="https://github.com/user-attachments/assets/11bde409-5e4b-4c26-9cdf-682310a9db62" />

### 🏔️ Mystic Valley

An explorable illustrated environment with pathways, ruins, and a portal.

<img width="1365" height="862" alt="Mystic Valley gameplay" src="https://github.com/user-attachments/assets/ccbe6816-3e14-47ac-90a2-e435382acb5a" />

---

## ✨ Features

### Exploration and Character Movement

- Three explorable environments: Bloodmoon Shrine, Mystic Valley, and Haunted Forest.
- Player movement and running.
- Animated character sprites.
- NPC interaction.
- Portals and scene transitions.
- Walkable-area collision system.

### Local AI Dialogue

The Wizard NPC, Vael, uses **Qwen3-4B** through `llama-cpp-python` to generate dialogue locally.

The system includes player text input, generated responses, conversation history, and response polling to avoid blocking the main game loop.

The language model runs locally, and its weights are not included in the repository.

### Experimental AI World Director

The Haunted Forest includes an experimental AI director implemented in `world_ai.py`.

The system selects from predefined actions related to environmental effects and supernatural encounters. Pygame is responsible for executing the selected actions.

This is a limited experimental system, not a fully autonomous game world.

### Forest Guardian

The Haunted Forest contains an animated Guardian with a separate horror controller, `guardian_horror.py`.

The controller includes behaviors such as teleporting, charging, growing, stalking, vanishing, and jumpscare effects.

These behaviors are still being tested and refined.

### Dynamic Environmental Effects

The game uses fog, particles, lighting overlays, smoke, and supernatural visual effects to add movement and atmosphere to illustrated backgrounds.

### Custom Walkable-Area Editor

A built-in editor allows walkable regions to be defined and saved for each environment.

This makes it possible to use detailed 2D illustrations as explorable game scenes without constructing complete 3D environments.

---

## 🤖 Computer Vision-Based Sprite Automation

### The Problem

Bloodmoon Shrine uses AI-generated artwork for its fantasy characters and monsters.

However, generated artwork is not automatically compatible with a game engine.

A sprite sheet may contain multiple poses with inconsistent spacing, unwanted backgrounds, overlapping character details, and variations in size or positioning.

To animate a character in Pygame, individual frames need to be extracted, cleaned, aligned, resized, and organized into a predictable sprite atlas.

Doing this manually for every new character would make asset creation increasingly time-consuming.

### The Approach

Rather than manually processing every sprite, I explored adapting existing **computer vision and image segmentation tools** to automate parts of the workflow.

The sprite-processing scripts use image-processing techniques and **SAM 2.1 (Segment Anything Model 2)** to help identify and extract character artwork from generated sprite sheets.

The extracted frames can then be prepared for the animation system used by the game.

This was an integration and automation task: adapting an existing segmentation model to a specific asset-processing problem, rather than developing or training a new segmentation model.

### Processing Pipeline

```text
AI-Generated Character Sprite Sheet
                 |
                 v
       Input Image Processing
                 |
                 v
       SAM 2.1 Segmentation
                 |
                 v
      Character Mask Extraction
                 |
                 v
     Individual Sprite Extraction
                 |
                 v
    Background / Artifact Cleanup
                 |
                 v
       Resizing and Alignment
                 |
                 v
       Animation Atlas Output
                 |
                 v
      pygame-ce Character System
```

The workflow combines model-assisted segmentation with conventional image processing.

### Implementation

The repository contains several scripts associated with this workflow:

| Component | Role |
|---|---|
| `sprite_auto.py` | Sprite extraction automation |
| `sprite_auto_v4.py` | Iterated version of the automation workflow |
| `sprite_processor.py` | Image and sprite-processing utilities |
| `inspect_hero.py` | Sprite inspection and debugging |
| `sprite_auto_output/` | Generated sprite atlases and previews |
| `sprite_diagnostics/` | Diagnostic outputs used during development |
| `characters.py` | Character animation and sprite rendering |

The SAM 2.1 model is used locally. Its model weights are excluded from the repository.

### Adapting the Input to Improve Segmentation

An important part of the development process was discovering that segmentation quality depended on how the original sprite sheet was generated.

For example, when a staff, cape, or limb overlapped a neighboring pose, the segmentation process could incorrectly remove part of a character or include unwanted artwork.

Instead of relying only on post-processing, I adjusted the **character-generation approach itself** to make the images easier for the segmentation model to process.

This included:

- Keeping individual poses clearly separated.
- Using more consistent character proportions.
- Avoiding unnecessary overlap between neighboring frames.
- Making silhouettes and character accessories easier to distinguish.
- Reducing visual clutter around characters.
- Inspecting the extracted sprites and adjusting the input artwork when necessary.

This created an iterative workflow:

**Generate artwork → Process with segmentation → Inspect results → Identify errors → Adjust input → Process again**

The same approach was used while developing character assets such as the Shrine Master and Forest Guardian.

### What the Automation Achieves

The workflow reduces the amount of repetitive manual work involved in preparing AI-generated character artwork for the game.

It also provides a more consistent process for organizing character frames into animation assets.

However, segmentation results are not always perfect. Some images still require inspection, corrections, or changes to the original artwork.

The workflow is therefore best described as **AI-assisted sprite processing with partial automation**, rather than a fully autonomous sprite-generation system.

### Development Focus

This part of the project demonstrates the practical application of several techniques:

- **Computer vision integration:** Applying an existing segmentation model to a game asset-processing task.
- **Workflow automation:** Reducing repetitive image extraction and preparation steps.
- **Pipeline development:** Connecting generated artwork, segmentation, image processing, and game rendering.
- **Iterative debugging:** Inspecting failed extractions and improving the input or processing workflow.
- **Model-aware input design:** Adjusting the structure of generated images to make them easier for the model to process.
- **Tool adaptation:** Using an existing machine-learning tool outside its original demonstration context to solve a specific development problem.

The longer-term goal is to improve reliability and reduce manual intervention when adding new characters and monsters.

---

## 🛠️ Technology Stack

| Technology | Purpose |
|---|---|
| Python | Game logic and supporting tools |
| pygame-ce | 2D rendering, animation, input, and collision |
| Qwen3-4B | Local NPC dialogue and experimental world actions |
| llama-cpp-python | Local language model inference |
| SAM 2.1 | Character image segmentation |
| Image-processing utilities | Sprite extraction and atlas preparation |
| JSON | Configuration and NPC memory |
| AI-generated artwork | Backgrounds and character assets |

---

## 🎮 Controls

| Key | Action |
|---|---|
| W / A / S / D | Move |
| Shift | Run |
| E | Interact |
| Enter | Submit dialogue |
| Escape | Close dialogue |
| F2 | Path editor |
| F3 | Debug mode |
| F5 | Save path edits |

---

## 🚀 Installation

### Requirements

- Python 3.12 recommended.
- Windows (current development platform).
- `pygame-ce`.
- `llama-cpp-python`.
- A compatible Qwen3 GGUF model for local AI dialogue.

Optional sprite-processing utilities may require additional Python dependencies and separately downloaded SAM 2.1 model weights.

### 1. Clone the Repository

```bash
git clone https://github.com/N1S55M-X/Bloodmoon-Shrine.git
cd Bloodmoon-Shrine
```

### 2. Install Core Dependencies

```bash
python -m pip install pygame-ce llama-cpp-python
```

Additional dependencies may be required for the sprite-processing utilities.

### 3. Configure the Language Model

Download a compatible Qwen3 GGUF model separately.

Configure its local path according to `npc_ai.py` and `world_ai.py`.

Model weights are not included in this repository.

### 4. Run the Game

```bash
python game.py
```

Some AI features require additional local configuration.

---

## 🧩 Project Structure

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

### Main Components

**`game.py`** — Main game loop, input handling, and integration of game systems.

**`characters.py`** — Character animation and sprite rendering.

**`scene_manager.py`** — Scene management, portals, and transitions.

**`environment.py`** — Environmental visual effects.

**`npc_ai.py`** — Local language model interface for NPC dialogue.

**`world_ai.py`** — Experimental AI-based environmental action selection.

**`guardian_horror.py`** — Guardian supernatural animations and effects.

**Sprite-processing scripts** — Utilities for extracting and preparing character sprites.

---

## 🔮 Development Roadmap

The following features are planned or under consideration.

### AI and NPCs

- Improve NPC memory and context handling.
- Reduce local AI inference overhead.
- Allow NPCs to respond to more game-state information.
- Improve the reliability of AI-selected actions.

### Sprite Processing and Automation

- Improve segmentation accuracy for complex character artwork.
- Reduce errors caused by overlapping poses and accessories.
- Improve frame alignment and animation consistency.
- Add better automated quality checks.
- Reduce manual cleanup.
- Support more character and monster sprite sheets.

### Gameplay

- Improve Guardian behavior and encounters.
- Add additional creatures and NPCs.
- Develop combat and health systems.
- Add quests, inventory, and progression.
- Improve character and environment interactions.

### Environments

- Add animated environmental objects.
- Improve fog, lighting, and weather effects.
- Expand explorable locations.
- Experiment with AI-directed environmental interactions.

### Distribution

- Improve installation and model configuration.
- Package a Windows executable.
- Investigate browser compatibility for a simplified version.

---

## ⚠️ Development Status

**Experimental Alpha — Work in Progress**

Bloodmoon Shrine currently includes basic exploration, character animation, collision editing, scene transitions, and locally generated NPC dialogue.

The AI World Director, Guardian Horror controller, and sprite-processing tools are experimental components undergoing further development.

The sprite automation workflow has been used to prepare game assets, but some manual inspection and adjustment are still necessary.

The game currently runs from Python source code. A standalone executable and browser version are not yet available.

---

## 🤝 Contributions

Bug reports, suggestions, and contributions are welcome, particularly in:

- Python game development.
- Computer vision and image segmentation.
- Workflow automation.
- Sprite processing and animation.
- Local language models.
- Game AI.
- Environmental effects and optimization.

---

## 👨‍💻 Developer

**N1S55M-X**

GitHub: https://github.com/N1S55M-X

Repository: https://github.com/N1S55M-X/Bloodmoon-Shrine

---

<p align="center">
  <img src="https://github.com/user-attachments/assets/6b3d80f8-ba54-41c5-aab6-9628f928da65" alt="Bloodmoon Shrine" width="650">
</p>
