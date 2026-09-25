import unittest

import gymnasium as gym
import highway_env as highway
import numpy as np
from gymnasium import Env

from src.observation_logger import ObservationLogger

def create_test_env() -> Env:
    env = gym.make('highway-v0', render_mode='rgb_array', config={"observation": {
            "type": "MultiAgentObservation",
            "observation_config": {
                "type": "Kinematics",
                "vehicles_count": 1,
                "features": ["x", "y", "vx", "vy"],
                "normalize": False,
                "absolute": False,
                "see_behind": True,
                "order": "sorted"
            },
        }})
    env.reset()
    return env

class TestObservationLogger(unittest.TestCase):

    def test_logger(self):
        logger = ObservationLogger()

        env = create_test_env()
        obs, _ = env.reset()
        logger.save_observation(obs)

        obs = np.round(np.array(obs))
        saved_obs = np.round(logger.read_observations())

        for i in range(len(obs)):
            for j in range(len(obs[i])):
                for k in range(len(obs[i][j])):
                    self.assertEqual(obs[i][j][k], saved_obs[i][j][k])

    def test_logger_negativ(self):
        logger = ObservationLogger()

        logger.save_observation(["","",""])

        with self.assertRaises(ValueError):
            logger.read_observations()