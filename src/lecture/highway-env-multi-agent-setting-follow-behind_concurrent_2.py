import gymnasium
import highway_env
import numpy as np
from bppy import *
from highway_env.vehicle.controller import MDPVehicle
from matplotlib import pyplot as plt
from z3 import *

simulation_frequency = 30
policy_frequency = 5

env = gymnasium.make(
    "highway-v0",
    render_mode="rgb_array",
    config={
        "controlled_vehicles": 2,  # Two controlled vehicles
        "vehicles_count": 1,  # A single other vehicle, for the sake of visualisation
        "simulation_frequency": simulation_frequency,  # Increase this to 50 or more for smoother playback
        "policy_frequency": policy_frequency,  # Reduce to slow down decision-making
    },
)
env.unwrapped.config.update(
    {
        "action": {
            "type": "MultiAgentAction",
            "action_config": {
                "type": "DiscreteMetaAction",
            },
        },
        "observation": {
            "type": "MultiAgentObservation",
            "observation_config": {
                "type": "Kinematics",
            },
        },
        "lanes_count": 3,
        "screen_height": 150,
        "screen_width": 1200,
    }
)
env.reset(seed=0)


### Z3

# Define an enumeration sort (enum type) with the possible actions (for SMT-based events in BPpy)
Actions, (LANE_LEFT, IDLE, LANE_RIGHT, FASTER, SLOWER) = EnumSort(
    "Actions", ["LANE_LEFT", "IDLE", "LANE_RIGHT", "FASTER", "SLOWER"]
)

# Create symbolic variables that can take any value from the Actions enum (for SMT-based events in BPpy)
v1_action = Const("v1_action", Actions)
v2_action = Const("v2_action", Actions)


class Vehicle:

    # Represents/Wraps an uncontrollable vehicle
    # Adds functions like speed and lane_index that delegate to function calls on the vehicles in the simulation env.
    # Adds convenience functions for conditions like is_ahead_of.

    def __init__(self, v_index, env, name):
        self.v_index = v_index
        self.env = env
        self.env_vehicle = env.unwrapped.road.vehicles[v_index]
        self.name = name

    def delta_pos(self, other_vehicle):
        return self.env_vehicle.position - other_vehicle.env_vehicle.position

    def delta_x_pos(self, other_vehicle):
        return self.env_vehicle.position[0] - other_vehicle.env_vehicle.position[0]

    def is_ahead_of(self, other_vehicle, more_than=0.0):
        # TODO: Only works when traveling in x-direction, needs to incorporate heading etc.
        return (
            self.env_vehicle.position[0] - more_than
            > other_vehicle.env_vehicle.position[0]
        )

    def is_behind(self, other_vehicle, more_than=0.0):
        # TODO: Only works when traveling in x-direction, needs to incorporate heading etc.
        return (
            self.env_vehicle.position[0] + more_than
            < other_vehicle.env_vehicle.position[0]
        )

    def speed(self):
        return self.env_vehicle.speed

    def target_speed(self):
        return self.env_vehicle.target_speed

    def velocity(self):
        return self.env_vehicle.velocity

    def lane_index(self):
        return self.env_vehicle.lane_index


class ControllableVehicle(Vehicle):

    # An extension of the Vehicle for controllable vehicles
    # mainly adds convenience functions for obtaining the conditions
    # that represent the actions that we want to request for that vehicle

    def __init__(self, v_index, env, vehicle_smt_var, name):
        super().__init__(v_index, env, name)  # Call parent constructor
        self.vehicle_smt_var = vehicle_smt_var

    def LANE_LEFT(self):
        return self.vehicle_smt_var == LANE_LEFT

    def IDLE(self):
        return self.vehicle_smt_var == IDLE

    def LANE_RIGHT(self):
        return self.vehicle_smt_var == LANE_RIGHT

    def FASTER(self):
        return self.vehicle_smt_var == FASTER

    def SLOWER(self):
        return self.vehicle_smt_var == SLOWER


action_map = {LANE_LEFT: 0, IDLE: 1, LANE_RIGHT: 2, FASTER: 3, SLOWER: 4}


# Vehicles inde 0 and 2 are controlled vehicles:
v1_red = ControllableVehicle(0, env, v1_action, "v1")
v2_green = ControllableVehicle(2, env, v2_action, "v1")
vut = Vehicle(1, env, "vut")
controllable_vehicles = [v1_red, v2_green]

