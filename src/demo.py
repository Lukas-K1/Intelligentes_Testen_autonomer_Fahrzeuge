import gymnasium
from bppy import *
import highway_env
from matplotlib import pyplot as plt

# Define the system
env = gymnasium.make('highway-v0', render_mode='rgb_array', config={"lanes_count": 4, "vehicles_count": 2, "duration": 40, "initial_spacing": 2, "road": "highway"})
obs = env.reset()

# Define the specification
CHANGE_LEFT = Bool("left")
CHANGE_RIGHT = Bool("right")


@thread
def change_lane_left():
    for i in range(10):
        yield sync(request=CHANGE_LEFT)


@thread
def change_lane_right():
    for i in range(10):
        yield sync(request=CHANGE_RIGHT)


@thread
def regulator():
    e = yield sync(waitFor=true)
    while True:
        if e.eval(CHANGE_LEFT):
            e = yield sync(block=CHANGE_LEFT, waitFor=true)
        else:
            e = yield sync(block=CHANGE_RIGHT, waitFor=true)


def map_action_to_highwayenv(event):
    if event == CHANGE_LEFT:
        return 2  # Spurwechsel links
    elif event == CHANGE_RIGHT:
        return 3  # Spurwechsel rechts
    return 0


def collision_detected(environment):
    for vehicle in environment.metadata["vehicle_count"]:
        if vehicle.crashed:
            return True
    return False


def init_bpprogram():
    return BProgram(bthreads=[change_lane_left(), change_lane_right(), regulator()],
                          event_selection_strategy=SMTEventSelectionStrategy(), listener=BProgramRunnerListener())


if __name__ == '__main__':
    event_list = [CHANGE_LEFT, CHANGE_RIGHT]
    logger = EventLogger()

    program = init_bpprogram()
    done = False
    counter = 0
    while not done:
        program.run()
        ev = program.
        action = map_action_to_highwayenv(ev)
        obs = env.step(action)
        if counter == 8:
            done = True
        done = done# or collision_detected(env)
        counter += 1
        env.render()
        plt.imshow(env.render())
        plt.show()

# plt.imshow(env.render())
# plt.show()
