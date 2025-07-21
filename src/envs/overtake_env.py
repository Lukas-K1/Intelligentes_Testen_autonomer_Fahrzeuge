import gymnasium as gym
import highway_env
from highway_env.vehicle.behavior import IDMVehicle


class CutOffScenarioEnv(gym.Env):
    """RL‑Agent zwingt das VUT zum Überholen

    Phasenlogik (state machine):
    0 = VUT hinter Agent  (Start)
    1 = VUT neben Agent   (x‑Differenz |dist| < 5m, Spur ≠ Agent)
    2 = VUT überholt      (dist ≥ 20m und Spur ≠ Agent) → Erfolg, große Belohnung
    Abbruch: VUT bleibt > 5m hinter Agent in derselben Spur länger als 5s.
    """

    metadata = {"render_modes": ["human", "rgb_array"]}

    def __init__(self, render_mode: str | None = None):
        cfg = {
            "lanes_count": 2,
            "vehicles_count": 0,
            "controlled_vehicles": 1,
            "duration": 60,
            "initial_positions": [[35, 1, 10]],  # Agent bei x=35m, 10m/s
            "simulation_frequency": 10,
        }
        self._core_env = gym.make("highway-v0", render_mode=render_mode, config=cfg)
        self.base_env = self._core_env.unwrapped

        self.observation_space = self._core_env.observation_space
        self.action_space = self._core_env.action_space

        self._steps = 0
        self.phase = 0  # Startphase
        self.time_since_abort_check = 0

    # ------------------------------------------------------------------
    def reset(self, **kwargs):
        obs, info = self._core_env.reset(**kwargs)

        agent = self.base_env.vehicle

        # VUT 20m dahinter, leicht schneller
        vut = IDMVehicle.create_from(agent)
        vut.position = (agent.position[0] - 20.0, agent.position[1])
        vut.speed = 12.0
        vut.target_speed = 13.0
        self.base_env.road.vehicles.append(vut)
        self.vut = vut

        self._steps = 0
        self.phase = 0
        self.time_since_abort_check = 0
        return obs, info

    # ------------------------------------------------------------------
    def step(self, action):
        # VUT fährt IDM
        self.vut.act()
        self.vut.step(1 / self.base_env.config["policy_frequency"])

        # Agent handelt
        obs, _, terminated, truncated, info = self._core_env.step(action)

        # Positionsdaten
        agent_x = self.base_env.vehicle.position[0]
        vut_x = self.vut.position[0]
        dist = vut_x - agent_x  # >0 wenn VUT vorn
        agent_lane = self.base_env.vehicle.lane_index[1]
        vut_lane = self.vut.lane_index[1]

        reward = -0.01  # Grundstrafe pro Schritt
        done = False

        # ------------------------------------------------ Phase‑Logik
        if self.phase == 0:
            # Warten bis VUT aufschließt / Spurwechsel beginnt
            if abs(dist) < 5 and vut_lane != agent_lane:
                self.phase = 1
                reward += 0.3  # kleines Erfolgssignal
        elif self.phase == 1:
            # Prüfen, ob Überholen abgeschlossen
            if dist >= 20 and vut_lane != agent_lane:
                self.phase = 2
                reward = 1.0  # großer Reward
                done = True
            # Abbruch, falls VUT zurückfällt (>10m hinter Agent) oder wieder gleiche Spur
            elif dist < -10 or (vut_lane == agent_lane and dist < 5):
                reward = -1.0
                done = True

        # ------------------------------------------------ Schrittlimit / Crash
        self._steps += 1
        if info.get("crashed", False):
            reward = -1.0
            done = True
        if self._steps >= 60:
            done = True

        return obs, reward, done, truncated, info

    def render(self):
        return self._core_env.render()