for vehicle in env.unwrapped.road.vehicles:
    if isinstance(vehicle, MDPVehicle):
        # This vehicle is a controllable vehicle
        vehicle.target_speeds = np.linspace(-5, 45, 50)

step_count = 0


def wait_seconds(seconds):
    step_count_t0 = step_count
    target_step_count = seconds * simulation_frequency + step_count
    while step_count < target_step_count:
        print(f"waited {(step_count - step_count_t0) / simulation_frequency} seconds.")
        yield sync(request=true)


def seconds(steps):
    return steps / simulation_frequency


@thread
def highway_env_bthread():  # requesting cold=true three times
    global step_count
    while True:
        e = yield sync(waitFor=true)

        # from the event extract the actions for all vehicles.
        # Should there be no action for a vehicle, pick the IDLE action.
        actions = []
        for vehicle in controllable_vehicles:
            action_vehicle = e.eval(vehicle.vehicle_smt_var)
            if action_vehicle in action_map:
                actions.append(action_map[action_vehicle])
            else:
                actions.append(
                    1
                )  # Default: IDLE, equivalent to actions.append(action_map["IDLE"])
        actions_tuple = tuple(actions)

        obs, reward, done, truncated, info = env.step(
            actions_tuple
        )  # (1, 2) -- v1="IDLE" v2="LANE_RIGHT"
        step_count += 1

        # Use `env.unwrapped.road` to access the vehicles
        # for vehicle in env.unwrapped.road.vehicles:
        #     position = tuple(f"{x:.2f}" for x in vehicle.position)  # Format x, y positions
        #     velocity = tuple(f"{v:.2f}" for v in vehicle.velocity)  # Format vx, vy speeds
        #     print(f"  Position: {position}")  # [x, y] with 2 decimal places
        #     print(f"  Velocity: {velocity}")  # [vx, vy] with 2 decimal places
        #     print(f"  Lane: {vehicle.lane_index}")  # Lane index remains as-is
        #     print("--------------------------")
        # print("==========================")

        env.render()


def fall_behind(
    behind_vehicle: ControllableVehicle,
    in_front_vehicle: Vehicle,
    min_distance=25.0,
    max_duration=float("inf"),
):
    global step_count
    step_count_t0 = step_count
    while not behind_vehicle.is_behind(in_front_vehicle, min_distance):
        # behind_vehicle must slow down, but only until it is 2.0 slower than in_front_vehicle
        if behind_vehicle.speed() + 2.0 > in_front_vehicle.speed():
            yield sync(request=v1_action == SLOWER)
            yield sync(request=behind_vehicle.SLOWER())
        elif behind_vehicle.speed() - 2.0 < in_front_vehicle.speed():
            yield sync(request=behind_vehicle.FASTER())
        else:
            yield sync(request=behind_vehicle.IDLE())
        if seconds(step_count - step_count_t0) >= max_duration:
            print("TIMED INTERRUPT")
            break


def change_to_same_lane(
    vehicle_to_change_lane: ControllableVehicle, other_vehicle: Vehicle
):
    while vehicle_to_change_lane.lane_index() != other_vehicle.lane_index():
        if vehicle_to_change_lane.lane_index() > other_vehicle.lane_index():
            yield sync(request=vehicle_to_change_lane.LANE_LEFT())
        else:
            yield sync(request=vehicle_to_change_lane.LANE_RIGHT())


def close_distance(
    behind_vehicle: ControllableVehicle,
    in_front_vehicle: Vehicle,
    max_distance=25.0,
    max_duration=float("inf"),
):
    global step_count
    step_count_t0 = step_count
    while behind_vehicle.is_behind(in_front_vehicle, max_distance):
        # behind_vehicle must speed up down, but only until it is 2.0 faster than in_front_vehicle
        if behind_vehicle.speed() - 2.0 < in_front_vehicle.speed():
            yield sync(request=behind_vehicle.FASTER())
        elif behind_vehicle.speed() + 2.0 > in_front_vehicle.speed():
            yield sync(request=behind_vehicle.SLOWER())
        else:
            yield sync(request=behind_vehicle.IDLE())
        if seconds(step_count - step_count_t0) >= max_duration:
            print("TIMED INTERRUPT")
            break


