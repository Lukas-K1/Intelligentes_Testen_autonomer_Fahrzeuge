import os
import sys
import time

import gymnasium as gym
import register_env
import traci
from bppy import *
from z3 import *

from src.sumo.action_enum import *
from src.sumo.sumo_vehicle import *

# Create symbolic variables that can take any value from the Actions enum (for SMT-based events in BPpy)
v1_action = Const("v1_action", Actions)
v2_action = Const("v2_action", Actions)

v1: SumoControllableVehicle = SumoControllableVehicle(
    "veh_manual_1",
    ["entry", "longEdge", "exit"],
    typeID="manual",
    depart_time=0,
    depart_pos=0.0,
    depart_lane=1,
    depart_speed="avg",
    vehicle_color=[255, 0, 0],  # red
    lane_change_mode=0,
    speed_mode=0,
    vehicle_smt_var=v1_action,
)
v2: SumoControllableVehicle = SumoControllableVehicle(
    "veh_manual_2",
    ["entry", "longEdge", "exit"],
    typeID="manual",
    depart_time=0,
    depart_pos=45.0,
    depart_lane=1,
    depart_speed="avg",
    vehicle_color=[0, 255, 0],  # green
    lane_change_mode=0,
    speed_mode=0,
    vehicle_smt_var=v2_action,
)
controllable_vehicles = [v1, v2]
vut: SumoVehicle = SumoVehicle("vut")

config_path = "../../sumo-maps/autobahn/autobahn.sumocfg"
env = gym.make(
    "SumoEnv-v0", sumo_config_file=config_path, controllable_vehicles=[v1, v2]
)
env.reset()

action_map = {LANE_LEFT: 0, IDLE: 1, LANE_RIGHT: 2, FASTER: 3, SLOWER: 4}


def wait_seconds(seconds):
    step_count_t0 = step_count
    target_step_count = int(seconds / 0.05) + step_count
    while step_count < target_step_count:
        print(f"waited {(step_count - step_count_t0) * 0.05} seconds.")
        yield sync(request=true)


def seconds(steps):
    return steps * 0.05


step_count = 0


def fall_behind(
    behind_vehicle: SumoControllableVehicle,
    in_front_vehicle: SumoVehicle,
    min_distance=25.0,
    max_duration=float("inf"),
):
    global step_count
    step_count_t0 = step_count
    while not behind_vehicle.is_behind_by_x(in_front_vehicle, min_distance):
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
    vehicle_to_change_lane: SumoControllableVehicle, other_vehicle: SumoVehicle
):
    while vehicle_to_change_lane.lane_index() != other_vehicle.lane_index():
        if vehicle_to_change_lane.lane_index() < other_vehicle.lane_index():
            yield sync(request=vehicle_to_change_lane.LANE_LEFT())
        else:
            yield sync(request=vehicle_to_change_lane.LANE_RIGHT())


def close_distance(
    behind_vehicle: SumoControllableVehicle,
    in_front_vehicle: SumoVehicle,
    max_distance=25.0,
    max_duration=float("inf"),
):
    global step_count
    step_count_t0 = step_count
    while behind_vehicle.is_behind_by_x(in_front_vehicle, max_distance):
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


def equalize_speeds(
    controllable_vehicle: SumoControllableVehicle, other_vehicle: SumoVehicle
):
    while (
        abs(controllable_vehicle.speed() - other_vehicle.speed()) <= 0.1
        and abs(controllable_vehicle.speed() - other_vehicle.speed()) <= 0.1
    ):
        if controllable_vehicle.speed() > other_vehicle.speed():
            yield sync(request=controllable_vehicle.SLOWER())
        else:
            yield sync(request=controllable_vehicle.FASTER())
        # yield from wait_seconds(0.1)


def get_behind(behind_vehicle: SumoControllableVehicle, in_front_vehicle: SumoVehicle):
    yield from fall_behind(behind_vehicle, in_front_vehicle)
    yield from change_to_same_lane(behind_vehicle, in_front_vehicle)
    yield from close_distance(behind_vehicle, in_front_vehicle)
    yield from equalize_speeds(behind_vehicle, in_front_vehicle)


