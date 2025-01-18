import gym
import highway_env
from bppy import *
from matplotlib import pyplot as plt


env = gymnasium.make('highway-v0', render_mode='rgb_array',
                     config={"lanes_count": 4, "vehicles_count": 2, "duration": 40, "initial_spacing": 2,
                             "road": "highway"})
obs = env.reset()


CHANGE_LEFT = Bool("left")
CHANGE_RIGHT = Bool("right")


@thread
def change_lane_left():
    for i in range(100):
        yield sync(request=CHANGE_LEFT)


@thread
def change_lane_right():
    for i in range(100):
        yield sync(request=CHANGE_RIGHT)


@thread
def regulator():
    e = yield sync(waitFor=true)
    while True:
        if e.eval(CHANGE_LEFT):
            e = yield sync(block=CHANGE_LEFT, waitFor=true)
        else:
            e = yield sync(block=CHANGE_RIGHT, waitFor=true)


def map_action_to_highwayenv(event: Bool):
    if event == CHANGE_LEFT:
        return 0  # Spurwechsel links
    elif event == CHANGE_RIGHT:
        return 2  # Spurwechsel rechts
    return 1 # idle


if __name__ == '__main__':	
    program = BProgram(bthreads=[change_lane_left(), change_lane_right(), regulator()],
                    event_selection_strategy=SMTEventSelectionStrategy(), listener=PrintBProgramRunnerListener())


    done = False
    while not done:
        bp_program.run()
        event = bp_program.next_event()
        action = map_action_to_highwayenv(event)
        obs, reward, done, info = env.step(action)
        env.render()
        plt.imshow(env.render())
        plt.show()

env.close()