def equalize_speeds(controllable_vehicle: ControllableVehicle, other_vehicle: Vehicle):
    while (
        abs(controllable_vehicle.target_speed() - other_vehicle.target_speed()) <= 0.1
        and abs(controllable_vehicle.speed() - other_vehicle.speed()) <= 0.1
    ):
        if controllable_vehicle.target_speed() > other_vehicle.target_speed():
            yield sync(request=controllable_vehicle.SLOWER())
        else:
            yield sync(request=controllable_vehicle.FASTER())
        # yield from wait_seconds(0.1)


def get_behind(behind_vehicle: ControllableVehicle, in_front_vehicle: Vehicle):
    yield from fall_behind(behind_vehicle, in_front_vehicle)
    yield from change_to_same_lane(behind_vehicle, in_front_vehicle)
    yield from close_distance(behind_vehicle, in_front_vehicle)
    yield from equalize_speeds(behind_vehicle, in_front_vehicle)


def stay_behind(behind_vehicle: ControllableVehicle, in_front_vehicle: Vehicle):
    while True:
        yield from fall_behind(behind_vehicle, in_front_vehicle, 25.0)
        yield from change_to_same_lane(behind_vehicle, in_front_vehicle)
        yield from close_distance(behind_vehicle, in_front_vehicle, 30.0)
        yield from equalize_speeds(behind_vehicle, in_front_vehicle)
        yield from wait_seconds(0.1)


@thread
def follow_behind(
    behind_vehicle: ControllableVehicle,
    in_front_vehicle: Vehicle,
    delay_seconds: float = 0.0,
):
    # " serial: "
    yield from wait_seconds(delay_seconds)
    yield from get_behind(behind_vehicle, in_front_vehicle)
    yield from stay_behind(behind_vehicle, in_front_vehicle)


@thread
def two_vehicles_follow_vut():
    yield from parallel(follow_behind(v1_red, vut), follow_behind(v2_green, v1_red))


def await_condition(
    condition_function, deadline_seconds=float("inf"), local_reward=0.0
) -> Bool:
    global step_count
    step_count_t0 = step_count
    while seconds(step_count - step_count_t0) <= deadline_seconds:
        if condition_function():
            return true
        yield sync(waitFor=true, localReward=local_reward)
        print(
            f" +++  waited {seconds(step_count-step_count_t0)} seconds for condition."
        )
    return false


# abstract scenario:
#   - some sequence or control flow of conditions or events that we wait for / monitor
#   - or some composition of other scenarios.
@thread
def abstract_scenario_two_vehicles_follow_vut():
    def condition():
        return v1_red.is_behind(vut) and v2_green.is_behind(v1_red)  # TODO: Same lane?

    satisfied = yield from await_condition(condition, 10)
    if satisfied:
        print("################ SAT")
    else:
        print("################ UNSAT")


@thread
def abstract_scenario_2():
    # cond 1.
    satisfied = yield from await_condition(
        lambda: v1_red.is_behind(vut), local_reward=10.0
    )
    if not satisfied:
        print("################ UNSAT")
        return
    else:
        print("################ COND 1 SAT")
    # cond 2.
    satisfied = yield from await_condition(
        lambda: v1_red.lane_index() == vut.lane_index(), local_reward=10.0
    )
    if not satisfied:
        print("################ UNSAT")  # -> local_reward = -100.0 ???
        return
    else:
        print("################ COND 2 SAT")
    # cond 3.
    satisfied = yield from await_condition(
        lambda: v2_green.is_behind(v1_red), local_reward=10.0
    )
    if not satisfied:
        print("################ UNSAT")
        return
    else:
        print("################ COND 3 SAT")
    # cond 4.
    satisfied = yield from await_condition(
        lambda: v2_green.lane_index() == v1_red.lane_index(), local_reward=10.0
    )
    if not satisfied:
        print("################ UNSAT")
        return
    else:
        print("################ COND 4 SAT")
    print("################ SAT")


def parallel(*bthreads):
    for bt in bthreads:
        b_program.add_bthread(bt)
    yield sync(
        waitFor=true
    )  # needs to be here, otherwise there might be problem with no b_thread syncing anything.


if __name__ == "__main__":
    # Creating a BProgram with the defined b-threads, SMTEventSelectionStrategy,
    # and a listener to print the selected events
    b_program = BProgram(
        bthreads=[
            highway_env_bthread(),
            two_vehicles_follow_vut(),  # concrete scenario
            # abstract_scenario_two_vehicles_follow_vut()  # abstract scenario
            abstract_scenario_2(),
        ],
        event_selection_strategy=SMTEventSelectionStrategy(),
        listener=PrintBProgramRunnerListener(),
    )
    b_program.run()
