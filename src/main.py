from bppy import *
import gymnasium as gym
import highway_env as highway
from typing import Dict, Any, List

# BPpy Events

def create_env(config: Dict[str, Any]) -> gym.Env:
    env = gym.make('highway-v0', render_mode='rgb_array', config=config)
    env.reset()
    return env


def set_config():
    config = {
        "centering_position": [0.5, 0.5],
        "vehicles_count": 0,
        "controlled_vehicles": 8,
        "lanes_count": 4,
        "initial_positions": [
            [15, 2, 32],  # (x_position, lane_index, speed)
            [45, 1, 20],
            [65, 2, 27],
            [105, 0, 15],
            [135, 3, 35],
            [165, 1, 17],
            [195, 3, 23],
            [225, 0, 29]
        ],  # Fixed start positions WIP
        "observation": {
            "type": "MultiAgentObservation",
            "observation_config": {
                "type": "Kinematics",
                "vehicles_count": 1,
                "features": ["presence", "x", "y", "vx", "vy"],
                "features_range": {
                    "x": [-100, 100],
                    "y": [-100, 100],
                    "vx": [-20, 20],
                    "vy": [-20, 20]
                },
                "normalize": False,
                "absolute": True,
                "see_behind": True,
                "order": "sorted"
            },
        },
        "action": {
            "type": "MultiAgentAction",
            "action_config": {
                "type": "DiscreteMetaAction",
                "longitudinal": True,
                "lateral": True,
                "target_speeds": [0, 5, 10, 15, 20, 25, 30]
            },
        },
        "simulation_frequency": 100
    }
    return config


def main():

    config = set_config()
    env = create_env(config)
    obs, _ = env.reset()
    # bp = BProgram(bthreads=[],
    #               event_selection_strategy=SimpleEventSelectionStrategy(), listener=PrintBProgramRunnerListener())
    # bp.run()

    for _ in range(100):
        #bp.run()
        obs = env.step((1, 1, 2, 4,0,4,4,4))
        print(obs)
        env.render()

    env.close()


if __name__ == "__main__":
    main()