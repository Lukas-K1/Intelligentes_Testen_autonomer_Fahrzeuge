import os
import sys
import time

import traci
from bppy import *
from z3 import *

from src.sumo.action_enum import *
from src.sumo.sumo_vehicle import *

# Create symbolic variables that can take any value from the Actions enum (for SMT-based events in BPpy)
v1_action = Const('v1_action', Actions)
v2_action = Const('v2_action', Actions)

controllable_vehicles: [SumoControllableVehicle] = []
v1_red: SumoControllableVehicle = None
v2_green: SumoControllableVehicle = None
vut: SumoVehicle = None

action_map = {
    LANE_LEFT: 0,
    IDLE: 1,
    LANE_RIGHT: 2,
    FASTER: 3,
    SLOWER: 4
}

def wait_seconds(seconds):
    step_count_t0 = step_count
    target_step_count = int(seconds / 0.05) + step_count
    while step_count < target_step_count:
        print(f"waited {(step_count - step_count_t0) * 0.05} seconds.")
        yield sync(request=true)

def seconds(steps):
    return steps * 0.05

def change_lane_left(vehicle_id: str):
    """
    Change the lane of the vehicle to the left.
    """
    if 0 <= traci.vehicle.getLaneIndex(vehicle_id) + 1 < 3:
        traci.vehicle.changeLane(vehicle_id, traci.vehicle.getLaneIndex(vehicle_id) + 1, 1)


def change_lane_right(vehicle_id: str):
    """
    Change the lane of the vehicle to the right.
    """
    if 0 <= traci.vehicle.getLaneIndex(vehicle_id) - 1 < 3:
        traci.vehicle.changeLane(vehicle_id, traci.vehicle.getLaneIndex(vehicle_id) - 1, 1)

def faster(vehicle_id: str):
    """
    Increase the speed of the vehicle.
    """
    current_speed = traci.vehicle.getSpeed(vehicle_id)
    new_speed = current_speed + 1.0
    traci.vehicle.slowDown(vehicle_id, new_speed, 1)


def slower(vehicle_id: str):
    """
    Decrease the speed of the vehicle.
    """
    current_speed = traci.vehicle.getSpeed(vehicle_id)
    new_speed = max(0.0, current_speed - 1.0)
    traci.vehicle.slowDown(vehicle_id, new_speed, 1)

def execute_action(vehicle_id: str, action: Actions):
    """
    Execute the action for the vehicle based on the action type.

    Args:
        vehicle_id (str): The ID of the vehicle to perform the action on.
        action (Actions): The action to be performed.
    """
    if action == LANE_LEFT:
        change_lane_left(vehicle_id)
    elif action == LANE_RIGHT:
        change_lane_right(vehicle_id)
    elif action == FASTER:
        faster(vehicle_id)
    elif action == SLOWER:
        slower(vehicle_id)
    elif action == IDLE:
        # No action, do nothing
        pass
    else:
        raise ValueError(f"Unknown action: {action}")

step_count = 0

def fall_behind(behind_vehicle: SumoControllableVehicle, in_front_vehicle: SumoVehicle, min_distance = 25.0, max_duration = float("inf")):
    global step_count
    step_count_t0 = step_count
    while not behind_vehicle.is_behind_by_x(in_front_vehicle, min_distance):
        # behind_vehicle must slow down, but only until it is 2.0 slower than in_front_vehicle
        if (behind_vehicle.speed() + 2.0 > in_front_vehicle.speed()):
            yield sync(request=v1_action == SLOWER)
            yield sync(request=behind_vehicle.SLOWER())
        elif (behind_vehicle.speed() - 2.0 < in_front_vehicle.speed()):
            yield sync(request=behind_vehicle.FASTER())
        else:
            yield sync(request=behind_vehicle.IDLE())
        if seconds(step_count - step_count_t0) >= max_duration:
            print("TIMED INTERRUPT")
            break

def change_to_same_lane(vehicle_to_change_lane: SumoControllableVehicle, other_vehicle: SumoVehicle):
    while vehicle_to_change_lane.lane_index() != other_vehicle.lane_index():
        if (vehicle_to_change_lane.lane_index() < other_vehicle.lane_index()):
            yield sync(request=vehicle_to_change_lane.LANE_LEFT())
        else:
            yield sync(request=vehicle_to_change_lane.LANE_RIGHT())

