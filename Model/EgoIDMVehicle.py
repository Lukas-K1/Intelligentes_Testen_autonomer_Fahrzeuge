import time

import gymnasium
import highway_env
from highway_env.vehicle.behavior import IDMVehicle

config={
    "observation": {
        "type": "Kinematics"
    },
    "action": {
        "type": "DiscreteMetaAction",
    },
    "lanes_count": 4,
    "vehicles_count": 10,
    "controlled_vehicles": 1,
    "duration": 500,  # [s]
    "initial_spacing": 2,
    "collision_reward": -1,
    "reward_speed_range": [20, 30],
    "simulation_frequency": 15,
    "policy_frequency": 1,
    "other_vehicles_type": "highway_env.vehicle.behavior.IDMVehicle",
    "screen_width": 600,
    "screen_height": 150,
    "centering_position": [0.3, 0.5],
    "scaling": 5.5,
    "show_trajectories": False,
    "render_agent": True,
    "offscreen_rendering": False
}

env = gymnasium.make('highway-v0', render_mode='rgb_array', config=config)
# Start the simulation
done = truncated = False
for _ in range(10):
    obs, info = env.reset()

    # Get the ego vehicle
    ego = env.unwrapped.vehicle

    # Convert ego vehicle to IDMVehicle
    idm_ego = IDMVehicle.create_from(ego)
    idm_ego.target_speed = 30  # [m/s]
    idm_ego.DISTANCE_WANTED = 7 # [m]
    idm_ego.TIME_WANTED = 0.5 # [s]
    idm_ego.LANE_CHANGE_MIN_ACC_GAIN = 0.2 # [m/s2]
    idm_ego.LANE_CHANGE_MAX_BRAKING_IMPOSED = 0.2 # [m/s2]

    # Replace the ego vehicle in the environment
    env.unwrapped.vehicle = idm_ego
    env.unwrapped.controlled_vehicles[0] = idm_ego
    env.unwrapped.road.vehicles[env.unwrapped.road.vehicles.index(ego)] = idm_ego

    # Start the simulation
    done = truncated = False
    while not (done or truncated):
        # Let IDM control the vehicle
        idm_ego.act()
        # Step the environment with a dummy action (IDM will override it)
        obs, reward, done, truncated, info = env.step(action=1)
        print(idm_ego.speed)
        if idm_ego.speed > 29:
            done = True
        # Update the display
        env.render()
        #time.sleep(0.1)
# Close the environment
env.close()