def stay_behind(behind_vehicle: SumoControllableVehicle, in_front_vehicle: SumoVehicle):
    while True:
        yield from fall_behind(behind_vehicle, in_front_vehicle, 20.0)
        yield from change_to_same_lane(behind_vehicle, in_front_vehicle)
        yield from close_distance(behind_vehicle, in_front_vehicle, 20.0)
        yield from equalize_speeds(behind_vehicle, in_front_vehicle)
        # yield from wait_seconds(0.1)


@thread
def follow_behind(
    behind_vehicle: SumoControllableVehicle,
    in_front_vehicle: SumoVehicle,
    delay_seconds: float = 0.0,
):
    # " serial: "
    # yield from wait_seconds(delay_seconds)
    yield from get_behind(behind_vehicle, in_front_vehicle)
    yield from stay_behind(behind_vehicle, in_front_vehicle)


@thread
def two_vehicles_follow_vut():
    yield from parallel(follow_behind(v1, vut), follow_behind(v2, v1))


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
        return v1.is_behind_by_x(vut) and v2.is_behind_by_x(v1)  # TODO: Same lane?

    satisfied = yield from await_condition(condition, 10)
    if satisfied:
        print("################ SAT")
    else:
        print("################ UNSAT")


@thread
def abstract_scenario_2():
    # cond 1.
    satisfied = yield from await_condition(
        lambda: v1.is_behind_by_x(vut), local_reward=10.0
    )
    if not satisfied:
        print("################ UNSAT")
        return
    else:
        print("################ COND 1 SAT")
    # cond 2.
    satisfied = yield from await_condition(
        lambda: v1.lane_index() == vut.lane_index(), local_reward=10.0
    )
    if not satisfied:
        print("################ UNSAT")  # -> local_reward = -100.0 ???
        return
    else:
        print("################ COND 2 SAT")
    # cond 3.
    satisfied = yield from await_condition(
        lambda: v2.is_behind_by_x(v1), local_reward=10.0
    )
    if not satisfied:
        print("################ UNSAT")
        return
    else:
        print("################ COND 3 SAT")
    # cond 4.
    satisfied = yield from await_condition(
        lambda: v2.lane_index() == v1.lane_index(), local_reward=10.0
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
    yield sync(waitFor=true)  # needs to be here, otherwise there might be problem w


@thread
def sumo_env_bthread():
    global step_count
    while True:
        # set vehicle_id to one of in this scenario to let it the gui follow that vehicle
        # vut, veh_manual_1, veh_manual_2
        traci.gui.trackVehicle("View #0", "veh_manual_1")
        collisions = traci.simulation.getCollisions()
        if collisions:
            print("Collision detected! Exiting simulation...")
            traci.close()
            raise SystemExit()

        e = yield sync(waitFor=true)

        actions = []
        for vehicle in controllable_vehicles:
            action_vehicle = e.eval(vehicle.vehicle_smt_var)
            if action_vehicle in action_map:
                actions.append(action_map[action_vehicle])
            else:
                actions.append(4)  # default is IDLE
        actions_tuple = tuple(actions)

        obs, reward, truncated, terminated, _ = env.step(actions_tuple)
        print(f"OBSERVATION in step {step_count}: {obs}")
        step_count += 1


if __name__ == "__main__":
    # setup_sumo_connection(config_path)
    # setup_sumo_vehicles()
    # Creating a BProgram with the defined b-threads, SMTEventSelectionStrategy,
    # and a listener to print the selected events
    b_program = BProgram(
        bthreads=[sumo_env_bthread(), two_vehicles_follow_vut(), abstract_scenario_2()],
        event_selection_strategy=SMTEventSelectionStrategy(),
        listener=PrintBProgramRunnerListener(),
    )
    b_program.run()
