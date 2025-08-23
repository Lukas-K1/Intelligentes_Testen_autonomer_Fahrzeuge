import time
from typing import Any, Dict, List

import gymnasium as gym
import highway_env
from bppy import *

# TODO DO NOT USE OBSOLETE DEMO
# BPpy Events
CHECK_CLEARANCE = BEvent("CheckClearance")
START_OVERTAKE = BEvent("StartOvertake")
PERFORM_OVERTAKE = BEvent("PerformOvertake")
COMPLETE_OVERTAKE = BEvent("CompleteOvertake")
ABORT_OVERTAKE = BEvent("AbortOvertake")


def create_env(config: Dict[str, Any]) -> gym.Env:
    env = gym.make("highway-v0", render_mode="rgb_array", config=config)
    env.reset()
    return env


def decide_overtake_action(vehicles: List[List[float]], lane_width: float = 4.0) -> int:
    """ 
    :param vehicles: List of vehicles in the highway_env observation
    :param lane_width: float width of each lane
    :return: action code for the highway_env
    """
    ego_vehicle = vehicles[0]

    if len(vehicles) == 1:
        return 1
    for i in range(1, len(vehicles)):
        current_vehicle = vehicles[i]
        action = check_action_for_vehicle(current_vehicle, ego_vehicle)
        if action != 1:
            return action
        return 1


def check_action_for_vehicle(current_vehicle: List[float], ego_vehicle: List[float], lane_width: float = 4.0) -> int:
    """
    :param current_vehicle: the highway_env observation of the current non-controlled vehicle
    :param ego_vehicle: the highway_env observation of the ego vehicle
    :param lane_width: floar width of each lane
    :return: int code of the highway_env action
    """
    ego_position = ego_vehicle[1]
    ego_lane = int(round(ego_vehicle[2] / lane_width))
    ego_speed = ego_vehicle[3]

    other_vehicle = current_vehicle
    other_position = other_vehicle[1]
    other_lane = int(round(other_vehicle[2] / lane_width))
    other_speed = other_vehicle[3]

    same_lane = other_lane == ego_lane
    other_is_in_front = other_position > ego_position
    ego_in_front = ego_position > other_position
    overtake_completed = ego_in_front and same_lane
    distance_between_vehicles = abs(other_position - ego_position)
    ego_is_faster = other_speed - ego_speed < 0

    if other_is_in_front and same_lane:
        if same_lane and 25 > distance_between_vehicles > 7:
            if ego_lane > 0:
                return 0
            else:
                return 2
        elif same_lane and other_speed - ego_speed <= -5 and distance_between_vehicles < 8:
            return 4
        elif same_lane and distance_between_vehicles > 75:
            return 3
    elif overtake_completed:
        return 4
    elif same_lane and not other_is_in_front:
        return 1
    elif distance_between_vehicles > 5 and ego_is_faster and same_lane:
        if other_lane - ego_lane >= 0:
            return 0
        else:
            return 2
    elif distance_between_vehicles > 5 and not ego_is_faster and not same_lane:
        return 3
    elif distance_between_vehicles > 5 and ego_is_faster:
        if other_lane - ego_lane >= 0:
            return 0
        else:
            return 2
    elif not same_lane and not other_is_in_front:
        return 1
    else:
        return 1  # Idle


@thread
def check_clearance(env, obs):
    while True:
        yield sync(request=CHECK_CLEARANCE)
        vehicles = obs
        action = decide_overtake_action(vehicles)
        print("Action: ", action)

        if action in [0, 2]:
            yield sync(request=START_OVERTAKE)
        elif action in [3, 4]:
             yield sync(request=CHECK_CLEARANCE)
        else:
            yield sync(request=ABORT_OVERTAKE)

        obs = env.step(action)
        env.render()


@thread
def perform_overtake(env):
    while True:
        yield sync(waitFor=START_OVERTAKE)
        yield sync(request=PERFORM_OVERTAKE)
        yield sync(request=COMPLETE_OVERTAKE)


@thread
def complete_overtake(env):
    while True:
        yield sync(waitFor=COMPLETE_OVERTAKE)


@thread
def abort_overtake(env):
    while True:
        yield sync(waitFor=ABORT_OVERTAKE)


def main():
    config = {
        "centering_position": [0.5, 0.5],
        "vehicles_count": 4,
        "controlled_vehicles": 1,
        "lanes_count": 3,
        "observation": {
            "type": "Kinematics",
            "vehicles_count": 4,
            "features": ["x", "y", "vx", "vy"],
            "normalize": False,
            "absolute": False,
            "see_behind": True
        },
        "action": {
            "type": "DiscreteMetaAction",
            "longitudinal": True,
            "lateral": True
        },
        "duration": 40,
        "simulation_frequency": 100,
    }

    env = create_env(config)
    obs, info = env.reset()
    bp = BProgram(bthreads=[check_clearance(env), perform_overtake(env), abort_overtake(env), complete_overtake(env)], event_selection_strategy=SimpleEventSelectionStrategy(), listener=PrintBProgramRunnerListener())
    bp.run()

    env.close()


if __name__ == "__main__":
    main()

