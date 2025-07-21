from stable_baselines3 import DQN
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.callbacks import BaseCallback
from src.envs.overtake_env import CutOffScenarioEnv
import torch
from pathlib import Path

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
    env = DummyVecEnv([lambda: CutOffScenarioEnv(render_mode="human")])

    # Modell initialisieren
    model = DQN(
        policy="MlpPolicy",
        device = "cuda" if use_cuda else "cpu",
        env=env,
        learning_rate=5e-4,
        buffer_size=10000,
        batch_size=64,
        gamma=0.95,
        train_freq=1,
        target_update_interval=100,
        verbose=1,
        tensorboard_log="logs/overtake_rl/",
    )

    # Training mit Render-Callback starten
    model.learn(total_timesteps=200_000, callback=RenderCallback(render_freq=20))

    # Modellpfad erstellen, falls nicht vorhanden
    Path("models").mkdir(exist_ok=True)

    # Modell speichern
    model.save("models/overtake_dqn.zip")
    print("Modell gespeichert unter models/overtake_dqn.zip")
