import time
from pathlib import Path

import numpy as np
import torch
from envs.intersection_aggressive_env import IntersectionCutOffScenarioEnv
from stable_baselines3 import DQN
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.vec_env import DummyVecEnv

SEED = 42

np.random.seed(SEED)
torch.manual_seed(SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)

def make_env(rank: int):
    """Funktion zum Erstellen einer einzelnen Umgebung."""
    def _init():
        env = IntersectionCutOffScenarioEnv(render_mode="human")
        obs, info = env.reset()
        return env
    return _init



class RenderCallback(BaseCallback):
    """Rendert jede N-te Episode im Trainingsfenster."""
    def __init__(self, render_freq: int = 20, verbose: int = 0):
        super().__init__(verbose)
        self.render_freq = render_freq
        self.episode_count = 0

    def _on_step(self) -> bool:
        # SB3 ruft _on_step während des Trainings sehr häufig auf.
        # Wir prüfen, ob gerade eine Episode beendet wurde.
        if self.locals.get("dones") is not None and any(self.locals["dones"]):
            self.episode_count += 1
            if self.episode_count % self.render_freq == 0:
                # Erste (und einzige) Env rendern
                self.training_env.envs[0].render()
        return True

if __name__ == "__main__":
    # ---------------- GPU-Check ----------------
    use_cuda = torch.cuda.is_available()
    device   = "cuda" if use_cuda else "cpu"
    print(f"Training auf Gerät: {device}")

    # Umgebung einrichten
    env = DummyVecEnv([lambda: IntersectionCutOffScenarioEnv(render_mode="human")])

    # Modell initialisieren
    model = DQN(
        policy="MlpPolicy",
        device = "cuda" if use_cuda else "cpu",
        env=env,
        learning_rate=1e-4,
        buffer_size=200_000,
        learning_starts=1_000,
        batch_size=128,
        gamma=0.99,
        train_freq=4,
        target_update_interval=1_000,
        gradient_steps=1,
        exploration_fraction=0.1,
        exploration_initial_eps=1.0,
        exploration_final_eps=0.02,
        policy_kwargs=dict(net_arch=[256, 256]),
        verbose=1,
        tensorboard_log="logs/intersection_cutoff/",
    )

    # Training mit Render-Callback starten
    # model.learn(total_timesteps=1_000_000, callback=RenderCallback(render_freq=20))
    model.learn(total_timesteps=1_000_000, callback=RenderCallback(render_freq=20))

    # Modellpfad erstellen, falls nicht vorhanden
    Path("models").mkdir(exist_ok=True)

    # Modell speichern
    # Current time as a string for unique filename
    current_time = time.strftime("%Y%m%d-%H%M%S")
    model.save("models/intersection_cutoff_dqn_" + current_time + ".zip")
    print("Modell gespeichert unter models/intersection_cutoff_dqn " + current_time + ".zip")
