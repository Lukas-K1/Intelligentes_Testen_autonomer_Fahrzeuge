import gymnasium as gym

import highway_env as highway

def kinematics_observation():
    return {
        "type": "Kinematics",
        "features": ["cos_d", "sin_d"],
        "absolute": False,
        "order": "sorted",
        "see_behind": True # damit auch die Fahrzeuge hinter einem Fahrzeug mit observiert werden
    }

def occupancygrid_observation():
    return {
        "type": "OccupancyGrid",
        "features": ["presence", "x", "y", "vx", "vy", "cos_h", "sin_h"],
        "features_range": {
            "x": [-100, 100],
            "y": [-100, 100],
            "vx": [-20, 20],
            "vy": [-20, 20]
        },
        "grid_size": [[-27.5, 27.5], [-27.5, 27.5]],
        "grid_step": [5, 5],
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

# wenn keine Spur mehr vorhanden ist, neben der aktuell befahrenen Spur, dann wird dies als 1 interpretiert
def time_to_collision_observation():
    return {
        "type": "TimeToCollision",
        "horizon": 10,
        }

def multiagent_observation():
    return { "type": "MultiAgentObservation",
    "observation_config":
        kinematics_observation()
        #occupancygrid_observation()
        #time_to_collision_observation()
        #grayscale_observation()
    }

env = gym.make('roundabout-v0', render_mode='rgb_array', config={

    "simulation_frequency": 100,
    "observation":
        # multiagent_observation()
        # kinematics_observation()
        occupancygrid_observation()
        # grayscale_observation()
    ,
    "screen_width": 1024,
    "screen_height": 720
})

obs = env.reset()

def action_name(action) -> String:
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
        obs, reward, done, truncated, info = env.step((1))
        print(obs)

        # for grayscale observation example for the first vehicle in a multi agent setting with 3 vehicles
        """
        fig, axes = plt.subplots(ncols=4, figsize=(12, 5))
        for i, ax in enumerate(axes.flat):
            ax.imshow(obs[0][i, ...].T, cmap=plt.get_cmap('gray'))
        plt.show()
        """
        env.render()