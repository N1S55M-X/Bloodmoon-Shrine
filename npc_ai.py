
import json
import queue
import threading
import traceback
from pathlib import Path

from huggingface_hub import hf_hub_download
from llama_cpp import Llama


# ==========================================================
# BLOODMOON SHRINE - SHARED NPC LANGUAGE MODEL
# ==========================================================

ROOT = Path(__file__).resolve().parent
MODEL_DIR = ROOT / "models"
MEMORY_FILE = ROOT / "npc_memory.json"

MODEL_REPO = "unsloth/Qwen3-4B-Instruct-2507-GGUF"
MODEL_FILE = "Qwen3-4B-Instruct-2507-Q4_K_M.gguf"
MODEL_PATH = MODEL_DIR / MODEL_FILE

CONTEXT_SIZE = 4096
MAX_TOKENS = 150
CPU_THREADS = 4

# ==========================================================
# NPC PERSONALITIES
# ==========================================================

NPCS = {
    "wizard": {
        "name": "Vael",
        "role": "Ancient Wizard",
        "personality": (
            "You are Vael, an ancient wizard in a dark fantasy RPG. "
            "You are intelligent, proud, witty and occasionally sarcastic. "
            "You study magic and guard ancient secrets. "
            "You know the Warlock, who is speaking to you. "
            "Respond directly to what the Warlock says. "
            "If asked for powers, explain what magic you could teach. "
            "If insulted, respond naturally and in character. "
            "You may discuss spells, history, danger and quests. "
            "Speak in one to three complete sentences. "
            "Do not begin every reply with 'Ah'. "
            "Do not repeat yourself or change the subject."
        )
    },
    "shrine_master": {
        "name": "Shrine Master",
        "role": "Guardian of the Portal",
        "personality": (
            "You are the Shrine Master, an old and stern guardian. "
            "You protect the portal between Bloodmoon Shrine "
            "and Mystic Valley. You are solemn, knowledgeable "
            "and suspicious of strangers. "
            "Respond directly to the player's latest message. "
            "Speak in one to three sentences."
        )
    },
    "merchant": {
        "name": "Merchant",
        "role": "Traveling Merchant",
        "personality": (
            "You are a traveling merchant in a fantasy village. "
            "You are charming, practical and interested in trading. "
            "Respond directly to the player's latest message. "
            "Do not invent actual game inventory or prices. "
            "Speak in one to three sentences."
        )
    }
}

WORLD_KNOWLEDGE = (
    "World: Bloodmoon Shrine is an ancient fantasy settlement. "
    "Mystic Valley is a mysterious mountain forest. "
    "The Shrine Master guards a portal between these places. "
    "The player character is a Warlock."
)


# ==========================================================
# SHARED MODEL
# ==========================================================

class SharedNPCModel:

    _model = None
    _load_lock = threading.Lock()
    _generate_lock = threading.Lock()

    @classmethod
    def get_model(cls):
        with cls._load_lock:
            if cls._model is not None:
                return cls._model

            MODEL_DIR.mkdir(
                parents=True,
                exist_ok=True
            )

            if not MODEL_PATH.exists():
                print("Downloading Qwen3-4B NPC model...")
                print("This happens only once.")
                print("Model size: approximately 2.5 GB")

                hf_hub_download(
                    repo_id=MODEL_REPO,
                    filename=MODEL_FILE,
                    local_dir=str(MODEL_DIR)
                )

            print("Loading shared NPC model...")

            cls._model = Llama(
                model_path=str(MODEL_PATH),
                n_ctx=CONTEXT_SIZE,
                n_threads=CPU_THREADS,
                n_gpu_layers=0,
                n_batch=256,
                verbose=False
            )

            print("Shared NPC model ready!")
            return cls._model

    @classmethod
    def generate(cls, messages):
        model = cls.get_model()

        # A single llama.cpp context must not be used
        # simultaneously by multiple NPC threads.
        with cls._generate_lock:
            response = model.create_chat_completion(
                messages=messages,
                max_tokens=MAX_TOKENS,
                temperature=0.65,
                top_p=0.85,
                repeat_penalty=1.12
            )

        return (
            response["choices"][0]["message"]
            .get("content") or ""
        ).strip()


# ==========================================================
# NPC CONVERSATION AND MEMORY
# ==========================================================