def close_distance(behind_vehicle: SumoControllableVehicle, in_front_vehicle: SumoVehicle, max_distance = 25.0, max_duration = float("inf")):
    global step_count
    step_count_t0 = step_count
    while behind_vehicle.is_behind_by_x(in_front_vehicle, max_distance):
        # behind_vehicle must speed up down, but only until it is 2.0 faster than in_front_vehicle
        if (behind_vehicle.speed() - 2.0 < in_front_vehicle.speed()):
            yield sync(request=behind_vehicle.FASTER())
        elif (behind_vehicle.speed() + 2.0 > in_front_vehicle.speed()):
            yield sync(request=behind_vehicle.SLOWER())
        else:
            yield sync(request=behind_vehicle.IDLE())
        if seconds(step_count - step_count_t0) >= max_duration:
            print("TIMED INTERRUPT")
            break


def equalize_speeds(controllable_vehicle: SumoControllableVehicle, other_vehicle: SumoVehicle):
    while (abs(controllable_vehicle.speed() - other_vehicle.speed()) <= 0.1
            and abs(controllable_vehicle.speed() - other_vehicle.speed()) <= 0.1):
        if controllable_vehicle.speed() > other_vehicle.speed():
            yield sync(request=controllable_vehicle.SLOWER())
        else:
            yield sync(request=controllable_vehicle.FASTER())
        #yield from wait_seconds(0.1)


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
        #yield from wait_seconds(0.1)


@thread
def follow_behind(behind_vehicle : SumoControllableVehicle, in_front_vehicle: SumoVehicle, delay_seconds : float = 0.0):
    # " serial: "
    #yield from wait_seconds(delay_seconds)
    yield from get_behind(behind_vehicle, in_front_vehicle)
    yield from stay_behind(behind_vehicle, in_front_vehicle)

@thread
def two_vehicles_follow_vut():
    yield from parallel(
        follow_behind(v1_red, vut),
        follow_behind(v2_green, v1_red)
    )


def await_condition(condition_function, deadline_seconds=float("inf"), local_reward=0.0) -> Bool:
    global step_count
    step_count_t0 = step_count
    while seconds(step_count-step_count_t0) <= deadline_seconds :
        if condition_function():
            return true
        yield sync(waitFor=true, localReward=local_reward)
        print(f" +++  waited {seconds(step_count-step_count_t0)} seconds for condition.")
    return false


# abstract scenario:
#   - some sequence or control flow of conditions or events that we wait for / monitor
#   - or some composition of other scenarios.
@thread
def abstract_scenario_two_vehicles_follow_vut():
    def condition():
        return v1_red.is_behind_by_x(vut) and v2_green.is_behind_by_x(v1_red)  # TODO: Same lane?
    satisfied = yield from await_condition(condition, 10)
    if satisfied:
        print("################ SAT")
    else:
        print("################ UNSAT")

@thread
def abstract_scenario_2():
    # cond 1.
    satisfied = yield from await_condition(lambda : v1_red.is_behind_by_x(vut), local_reward=10.0)
    if not satisfied:
        print("################ UNSAT")
        return
    else:
        print("################ COND 1 SAT")
    # cond 2.
    satisfied = yield from await_condition(lambda : v1_red.lane_index() == vut.lane_index(), local_reward=10.0)
    if not satisfied:
        print("################ UNSAT") # -> local_reward = -100.0 ???
        return
    else:
        print("################ COND 2 SAT")
    # cond 3.
    satisfied = yield from await_condition(lambda : v2_green.is_behind_by_x(v1_red), local_reward=10.0)
    if not satisfied:
        print("################ UNSAT")
        return
    else:
        print("################ COND 3 SAT")
    # cond 4.
    satisfied = yield from await_condition(lambda : v2_green.lane_index() == v1_red.lane_index(), local_reward=10.0)
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
def traci_bthread():
    global step_count
    while True:
        e = yield sync(waitFor=true)

        actions = []
        for vehicle in controllable_vehicles:
            action_vehicle = e.eval(vehicle.vehicle_smt_var)
            if action_vehicle in action_map:
                execute_action(vehicle.vehicle_id, action_vehicle)
        traci.simulationStep()
        step_count += 1

