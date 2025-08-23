import time

from src.envs.overtake_env import CutOffScenarioEnv
from stable_baselines3 import DQN

if __name__ == "__main__":
    # Umgebung vorbereiten
    env = CutOffScenarioEnv(render_mode="rgb_array")
    obs, _ = env.reset()

    # Modell laden
    model = DQN.load("D:/Programming/models/overtake_dqn.zip", env=env)

    total_reward = 0
    done = False

    while not done:
        action, _ = model.predict(obs, deterministic=False)
        obs, reward, done, truncated, info = env.step(action)
        total_reward += reward

        env.render()
        time.sleep(0)  # für flüssigere Darstellung

    print(f"Episode beendet. Gesamt-Reward: {total_reward:.2f}")
