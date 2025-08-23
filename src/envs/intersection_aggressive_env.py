import gymnasium as gym
import highway_env
from highway_env.vehicle.behavior import IDMVehicle
from typing import Optional
import numpy as np


class IntersectionCutOffScenarioEnv(gym.Env):
    """RL-Agent soll dem VUT von rechts die Vorfahrt nehmen"""

    metadata = {"render_modes": ["human", "rgb_array"]}

    def __init__(self, render_mode: Optional[str] = None):
        cfg = {
            "observation": {
                "type": "Kinematics",
                "vehicles_count": 5,
                "features": ["x", "y", "vx", "vy"],
                "absolute": True,
                "order": "sorted"
            },
            "duration": 100,
            "simulation_frequency": 10,
            "policy_frequency": 10,
            "screen_width": 600,
            "screen_height": 600,
            "centering_position": [0.5, 0.5],
        }

        # intersection env
        self._core_env = gym.make("intersection-v0", render_mode=render_mode, config=cfg)
        self.base_env = self._core_env.unwrapped
        self.np_random = self.base_env.road.np_random

        # use same spaces
        self.observation_space = self._core_env.observation_space
        self.action_space = self._core_env.action_space

        # Internal state
        self._steps = 0
        self.phase = 0
        self.last_dist = None

    def reset(self, **kwargs):
        obs, info = self._core_env.reset(**kwargs)

        # Agent von unten (südliche Zufahrt → nach oben)
        agent = self.base_env.vehicle
        agent.position = (0, -60)   # unten
        agent.heading = np.pi / 2   # nach oben
        agent.speed = 8.0

        # VUT von rechts (östliche Zufahrt → nach links)
        vut = IDMVehicle.create_random(self.base_env.road)
        vut.position = (60, 0)      # rechts
        vut.heading = np.pi         # nach links
        vut.speed = 9.0
        vut.target_speed = 9.0

        self.base_env.road.vehicles.append(vut)
        self.vut = vut

        # Reset counters
        self._steps = 0
        self.phase = 0
        self.last_dist = np.linalg.norm(
            np.array(agent.position) - np.array(vut.position)
        )

        return obs, info

    def step(self, action):
        # Step VUT (IDM gesteuert)
        self.vut.act()
        dt = 1 / self.base_env.config["simulation_frequency"]
        self.vut.step(dt)

        # Step Agent (gesteuert durch RL)
        obs, _, _, truncated, info = self._core_env.step(action)

        agent = self.base_env.vehicle
        dist = np.linalg.norm(
            np.array(agent.position) - np.array(self.vut.position)
        )

        reward = 0.0
        terminated = False

        # === Kreuzungslogik ===
        # Phase 0: beide nähern sich Kreuzung
        if self.phase == 0:
            if abs(agent.position[1]) < 5 and abs(self.vut.position[0]) < 5:
                # beide gleichzeitig in Kreuzung -> Risiko
                reward -= 0.3
            elif agent.position[1] > -5:
                # Agent fährt in Kreuzung hinein
                self.phase = 1

        # Phase 1: Durchfahrt
        if self.phase == 1:
            if agent.position[1] > 20:
                # Agent hat Kreuzung klar überquert
                reward += 1.0  # Erfolg: Vorfahrt genommen
                terminated = True
            elif info.get("crashed", False):
                reward -= 1.0  # Unfall
                terminated = True
            else:
                reward -= 0.01  # kleine Schrittstrafe

        self._steps += 1
        if self._steps >= self.base_env.config["duration"] * self.base_env.config["simulation_frequency"]:
            terminated = True

        return obs, reward, terminated, truncated, info

    def render(self):
        return self._core_env.render()
