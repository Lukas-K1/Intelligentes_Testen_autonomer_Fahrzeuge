import gymnasium
import highway_env
from highway_env.vehicle.controller import MDPVehicle
from bppy import (
    BProgram,
    SMTEventSelectionStrategy,
    sync,
    thread,
    true,
    PrintBProgramRunnerListener,
)
from z3 import *
import numpy as np
import logging

from src.overtake_scenarios.commons.controllable_vehicle import ControllableVehicle
from src.overtake_scenarios.commons.orchestration_helpers import is_safe_to_accelerate, is_safe_to_change_lane
from src.overtake_scenarios.commons.vehicle import Vehicle
from src.overtake_scenarios.commons.z3_actions import Actions, LANE_LEFT, LANE_RIGHT, FASTER, SLOWER

# ---- Logging configuration ----
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.DEBUG,
)
logger = logging.getLogger(__name__)

# ---- Environment Configuration ----
simulation_frequency = 20
policy_frequency = 4
safe_distance = 10.0  # safe Euclidean distance for lane changes and acceleration

env = gymnasium.make(
    "highway-v0",
    render_mode="rgb_array",
    config={
        "controlled_vehicles": 2,  # Zwei kontrollierte Fahrzeuge
        "vehicles_count": 1,       # Ein zusätzliches Fahrzeug (VUT)
        "simulation_frequency": simulation_frequency,
        "policy_frequency": policy_frequency,
        "action": {
            "type": "MultiAgentAction",
            "action_config": {
                "type": "DiscreteMetaAction",
                "target_speeds": [16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26],
            }
        },
        "observation": {
            "type": "MultiAgentObservation",
            "observation_config": {
                "type": "Kinematics",
            }
        },
        "lanes_count": 3,
        "screen_height": 150,
        "screen_width": 1200,
    },
)
env.reset(seed=2)

v1_action = Const("v1_action", Actions)
v2_action = Const("v2_action", Actions)


# ---- Utility Functions (ohne @thread) ----
def fall_behind(behind_vehicle, in_front_vehicle, min_distance=25.0, max_duration=float("inf")):
    global step_count
    start_steps = step_count
    while not behind_vehicle.is_behind(in_front_vehicle, min_distance):
        logger.debug(
            f"fall_behind: {behind_vehicle.name} speed: {behind_vehicle.speed()}, {in_front_vehicle.name} speed: {in_front_vehicle.speed()}"
        )
        if behind_vehicle.speed() + 2.0 > in_front_vehicle.speed():
            yield sync(request=behind_vehicle.SLOWER())
        elif behind_vehicle.speed() - 2.0 < in_front_vehicle.speed():
            if is_safe_to_accelerate(behind_vehicle, safe_distance, env):
                yield sync(request=behind_vehicle.FASTER())
            else:
                logger.info(f"{behind_vehicle.name}: Not safe to accelerate while falling behind")
                yield sync(request=behind_vehicle.IDLE())
        else:
            yield sync(request=behind_vehicle.IDLE())
        if seconds(step_count - start_steps) >= max_duration:
            logger.warning("fall_behind: TIMED INTERRUPT")
            break
    yield sync(request=behind_vehicle.IDLE())

def change_to_same_lane(vehicle, target_lane):
    while vehicle.lane_index() != target_lane:
        logger.debug(f"change_to_same_lane: {vehicle.name} lane: {vehicle.lane_index()}, target: {target_lane}")
        if is_safe_to_change_lane(vehicle, target_lane, safe_distance, env):
            if vehicle.lane_index() > target_lane:
                yield sync(request=vehicle.LANE_LEFT())
            else:
                yield sync(request=vehicle.LANE_RIGHT())
        else:
            logger.info(f"{vehicle.name}: Not safe to change lane to {target_lane}")
        yield sync(request=vehicle.IDLE())
    yield sync(request=vehicle.IDLE())

