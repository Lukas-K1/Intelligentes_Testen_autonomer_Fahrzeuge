from typing import Any, Dict, List

import gymnasium as gym
import highway_env as highway
from bppy import *

# BPpy Events
change_right = BEvent("change_right")
change_left = BEvent("change_left")
increase_speed = BEvent("increase_speed")
reduce_speed = BEvent("reduce_speed")
keep_speed = BEvent("keep_speed")


def create_env(config: Dict[str, Any]) -> gym.Env:
    env = gym.make('highway-v0', render_mode='rgb_array', config=config)
    env.reset()
    return env


@thread
def change_lane_right():
    yield sync(waitFor=change_right)


@thread
def change_lane_left():
    yield sync(waitFor=change_left)


@thread
def speed_increase():
    yield sync(waitFor=increase_speed)


@thread
def speed_reduce():
    yield sync(waitFor=reduce_speed)


@thread
def speed_idle():
    yield sync(waitFor=keep_speed)


@thread
def control_vehicle(env):
    while True: # TODO placeholder
        yield sync(request=change_right)
        yield sync(request=change_left)
        yield sync(request=increase_speed)
        yield sync(request=reduce_speed)
        yield sync(request=keep_speed)


@thread
def control_events():
    print("Control events") # TODO placeholder


def set_config():
    config = {
        "centering_position": [0.5, 0.5],
        "vehicles_count": 1,
        "controlled_vehicles": 7,
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
                "features": ["x", "y", "vx", "vy"],
                "normalize": False,
                "absolute": False,
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
    bp = BProgram(bthreads=[change_lane_right(), change_lane_left(), speed_increase(), speed_reduce(), speed_idle(), control_vehicle(env)],
                  event_selection_strategy=SimpleEventSelectionStrategy(), listener=PrintBProgramRunnerListener())
    #bp.run()

    for _ in range(100):
        bp.run()
        obs = env.step((1, 1, 2, 4, 0, 4, 4))
        print(obs)
        env.render()

    env.close()


if __name__ == "__main__":
    main()
