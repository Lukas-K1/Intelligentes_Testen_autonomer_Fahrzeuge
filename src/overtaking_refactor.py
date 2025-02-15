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


def decide_action(vehicles: List[List[float]], lane_width: float = 4.0) -> int:
    ego_vehicle = vehicles[0]
    ego_position = ego_vehicle[1]
    ego_lane = int(round(ego_vehicle[2] / lane_width))
    ego_speed = ego_vehicle[3]

    # print("ego: ", ego_lane, ego_position, ego_speed)

    if len(vehicles) == 1:
        return 1

    other_vehicle = vehicles[1]
    other_position = other_vehicle[1]
    other_lane = int(round(other_vehicle[2] / lane_width))
    other_speed = other_vehicle[3]

    # print("other: ", other_lane, other_position, other_speed)

    same_lane = other_lane == ego_lane
    other_is_in_front = other_position > ego_position
    distance_between_vehicles = abs(other_position - ego_position)
    ego_is_faster = other_speed - ego_speed < 0

    if other_is_in_front:
        if same_lane and distance_between_vehicles < 25:
            if ego_lane > 0:
                return 0  # Nach links wechseln
            else:
                return 2  # Nach rechts wechseln
        elif other_speed - ego_speed < -5:
            return 4  # bremsen
        else:
            return 3  # beschleunigen
    elif same_lane:
        return 4  # bremsen
    elif distance_between_vehicles > 5 and ego_is_faster:
        if other_lane - ego_lane < 0:
            return 0  # Nach links wechseln
        else:
            return 2  # Nach rechts wechseln

    return 1  # Idle


def decide_passiv(vehicles: List[List[float]], lane_width: float = 4.0) -> int:
    ego_vehicle = vehicles[[0]]
    ego_position = ego_vehicle[1]
    ego_lane = int(round(ego_vehicle[2] / lane_width))
    ego_speed = ego_vehicle[3]

    if len(vehicles) == 1:
        return 1

    other_vehicle = vehicles[1]
    other_position = other_vehicle[1]
    other_lane = int(round(other_vehicle[2] / lane_width))
    other_speed = other_vehicle[3]

    same_lane = other_lane == ego_lane
    other_is_in_front = other_position > ego_position
    distance_between_vehicles = abs(other_position - ego_position)
    ego_is_faster = other_speed - ego_speed < 1

    if same_lane and other_is_in_front and distance_between_vehicles < 25 and ego_is_faster:
        return 4

    return 1


@thread
def check_clearance(obs, env):
    while True:
        yield sync(request=CHECK_CLEARANCE)
        #obs, reward, done, terminate, info = env.step((1, 1))
        vehicles = obs
        #actions = decide_overtake_action(vehicles)
        action_0 = decide_action(vehicles)
        action_1 = decide_passiv(vehicles)
        print("Actions: ", action_0, action_1)

        if action_0 in [0, 2] or action_1 in [0, 2]:
            yield sync(request=START_OVERTAKE)
            obs = env.step((action_0, action_1))
            env.render()
        elif action_0 in [3, 4] or action_1 in [3, 4]:
            yield sync(request=CHECK_CLEARANCE)
            obs = env.step((action_0, action_1))
            env.render()
        else:
            yield sync(request=ABORT_OVERTAKE)
            obs = env.step((action_0, action_1))
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
                "target_speeds": [0, 5, 10, 15, 20, 25, 30],
                # Die dikreten Geschwindigkeiten, die das Auto annehmen kann
            },
        },
    }

    env = create_env(config)
    obs, info = env.reset(seed=1)
    bp = BProgram(bthreads=[check_clearance(obs, env), perform_overtake(), abort_overtake(), complete_overtake()], event_selection_strategy=SimpleEventSelectionStrategy(), listener=PrintBProgramRunnerListener())
    bp.run()

    for _ in range(100):
        # obs, info = env.reset(seed=1)
        # bp = BProgram(bthreads=[check_clearance(obs, env), perform_overtake(), abort_overtake(), complete_overtake()],
        #               event_selection_strategy=SimpleEventSelectionStrategy(), listener=PrintBProgramRunnerListener())
        bp.run()
        env.render()
        env.step((1, 1))

    env.close()


if __name__ == "__main__":
    main()
