import numpy as np


def is_safe_to_change_lane(vehicle, target_lane, safe_distance, env):
    """
    Checks if the target lane is free of other vehicles within the safe_distance.
    """
    for other in env.unwrapped.road.vehicles:
        if other != vehicle.env_vehicle:
            other_lane = other.lane_index
            if isinstance(other_lane, tuple):
                other_lane = other_lane[2]
            if other_lane == target_lane:
                dx = other.position[0] - vehicle.position()[0]
                dy = other.position[1] - vehicle.position()[1]
                distance = np.sqrt(dx * dx + dy * dy)
                if distance < safe_distance:
                    return False
    return True

def is_safe_to_accelerate(vehicle, safe_distance, env):
    """
    Checks if there are no vehicles in the same lane within the safe_distance.
    """
    for other in env.unwrapped.road.vehicles:
        if other != vehicle.env_vehicle:
            other_lane = other.lane_index
            if isinstance(other_lane, tuple):
                other_lane = other_lane[2]
            if other_lane == vehicle.lane_index():
                dx = other.position[0] - vehicle.position()[0]
                dy = other.position[1] - vehicle.position()[1]
                distance = np.sqrt(dx * dx + dy * dy)
                if distance < safe_distance:
                    return False
    return True


