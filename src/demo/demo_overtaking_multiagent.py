import gymnasium as gym
import highway_env
from bppy import *
from typing import Dict, Any, List

# BPpy Events
CHECK_CLEARANCE = BEvent("CheckClearance")
START_OVERTAKE = BEvent("StartOvertake")
PERFORM_OVERTAKE = BEvent("PerformOvertake")
COMPLETE_OVERTAKE = BEvent("CompleteOvertake")
ABORT_OVERTAKE = BEvent("AbortOvertake")


def create_env(config: Dict[str, Any]) -> gym.Env:
    env = gym.make('highway-v0', render_mode='rgb_array', config=config)
    env.reset()
    return env


def process_observation(obs: Any) -> List[List[float]]:
    return obs


def decide_action(vehicles: List[List[float]], lane_width: float = 4.0) -> int:
    ego_vehicle = vehicles[0]
    ego_position, ego_lane, ego_speed = ego_vehicle[1], int(round(ego_vehicle[2] / lane_width)), ego_vehicle[3]

    if len(vehicles) == 1:
        return 1

    other_vehicle = vehicles[1]
    other_position, other_lane, other_speed = other_vehicle[1], int(round(other_vehicle[2] / lane_width)), other_vehicle[3]

    same_lane = other_lane == ego_lane
    other_is_in_front = other_position > ego_position
    distance_between_vehicles = abs(other_position - ego_position)
    ego_is_faster = ego_speed > other_speed

    if other_is_in_front:
        if same_lane and distance_between_vehicles < 25:
            return 0 if ego_lane > 0 else 2
        elif not same_lane:
            return 1
        return 4 if other_speed - ego_speed < -5 else 3
    elif same_lane and distance_between_vehicles > 50 and ego_is_faster and not other_is_in_front:
        return 4
    elif not other_is_in_front and distance_between_vehicles > 15 and ego_is_faster:
        if ego_lane - other_lane < 0:
            return 2
        elif ego_lane - other_lane > 0:
            return 0
        return 3
    elif same_lane and distance_between_vehicles > 10:
        return 3  # Speed up to approach leading car
    elif same_lane and distance_between_vehicles > 45 or not same_lane:
        return 1  # Idle
    return 4 if same_lane else (
        0 if other_lane - ego_lane < 0 else 2) if distance_between_vehicles > 5 and ego_is_faster else 1


def decide_passiv(vehicles: List[List[float]], lane_width: float = 4.0) -> int:
    ego_vehicle = vehicles[0]
    ego_position, ego_lane, ego_speed = ego_vehicle[1], int(round(ego_vehicle[2] / lane_width)), ego_vehicle[3]

    if len(vehicles) == 1:
        return 1

    other_vehicle = vehicles[1]
    other_position, other_lane, other_speed = other_vehicle[1], int(round(other_vehicle[2] / lane_width)), other_vehicle[3]

    same_lane = other_lane == ego_lane
    other_is_in_front = other_position > ego_position
    distance_between_vehicles = abs(other_position - ego_position)
    ego_is_faster = ego_speed > other_speed

    if same_lane and other_is_in_front and distance_between_vehicles < 25 and ego_is_faster:
        return 4
    elif not other_is_in_front and distance_between_vehicles > 35 and other_position > 0:
        return 4
    elif not other_is_in_front and distance_between_vehicles > 35:
        return 1
    elif not other_is_in_front and 35 > distance_between_vehicles > 10:
        return 1
    elif other_is_in_front and 35 > distance_between_vehicles > 10:
        return 1
    elif other_is_in_front and distance_between_vehicles > 10 and ego_position < other_position:
        return 3
    return 4


@thread
def check_clearance(obs, env):
    while True:
        yield sync(request=CHECK_CLEARANCE)
        vehicles = process_observation(obs)
        action_0, action_1 = decide_action(vehicles[0]), decide_passiv(vehicles[1])

        if action_0 in [0, 2] and action_1 not in [0, 2, 3] or action_0 == 3 and action_1 in [1, 4]:
            yield sync(request=START_OVERTAKE)
        elif action_0 in [3, 4] and action_1 in [0,1,2,3] or action_0 == 1 and action_1 in [0, 2, 3,4]:
            yield sync(request=CHECK_CLEARANCE)
        else:
            yield sync(request=ABORT_OVERTAKE)

        obs, _, _, _, _ = env.step((action_0, action_1))
        env.render()


@thread
def perform_overtake():
    while True:
        yield sync(waitFor=START_OVERTAKE)
        yield sync(request=PERFORM_OVERTAKE)
        yield sync(request=COMPLETE_OVERTAKE)


@thread
def complete_overtake():
    while True:
        yield sync(waitFor=COMPLETE_OVERTAKE)


@thread
def abort_overtake():
    while True:
        yield sync(waitFor=ABORT_OVERTAKE)


def main():
    config = {
        "centering_position": [0.5, 0.5],
        "vehicles_count": 0,
        "controlled_vehicles": 2,
        "lanes_count": 3,
        "initial_positions": [
            [15, 1, 20],  # (x_position, lane_index, speed)
            [45, 1, 10]   # Another vehicle in a different lane
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

    env = create_env(config)
    obs, _ = env.reset()
    bp = BProgram(bthreads=[check_clearance(obs, env), perform_overtake(), abort_overtake(), complete_overtake()],
                  event_selection_strategy=SimpleEventSelectionStrategy(), listener=PrintBProgramRunnerListener())
    bp.run()

    for _ in range(100):
        bp.run()
        env.render()
        env.step((1, 1))

    env.close()


if __name__ == "__main__":
    main()