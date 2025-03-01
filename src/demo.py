import gymnasium as gym
from bppy import *
import highway_env
from matplotlib import pyplot as plt
import time

env = gym.make('highway-v0', render_mode='rgb_array', config={
    "lanes_count": 4, "vehicles_count": 2, "duration": 40, "initial_spacing": 2, "road": "highway"
})
obs = env.reset()


CHANGE_LEFT = Bool("left")
CHANGE_RIGHT = Bool("right")
KEEP_LANE = Bool("keep")
#IDLE = Bool("idling")
was_right = False
was_left = False

@thread
def change_lane_left():
    global was_left
    global was_right
    for i in range(10):
        yield sync(request=CHANGE_LEFT)
        action = map_action_to_highwayenv(CHANGE_LEFT)  # left
        was_left = True
        was_right = False
        print(was_left, was_right)
        obs, reward, done, truncated, info = env.step(action)
        env.render()
        time.sleep(0.1)

        if done or truncated:
            print("Simulation abgeschlossen.")
            obs = env.reset()


@thread
def keep_lane_after_left():
    while True:
        yield sync(waitFor=CHANGE_LEFT)
        yield sync(block=Or(CHANGE_LEFT, CHANGE_RIGHT),waitFor=KEEP_LANE)


@thread
def idle_lane():
    while True:
        yield sync(request=KEEP_LANE)


@thread
def keep_current_lane():
    for i in range(10):
        yield sync(request=KEEP_LANE)
        action = map_action_to_highwayenv(KEEP_LANE)  # left
        obs, reward, done, truncated, info = env.step(action)
        env.render()
        time.sleep(0.1)

        if done or truncated:
            print("Simulation abgeschlossen.")
            obs = env.reset()


@thread
def change_lane_right():
    global was_left
    global was_right
    for i in range(10):
        yield sync(request=CHANGE_RIGHT)
        action = map_action_to_highwayenv(CHANGE_RIGHT)  # left
        was_right = True
        was_left = False
        print(was_left, was_right)
        obs, reward, done, truncated, info = env.step(action)
        env.render()
        time.sleep(0.1)

        if done or truncated:
            print("Simulation abgeschlossen.")
            obs = env.reset()


@thread
def keep_lane_after_right():
    while True:
        yield sync(waitFor=CHANGE_RIGHT)
        yield sync(block=Or(CHANGE_LEFT, CHANGE_RIGHT),waitFor=KEEP_LANE)


@thread
def change_lane_after_keep():
    while True:
        yield sync(waitFor=KEEP_LANE)
        yield sync(waitfor=Or(CHANGE_LEFT, CHANGE_RIGHT),block=KEEP_LANE)


@thread
def change_left_after_keep():
    global was_left
    global was_right
    while True:
        yield sync(waitFor=KEEP_LANE)
        if was_right:
            yield sync(block=KEEP_LANE, waitFor=CHANGE_LEFT)
        else:
            yield sync(block=KEEP_LANE, waitFor=CHANGE_RIGHT)


@thread
def change_right_after_keep():
    global was_left
    global was_right
    while True:
        yield sync(waitFor=KEEP_LANE)
        if was_left:
            yield sync(block=KEEP_LANE, waitFor=CHANGE_RIGHT)
        else:
            yield sync(block=KEEP_LANE, waitFor=CHANGE_LEFT)


@thread
def change_right_after_keep():
    while True:
        yield sync(waitFor=KEEP_LANE)
        yield sync(block=Or(KEEP_LANE, CHANGE_LEFT),waitFor=CHANGE_RIGHT)



@thread
def regulator():
    e = yield sync(waitFor=true)
    while True:
        if e.eval(CHANGE_LEFT):
            e = yield sync(block=CHANGE_LEFT, waitFor=true)
            #action = 0 # left
            print("Change left")
            action = map_action_to_highwayenv(CHANGE_LEFT) # left
        elif e.eval(CHANGE_RIGHT):
            e = yield sync(block=CHANGE_RIGHT, waitFor=true)
            print("Change right")
            #action = 2 # right
            action = map_action_to_highwayenv(CHANGE_RIGHT) # right
        elif e.eval(KEEP_LANE):# TODO WIP does not get executed
            #action = 1 # idle
            e = yield sync(block=KEEP_LANE, waitFor=true)
            print("Keep lane")
            action = map_action_to_highwayenv(KEEP_LANE) # idle
        else:
            e = yield sync(request=KEEP_LANE)
            print("Idle")
            action = map_action_to_highwayenv(KEEP_LANE) # idle

        obs, reward, done, truncated, info = env.step(action)
        env.render()
        time.sleep(0.1)

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
    elif event == KEEP_LANE:
        return 1
    return 1  # idle


if __name__ == '__main__':
    program = BProgram(bthreads=[change_lane_left(), change_lane_right(), keep_current_lane(), keep_lane_after_left(),keep_lane_after_right(),change_lane_after_keep()],
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
                obs = env.reset()

        except Exception as e:
            print(f"Fehler während der Programmausführung: {e}")
            break

    plt.imshow(env.render())
    plt.show()