def close_distance(behind_vehicle, in_front_vehicle, max_distance=25.0, max_duration=float("inf")):
    global step_count
    start_steps = step_count
    while behind_vehicle.is_behind(in_front_vehicle, max_distance):
        logger.debug(
            f"close_distance: {behind_vehicle.name} speed: {behind_vehicle.speed()}, {in_front_vehicle.name} speed: {in_front_vehicle.speed()}"
        )
        if behind_vehicle.speed() - 2.0 < in_front_vehicle.speed():
            if is_safe_to_accelerate(behind_vehicle, safe_distance, env):
                yield sync(request=behind_vehicle.FASTER())
            else:
                logger.info(f"{behind_vehicle.name}: Not safe to accelerate while closing distance")
                yield sync(request=behind_vehicle.IDLE())
        elif behind_vehicle.speed() + 2.0 > in_front_vehicle.speed():
            yield sync(request=behind_vehicle.SLOWER())
        else:
            yield sync(request=behind_vehicle.IDLE())
        if seconds(step_count - start_steps) >= max_duration:
            logger.warning("close_distance: TIMED INTERRUPT")
            break
    yield sync(request=behind_vehicle.IDLE())

def equalize_speeds(behind_vehicle, in_front_vehicle):
    while abs(behind_vehicle.speed() - in_front_vehicle.speed()) > 0.1:
        logger.debug(
            f"equalize_speeds: {behind_vehicle.name} speed: {behind_vehicle.speed()}, {in_front_vehicle.name} speed: {in_front_vehicle.speed()}"
        )
        if behind_vehicle.speed() < in_front_vehicle.speed():
            if is_safe_to_accelerate(behind_vehicle, safe_distance, env):
                yield sync(request=behind_vehicle.FASTER())
            else:
                logger.info(f"{behind_vehicle.name}: Not safe to accelerate while equalizing speeds")
                yield sync(request=behind_vehicle.IDLE())
        else:
            yield sync(request=behind_vehicle.SLOWER())
    yield sync(request=behind_vehicle.IDLE())

def get_behind(behind_vehicle, in_front_vehicle):
    logger.info(f"get_behind: {behind_vehicle.name} starting to get behind {in_front_vehicle.name}")
    yield from fall_behind(behind_vehicle, in_front_vehicle)
    target_lane = in_front_vehicle.lane_index()
    logger.info(f"get_behind: {behind_vehicle.name} target lane: {target_lane}")
    yield from change_to_same_lane(behind_vehicle, target_lane)
    yield from close_distance(behind_vehicle, in_front_vehicle)
    yield from equalize_speeds(behind_vehicle, in_front_vehicle)
    logger.info(f"get_behind: {behind_vehicle.name} completed getting behind {in_front_vehicle.name}")

def idle_lock(vehicle):
    """
    Locks the vehicle in the idle state.
    """
    while True:
        yield sync(request=vehicle.IDLE())

# ---- BThread: Monitor Safe Distance Between v1 and v2 ----
@thread
def maintain_safe_distance_same_line():
    safe_gap = 15.0  # minimum gap in the x-direction (adjust as needed)
    while True:
        # Only check when both vehicles are in the same lane
        if v1.lane_index() == v2.lane_index():
            # Identify the trailing vehicle
            if v1.position()[0] < v2.position()[0]:
                trailing, leading = v1, v2
            else:
                trailing, leading = v2, v1
            gap = leading.position()[0] - trailing.position()[0]
            logger.debug(f"maintain_safe_distance: Gap between {trailing.name} and {leading.name} = {gap:.2f}")
            if gap < safe_gap:
                logger.info(f"{trailing.name}: Too close to {leading.name} (gap={gap:.2f}). Slowing down.")
                yield sync(request=trailing.SLOWER())
            else:
                yield sync(request=trailing.IDLE())
        else:
            yield sync(request=true)

