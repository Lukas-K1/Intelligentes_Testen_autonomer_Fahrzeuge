from typing import Optional

import gymnasium as gym
import highway_env
import numpy as np
from highway_env.vehicle.behavior import IDMVehicle


class IntersectionCutOffScenarioEnv(gym.Env):
    """RL-Agent soll dem VUT von rechts die Vorfahrt nehmen"""

    metadata = {"render_modes": ["human", "rgb_array"]}

    def __init__(self, render_mode: Optional[str] = None):
        cfg = {
            "lanes_count": 2,
            "vehicles_count": 0,
            "controlled_vehicles": 1,
            "duration": 100,  # Are 10 seconds at 10Hz
            "initial_positions": [[150, 1, 10]],  # Agent bei x=35m, 10m/s
            "simulation_frequency": 10,
            "policy_frequency": 10,
        }
        # Use the intersection-v0 environment from highway-env
        self._core_env = gym.make("intersection-v0", render_mode=render_mode, config=cfg)
        self.base_env = self._core_env.unwrapped

        # Use highway-env’s own RNG for consistent randomizations
        self.np_random = self.base_env.road.np_random

        self.observation_space = self._core_env.observation_space
        self.action_space = self._core_env.action_space

        # Internal state
        self._steps = 0
        self.phase = 0
        self.time_since_abort_check = 0
        self.last_dist = None
        self.prev_agent_lane = None

    def seed(self, seed: Optional[int] = None):
        """Optional compatibility: allow env.seed(...) calls."""
        self._core_env.seed(seed)
        self.np_random.seed(seed)
        return [seed]

    def reset(
            self,
            **kwargs
    ):
        # Forward seed & other args to the core env
        obs, info = self._core_env.reset(**kwargs)

        agent = self.base_env.vehicle
        # === Randomize agent’s initial speed ±10% around 10 m/s ===
        base_speed = 10.0
        agent.speed = self.np_random.uniform(0.9 * base_speed, 1.1 * base_speed)

        # Create the VUT from the agent’s current state
        vut = IDMVehicle.create_from(agent)
        # === Randomize VUT initial gap (15–25 m) ===
        gap = self.np_random.uniform(15.0, 25.0)
        vut.position = (agent.position[0] - gap, agent.position[1])
        # === Randomize VUT speed & target_speed (slightly faster) ===
        min_vs = agent.speed * 1.05
        max_vs = agent.speed * 1.3
        vut.speed = self.np_random.uniform(min_vs, max_vs)
        vut.target_speed = vut.speed + self.np_random.uniform(0.5, 2.0)

        self.base_env.road.vehicles.append(vut)
        self.vut = vut

        # Reset internal counters and tracking
        self._steps = 0
        self.phase = 0
        self.time_since_abort_check = 0
        # Track initial distance and lane for reward shaping
        agent_x = self.base_env.vehicle.position[0]
        vut_x = self.vut.position[0]
        self.last_dist = vut_x - agent_x
        self.prev_agent_lane = self.base_env.vehicle.lane_index[1]

        return obs, info

    def step(self, action):
        # Step VUT (IDM gesteuert)
        neighbours = self.vut.road.network.all_side_lanes(self.vut.lane_index)
        lane = (
            self.vut.target_lane_index[2]
            if isinstance(self.vut, IDMVehicle)
            else self.lane_index[2]
        )

        self.vut.act()
        dt = 1 / self.base_env.config["simulation_frequency"]
        self.vut.step(dt)

        # Step Agent (gesteuert durch RL)
        obs, _, _, truncated, info = self._core_env.step(action)

        # 3) Compute relative positions and reward shaping
        agent = self.base_env.vehicle
        agent_x = agent.position[0]
        vut_x = self.vut.position[0]
        dist = vut_x - agent_x

        # Shaped reward: progress in forcing overtake
        delta = dist - self.last_dist
        reward = 0.1 * delta
        self.last_dist = dist

        # Small step penalty to encourage efficiency
        reward -= 0.01

        # Penalize excessive lane changes
        current_lane = agent.lane_index[1]
        if current_lane != self.prev_agent_lane:
            reward -= 0.01
        self.prev_agent_lane = current_lane

        terminated = False

        agent_y = agent.position[1]
        vut_y = self.vut.position[1]

        # === Kreuzungslogik ===
        # Phase 0: beide nähern sich Kreuzung
        if self.phase == 0:
            if abs(agent_y) < 5 and abs(vut_x) < 5:
                # beide gleichzeitig in Kreuzung -> Risiko
                reward -= 0.3
            elif agent_y > -5:
                # Agent fährt in Kreuzung hinein
                self.phase = 1

        # Phase 1: Durchfahrt
        if self.phase == 1:
            if agent_y > 20:
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
