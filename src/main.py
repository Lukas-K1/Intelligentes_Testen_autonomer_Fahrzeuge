from typing import Any, Dict, List

import gymnasium as gym
import highway_env as highway
from bppy import *

from observation_wrapper import ObservationWrapper

# BPpy Events
change_lane = BEvent("LANE_CHANGE")
update_position = BEvent("POSITION_UPDATE")
increase_speed = BEvent("SPEED_UP")
new_step = BEvent("STEP")
update_speed = BEvent("SPEED_UPDATE")


def create_env(config: Dict[str, Any]) -> gym.Env:
    env = gym.make('highway-v0', render_mode='rgb_array', config=config)
    env.reset(seed=1)
    return env


def decide_action(env, obs, obs_wrapper: ObservationWrapper, v_id: int, space: float) -> int:
    """
    Decides the action to be taken by the vehicle based on the current observation.
    :param env: the highway environment
    :param obs_wrapper: The observation wrapper containing functionality based on the current observation
    :param v_id: The id of the vehicle
    :param space: The space to be considered for the action
    :return: The action to be taken
    """
    distance = obs_wrapper.get_distance_to_leading_vehicle(v_id)
    right_clear = obs_wrapper.is_right_lane_clear(v_id, space, space)
    left_clear = obs_wrapper.is_left_lane_clear(v_id, space, space)
    same_lane = obs_wrapper.is_in_same_lane(v_id, 1)
    velocity = obs_wrapper.get_velocity(v_id)
    lane = env.unwrapped.road.vehicles[v_id].lane_index
    current_lane = lane[2]
    other_lane_info = env.unwrapped.road.vehicles[1].lane_index[2]
    # highway_env.envs.common.action.DiscreteMetaAction.get_available_actions
    # highway_env.road.road.Road.neighbour_vehicles
    current_vehicle = env.unwrapped.road.vehicles[v_id]
    vehicles = env.unwrapped.road.vehicles
    print(vehicles)
    road_neighbours = env.unwrapped.road.neighbour_vehicles(current_vehicle)

    if distance > 35 and same_lane:
        return 3
    elif 15 > distance > 10 and same_lane and (right_clear or left_clear) and current_lane != 0:
        return 0
    elif 15 > distance > 10 and right_clear and not left_clear and same_lane and current_lane != 3:
        return 2
    elif not right_clear and 15 > distance > 10 and not left_clear and same_lane and (current_lane != 0 or current_lane != 3):
        return 4
    elif not right_clear and 15 > distance > 10 and left_clear and same_lane and current_lane != 0:
        return 0
    elif 35 > distance > 10 and same_lane:
        return 1
    elif distance == 0 and right_clear and current_lane - other_lane_info < 0:
        return 2
    elif distance == 0 and right_clear and current_lane - other_lane_info > 0:
        return 0
    elif not same_lane:
        return 1
    elif distance == 0 and not same_lane and right_clear and not left_clear:
        return 2
    elif distance == 0 and not same_lane and left_clear and not right_clear:
        return 0
    elif velocity < 24 and same_lane:
        return 3
    elif 24 < velocity < 28:
        return 1
    elif distance == 0 and same_lane and 30 > velocity > 25:
        return 4
    elif distance < 12 and same_lane:
        return 4
    return 1


def position_update(distance: float) -> BEvent:
    return BEvent("POSITION_UPDATE", data={"distance_to_vut": distance})


def speed_update(speed: float) -> BEvent:
    return BEvent("SPEED_UPDATE", data={"speed": speed})


def speed_increase(step: int) -> BEvent:
    return BEvent("SPEED_UP", data={"step": step})


def make_step() -> BEvent:
    return BEvent("STEP")


def change_the_lane(step: int) -> BEvent:
    return BEvent("LANE_CHANGE", data={"step": step})


def make_end() -> BEvent:
    return BEvent("END")


@thread
def control_vehicle(env, obs, obs_wrapper):
    step = 0
    while True:
        step += 1
        obs_wrapper.set_observation(obs)
        action = decide_action(env, obs, obs_wrapper, 0, 20)
        print(action)
        if action == 0:
            yield sync(request=change_the_lane(step))
        if action == 1:
            print("Action 1")
        if action == 2:
            yield sync(request=change_the_lane(step))
        if action == 3:
            yield sync(request=speed_increase(step))
        if action == 4:
            print("Action 4")
        obs, _, _, _, _ = env.step((action, 1, 1, 1, 1, 1, 1))
        env.render()
        distance = obs_wrapper.get_distance_to_leading_vehicle(0)
        yield sync(request=position_update(distance))
        velocity = obs_wrapper.get_velocity(0)
        yield sync(request=speed_update(velocity))
        yield sync(request=make_step())


@thread
def control_events():
    print("Control events")


def set_config():
    config = {
        "centering_position": [0.5, 0.5],
        "vehicles_count": 0,
        "controlled_vehicles": 7,
        "lanes_count": 4,
        "initial_positions": [
            [55, 0, 25],
            [105, 0, 20],  #,
            [55, 2, 20],
            [65, 3, 20],  # (x_position, lane_index, speed)
            [45, 2, 20],
            [15, 3, 20],
            [85, 3, 20]
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
    obs, _ = env.reset(seed=0)
    obsw = ObservationWrapper(obs)
    bp = BProgram(bthreads=[control_vehicle(env, obs, obsw)],
                  event_selection_strategy=SimpleEventSelectionStrategy(), listener=PrintBProgramRunnerListener())
    bp.run()

    for _ in range(100):
        obs = env.step((1, 1, 1, 1, 1, 1, 1))
        print(obs)
        env.render()

    env.close()


if __name__ == "__main__":
    main()