# ---- BThread: Simulationsschleife ----
@thread
def highway_env_bthread():
    global step_count
    controlled_vehicles = [v1, v2]
    while True:
        ev = yield sync(waitFor=true)
        logger.debug(f"highway_env_bthread: step_count: {step_count}, SMT eval: {ev.eval(v1.vehicle_smt_var)}, {ev.eval(v2.vehicle_smt_var)}")
        actions = []
        for vehicle in controlled_vehicles:
            act_val = ev.eval(vehicle.vehicle_smt_var)
            if act_val == LANE_LEFT:
                actions.append(0)
            elif act_val == LANE_RIGHT:
                actions.append(2)
            elif act_val == FASTER:
                actions.append(3)
            elif act_val == SLOWER:
                actions.append(4)
            else:
                actions.append(1)
        actions_tuple = tuple(actions)
        env.step(actions_tuple)
        step_count += 1
        env.render()

# ---- BThread: Overtaking-Maneuver für ein Fahrzeug ----
def overtaking_maneuver(vehicle: ControllableVehicle):
    @thread
    def maneuver():
        logger.info(f"{vehicle.name}: Starting overtaking maneuver")
        # Phase 1: Positionierung – hinter den VUT kommen.
        yield from get_behind(vehicle, vut)
        yield from wait_seconds(0.5)
        # Phase 2: Ausscheren – in Überholspur wechseln.
        original_lane = vehicle.lane_index()
        logger.info(f"{vehicle.name}: Changing lane for overtaking (original lane: {original_lane})")
        # Attempt lane change only if safe.
        if original_lane > 0:
            if is_safe_to_change_lane(vehicle, original_lane - 1, safe_distance, env):
                yield sync(request=vehicle.LANE_LEFT())
            else:
                logger.info(f"{vehicle.name}: Not safe to change lane left for overtaking")
        else:
            if is_safe_to_change_lane(vehicle, original_lane + 1, safe_distance, env):
                yield sync(request=vehicle.LANE_RIGHT())
            else:
                logger.info(f"{vehicle.name}: Not safe to change lane right for overtaking")
        yield from wait_seconds(0.5)
        # Phase 3: Überholen – beschleunigen, bis das Fahrzeug den VUT überholt.
        while vehicle.position()[0] <= vut.position()[0] + safe_distance:
            logger.info(f"{vehicle.name}: Overtaking: pos: {vehicle.position()[0]} vs. VUT: {vut.position()[0]}")
            if is_safe_to_accelerate(vehicle, safe_distance, env):
                yield sync(request=vehicle.FASTER())
            else:
                logger.info(f"{vehicle.name}: Not safe to accelerate during overtaking")
                yield sync(request=vehicle.IDLE())
        # Phase 4: Wiedereinscheren – zurück in die Originalspur wechseln.
        yield from change_to_same_lane(vehicle, original_lane)
        yield from equalize_speeds(vehicle, vut)
        yield from idle_lock(vehicle)
        logger.info(f"{vehicle.name}: Overtaking maneuver completed.")
    return maneuver()

# ---- Globale Variablen und Zeitfunktionen ----
step_count = 0
def seconds(steps):
    return steps / simulation_frequency

def wait_seconds(sec):
    global step_count
    target = step_count + int(sec * simulation_frequency)
    while step_count < target:
        yield sync(request=true)

# ---- Fahrzeuge erstellen ----
# In MultiAgent-Setups sind oft die Indizes 0 und 2 für kontrollierte Fahrzeuge reserviert.
v1 = ControllableVehicle(0, env, v1_action, "v1")
v2 = ControllableVehicle(2, env, v2_action, "v2")
vut = Vehicle(1, env, "vut")

# ---- Main Program ----
def main():
    bthreads = [
        highway_env_bthread(),
        # Optionally re-enable safe distance monitoring if desired:
        # maintain_safe_distance_same_line(),
        overtaking_maneuver(v1),
        overtaking_maneuver(v2),
    ]
    bp = BProgram(
        bthreads=bthreads,
        event_selection_strategy=SMTEventSelectionStrategy(),
        listener=PrintBProgramRunnerListener(),
    )
    bp.run()

if __name__ == "__main__":
    main()
