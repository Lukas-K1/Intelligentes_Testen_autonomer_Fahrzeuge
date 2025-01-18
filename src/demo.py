import gymnasium as gym
from bppy import *
import highway_env
from matplotlib import pyplot as plt


env = gym.make('highway-v0', render_mode='rgb_array', config={
    "lanes_count": 4, "vehicles_count": 2, "duration": 40, "initial_spacing": 2, "road": "highway"
})
obs = env.reset()


CHANGE_LEFT = Bool("left")
CHANGE_RIGHT = Bool("right")


@thread
def change_lane_left():
    while True:
        yield sync(request=CHANGE_LEFT)


@thread
def change_lane_right():
    while True:
        yield sync(request=CHANGE_RIGHT)


@thread
def regulator():
    e = yield sync(waitFor=true)
    while True:
        if e.eval(CHANGE_LEFT):
            e = yield sync(block=CHANGE_LEFT, waitFor=true)
            action = 0 # left
        elif e.eval(CHANGE_RIGHT):
            e = yield sync(block=CHANGE_RIGHT, waitFor=true)
            action = 2 # right
        else:
            action = 1 # idle
        obs, reward, done, truncated, info = env.step(action)
        env.render()
        # Überprüfe, ob die Simulation zu Ende ist
        if done or truncated:
            print("Simulation abgeschlossen.")
            obs = env.reset()


# collision detection
#def collision_detected(environment):
#     for vehicle in environment.metadata["vehicle_count"]:
#         if vehicle.crashed:
#             return True
#     return False


# mapping to highwayenv action
def map_action_to_highwayenv(event):
    if event == CHANGE_LEFT:
        return 0  # change lane left
    elif event == CHANGE_RIGHT:
        return 2  # change lane right
    return 1  # idle


if __name__ == '__main__':
    program = BProgram(bthreads=[change_lane_left(), change_lane_right(), regulator()],
                       event_selection_strategy=SMTEventSelectionStrategy(), listener=PrintBProgramRunnerListener())

    done = False
    initial_action = 1
    obs, reward, done, truncated, info = env.step(initial_action)
    env.render()
    while not done:
        try:
            program.run()
            #selected_event = program.next_event()

            #action = map_action_to_highwayenv(selected_event)

            #obs, reward, done, truncated, info = env.step(action)

            env.render()

            if done or truncated:
                print("Simulation abgeschlossen. Reset der Umgebung.")
                obs = env.reset()  # Umgebung zurücksetzen

        except Exception as e:
            print(f"Fehler während der Programmausführung: {e}")
            break

    # Zeige die finale Visualisierung der Simulation
    plt.imshow(env.render())
    plt.show()