def setup_sumo_connection(config_path: str, sumo_gui=True):
    """
    Setup and start the SUMO-traci connection.

    Args:
        config_path (str): Path to the .sumocfg file, to set up the simulation environment.
        sumo_gui (bool): Whether to run sumo-gui or just sumo in command line.
    """
    # Check SUMO_HOME environment
    if "SUMO_HOME" not in os.environ:
        sys.exit("Please declare environment variable 'SUMO_HOME'")

    sumo_bin = "sumo-gui" if sumo_gui else "sumo"
    sumo_bin_path = os.path.join(os.environ["SUMO_HOME"], "bin", sumo_bin)

    if not os.path.isfile(sumo_bin_path):
        sys.exit(f"SUMO executable not found at: {sumo_bin_path}")

    # Append tools path for traci import
    tools = os.path.join(os.environ["SUMO_HOME"], "tools")
    sys.path.append(tools)

    sumo_config = [
        sumo_bin_path,
        "-c",
        config_path,
        "--step-length",
        "0.05",
        "--delay",
        "1000",
        "--lateral-resolution",
        "0.1",
        "--start"
    ]

    traci.start(sumo_config)
    traci.gui.setZoom("View #0", 600)
    traci.gui.setOffset("View #0", -100, -196)

def setup_sumo_vehicles():
    # Controllable vehicles
    route_edges = ["entry", "longEdge", "exit"]  # Same as in your flow
    traci.vehicle.addFull(
        vehID="veh_manual_1",
        routeID="",  # We'll assign edges manually
        typeID="manual",
        depart=0,
        departPos=0.0,  # 30 meters into the entry edge
        departLane=1,
        departSpeed="avg"
    )
    traci.vehicle.addFull(
        vehID="veh_manual_2",
        routeID="",  # We'll assign edges manually
        typeID="manual",
        depart=0,
        departPos=30.0,  # 15 meters into the entry edge
        departLane=1,
        departSpeed="avg"
    )
    traci.vehicle.addFull(
        vehID="vut",
        routeID="",  # We'll assign edges manually
        typeID="vut",
        depart=0,
        departPos=15.0,  # 15 meters into the entry edge
        departLane=2,
        departSpeed="avg"
    )
    traci.vehicle.setRoute("veh_manual_1", route_edges)
    traci.vehicle.setLaneChangeMode("veh_manual_1", 0)
    traci.vehicle.setSpeedMode("veh_manual_1", 0)# Disable lane changes for manual vehicle
    traci.vehicle.setColor("veh_manual_1", (255, 0, 0, 255)) # red
    traci.vehicle.setRoute("veh_manual_2", route_edges)
    traci.vehicle.setColor("veh_manual_2", (0, 255, 0, 255)) # green
    traci.vehicle.setLaneChangeMode("veh_manual_2", 0)
    traci.vehicle.setSpeedMode("veh_manual_2", 0)# Disable lane changes for manual vehicle
    traci.vehicle.setRoute("vut", route_edges)

    global v1_red
    v1_red = SumoControllableVehicle('veh_manual_1', v1_action)
    global v2_green
    v2_green = SumoControllableVehicle('veh_manual_2', v2_action)
    global controllable_vehicles
    controllable_vehicles = [v1_red, v2_green]
    global vut
    vut = SumoVehicle('vut')
    # we have to wait a bit for the vehicles to be added to the simulation, else traci/ sumo crashes
    time.sleep(2)

if __name__ == "__main__":
    config_path = "../../sumo-maps/autobahn/autobahn.sumocfg"
    setup_sumo_connection(config_path)
    setup_sumo_vehicles()
    # Creating a BProgram with the defined b-threads, SMTEventSelectionStrategy,
    # and a listener to print the selected events
    b_program = BProgram(bthreads=[traci_bthread(), two_vehicles_follow_vut()],
                         event_selection_strategy=SMTEventSelectionStrategy(),
                         listener=PrintBProgramRunnerListener())
    b_program.run()
