import gymnasium as gym
import highway_env
import time
from typing import List, Dict, Any

from highway_env.vehicle.behavior import IDMVehicle


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
    ego_vehicle = vehicles[0]
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


def run_simulation(env: gym.Env, steps: int = 100) -> None:
    # Start the simulation
    for _ in range(10):
        obs, info = env.reset()

        # Get the ego vehicle
        ego = env.unwrapped.vehicle

        # Convert ego vehicle to IDMVehicle
        idm_ego = IDMVehicle.create_from(ego)
        idm_ego.target_speed = 5  # [m/s]
        idm_ego.DISTANCE_WANTED = 7  # [m]
        idm_ego.TIME_WANTED = 0.5  # [s]
        idm_ego.LANE_CHANGE_MIN_ACC_GAIN = 0.2  # [m/s2]
        idm_ego.LANE_CHANGE_MAX_BRAKING_IMPOSED = 0.2  # [m/s2]

        # Replace the ego vehicle in the environment
        env.unwrapped.vehicle = idm_ego
        env.unwrapped.controlled_vehicles[0] = idm_ego
        env.unwrapped.road.vehicles[env.unwrapped.road.vehicles.index(ego)] = idm_ego

        # Start the simulation
        done = truncated = False
        while not (done):
            # Let IDM control the vehicle
            idm_ego.act()
            active = decide_action(obs[1])
            # Step the environment with a dummy action (IDM will override it)
            obs, reward, done, truncated, info = env.step((1, active))
            print(idm_ego.speed)
            #if idm_ego.speed > 29:
                #done = True
            # Update the display
            env.render()
            time.sleep(0.1)
    # Close the environment
    env.close()


if __name__ == "__main__":
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
    run_simulation(env)