class NPCBrain:

    def __init__(self, npc_id="wizard"):
        if npc_id not in NPCS:
            raise ValueError(
                f"Unknown NPC: {npc_id}"
            )

        self.npc_id = npc_id
        self.config = NPCS[npc_id]

        self.history = []
        self.pending = False
        self.results = queue.Queue()
        self.lock = threading.Lock()

        self.load_memory()

    def load_memory(self):
        if not MEMORY_FILE.exists():
            return

        try:
            data = json.loads(
                MEMORY_FILE.read_text(encoding="utf-8")
            )

            self.history = [
                msg for msg in data.get(self.npc_id, [])
                if isinstance(msg, dict)
                and msg.get("role") in ("user", "assistant")
                and isinstance(msg.get("content"), str)
            ][-24:]

        except Exception as exc:
            print("NPC memory error:", exc)

    def save_memory(self):
        # Preserve memory belonging to other NPCs.
        with SharedMemory.lock:
            data = {}

            if MEMORY_FILE.exists():
                try:
                    data = json.loads(
                        MEMORY_FILE.read_text(
                            encoding="utf-8"
                        )
                    )
                    if not isinstance(data, dict):
                        data = {}
                except Exception:
                    data = {}

            data[self.npc_id] = self.history[-24:]

            temp = MEMORY_FILE.with_suffix(".tmp")
            temp.write_text(
                json.dumps(
                    data,
                    indent=2,
                    ensure_ascii=False
                ),
                encoding="utf-8"
            )
            temp.replace(MEMORY_FILE)

    def reset_memory(self):
        with self.lock:
            if self.pending:
                return False

            self.history.clear()
            self.save_memory()

        return True

    def relevant_environment(self, message, observations):
        # Environment is optional, not the primary prompt.
        # Only supply it for questions about surroundings.
        if not isinstance(observations, dict):
            return ""

        keywords = (
            "rain", "weather", "fog", "here",
            "where", "around", "see", "near",
            "portal", "shrine", "valley",
            "location", "surroundings"
        )

        if not any(
            word in message.lower()
            for word in keywords
        ):
            return ""

        lines = []

        for key, value in observations.items():
            if isinstance(value, (str, int, float, bool)):
                lines.append(f"{key}: {value}")

        return "\n".join(lines)[:700]

    def ask(self, message, observations=None):
        message = str(message).strip()

        if not message:
            return False

        with self.lock:
            if self.pending:
                return False
            self.pending = True

        snapshot = (
            dict(observations)
            if isinstance(observations, dict)
            else {}
        )

        threading.Thread(
            target=self._generate,
            args=(message, snapshot),
            daemon=True
        ).start()

        return True

    def _generate(self, message, observations):
        try:
            system = (
                self.config["personality"]
                + "\n"
                + WORLD_KNOWLEDGE
                + "\n"
                + "Answer the player's most recent message "
                + "before discussing anything else. "
                + "Never claim to change game state."
            )

            environment = self.relevant_environment(
                message,
                observations
            )

            if environment:
                system += (
                    "\nRelevant current observations:\n"
                    + environment
                )

            with self.lock:
                previous = list(self.history[-10:])

            messages = [
                {
                    "role": "system",
                    "content": system
                },
                *previous,
                {
                    "role": "user",
                    "content": message
                }
            ]

            print(
                f"{self.config['name']} responding to:",
                message
            )

            answer = SharedNPCModel.generate(messages)

            if not answer:
                answer = (
                    "Speak again, Warlock. "
                    "I did not quite understand."
                )

            # Defensive removal of accidental role text.
            for marker in (
                "<|im_start|>",
                "<|im_end|>",
                "\nUser:",
                "\nAssistant:"
            ):
                if marker in answer:
                    answer = answer.split(marker, 1)[0].strip()

            if not answer:
                answer = "What do you seek?"

            with self.lock:
                self.history.extend([
                    {"role": "user", "content": message},
                    {"role": "assistant", "content": answer}
                ])
                self.history = self.history[-24:]
                self.save_memory()

            self.results.put(("success", answer))
            print(self.config["name"] + ":", answer)

        except Exception as exc:
            traceback.print_exc()
            self.results.put((
                "error",
                f"AI ERROR: {str(exc)[:160]}"
            ))

        finally:
            with self.lock:
                self.pending = False

    def poll(self):
        try:
            return self.results.get_nowait()
        except queue.Empty:
            return None


class SharedMemory:
    lock = threading.Lock()


# ==========================================================
# COMPATIBILITY WITH YOUR EXISTING GAME
# ==========================================================

class WizardAI(NPCBrain):
    def __init__(self, model=None):
        super().__init__("wizard")


# ==========================================================
# STANDALONE TEST
# ==========================================================

if __name__ == "__main__":
    import time

    print("=" * 55)
    print("BLOODMOON SHRINE - NPC AI TEST")
    print("=" * 55)

    wizard = WizardAI()

    print("Testing Vael with no environmental distractions.")
    print("Type 'quit' to exit.")

    while True:
        try:
            question = input("\nWarlock: ").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if question.lower() in ("quit", "exit"):
            break

        if not question:
            continue

        if wizard.ask(question, {}):
            while wizard.pending:
                time.sleep(0.1)

            result = wizard.poll()
            if result:
                print("Vael:", result[1])
