import gymnasium as gym

import highway_env as highway

import numpy as np

def kinematics_observation():
    return {
        "type": "Kinematics",
        "features": ["presence", "x", "y", "vx", "vy", "heading", "cos_h", "sin_h", "cos_d", "sin_d", "long_off",
                     "lat_off", "ang_off"],
        "absolute": False,
        "order": "sorted",
        "see_behind": True # damit auch die Fahrzeuge hinter einem Fahrzeug mit observiert werden
    }

def occupancygrid_observation():
    return {
        "type": "OccupancyGrid",
        "features": ["on_road"],  # on_road gibt an, ob ein Fahrzeug auf der Straße ist bzw. ob sich eine Straße um das Fahrzeug befindet
        "features_range": {
            "x": [-100, 100],
            "y": [-100, 100],
            "vx": [-20, 20],
            "vy": [-20, 20]
        },
        "grid_size": [[-9, 9], [-9, 9]],
        "grid_step": [6, 6],
        "absolute": False
    }

def grayscale_observation():
    return {
        "type": "GrayscaleObservation",
        "observation_shape": (128, 64),
        "stack_size": 4,
        "weights": [0.2989, 0.5870, 0.1140],  # weights for RGB conversion
        "scaling": 1.75
    }

def time_to_collision_observation():
    return {
        "type": "TimeToCollision",
        "horizon": 20,
        }

def multiagent_observation():
    return { "type": "MultiAgentObservation",
    "observation_config":
        #kinematics_observation()
        occupancygrid_observation()
        #time_to_collision_observation()
        #grayscale_observation()
    }

env = gym.make('highway-v0', render_mode='rgb_array', config={
    "lanes_count": 4,
    "controlled_vehicles": 3,
    "vehicles_count": 0,
    "duration": 40,
    "road": "highway",
    "initial_lane_id": 2,
    "ego_spacing": 0.5,
    "simulation_frequency": 100,
    "observation":
        multiagent_observation()
        # kinematics_observation()
        # occupancygrid_observation()
        # grayscale_observation()
    ,
    "action": {
        "type": "MultiAgentAction",
        "action_config": {
            "type": "DiscreteMetaAction",
        }
      },
    "width": 100,
    "screen_width": 1024,
    "screen_height": 720
})

obs = env.reset()

"""
The first agent overtakes the second agent.

Returns:
    int: The action value for the first agent
"""
def calc_Action_1(step):
    if step == 1:
        return 0
    elif step == 2:
        return 3
    elif step == 7:
        return 2
    if step == 9:
        return 4
    else:
        return 1

"""
Returns the action for vehicle 2, which only idles
"""
def calc_Action_2(step):
    return 1

"""
The third agent changes his lane to the right and then speeds up, so that he is not the last one.
"""
def calc_Action_3(step):
    if step == 0:
        return 2
    if step == 1:
        return 4
    if step == 4 or step == 6:
        return 3
    else:
        return 1

def action_name(action) -> str:
    if action == 0:
        return "LANE_LEFT"
    elif action == 1:
        return "IDLE"
    elif action == 2:
        return "LANE_RIGHT"
    elif action == 3:
        return "FASTER"
    elif action == 4:
        return "SLOWER"

if __name__ == '__main__':
    for i in range(15):
        action1 = calc_Action_1(i)
        action2 = calc_Action_2(i)
        action3 = calc_Action_3(i)
        print("Action 1: ", action_name(action1))
        print("Action 2: ", action_name(action2))
        print("Action 3: ", action_name(action3))

        obs, reward, done, truncated, info = env.step((action1, action2, action3))

        controlled_vehicle_count = 0
        for obs_i in zip(obs):
            with np.printoptions(precision=3, suppress=True):
                print("\033[34mControlled vehicle \033[0m", controlled_vehicle_count)
                controlled_vehicle_count += 1
                print(obs_i)

        # for grayscale observation example for the first vehicle in a multi agent setting with 3 vehicles
        """
        fig, axes = plt.subplots(ncols=4, figsize=(12, 5))
        for i, ax in enumerate(axes.flat):
            ax.imshow(obs[0][i, ...].T, cmap=plt.get_cmap('gray'))
        plt.show()
        """

        env.render()