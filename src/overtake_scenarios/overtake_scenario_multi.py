"""
Overtaking Scenario Simulation
---------------------------------
This module simulates a multi-vehicle overtaking scenario using the Highway environment
and a BProgram-based coordination. Vehicles execute maneuvers that include safely positioning
behind a VUT, executing a lane change if no vehicles are within a specified Euclidean safety
radius, and accelerating only when safe. Clean code principles have been applied for clarity,
maintainability, and academic rigor.
"""

import gymnasium
import highway_env
import logging
import numpy as np
from z3 import Const, EnumSort

from bppy import (
    BProgram,
    SMTEventSelectionStrategy,
    sync,
    thread,
    true,
    PrintBProgramRunnerListener,
)
from src.overtake_scenarios.commons.controllable_vehicle import ControllableVehicle
from src.overtake_scenarios.commons.vehicle import Vehicle
from src.overtake_scenarios.commons.z3_actions import Actions, LANE_LEFT, LANE_RIGHT, FASTER, SLOWER
from src.overtake_scenarios.commons.orchestration_helpers import is_safe_to_accelerate, is_safe_to_change_lane

# -----------------------------------------------------------------------------
# Logging Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.DEBUG,
)
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Global Constants and Simulation Parameters
# -----------------------------------------------------------------------------
SIMULATION_FREQUENCY: int = 20
POLICY_FREQUENCY: int = 4
SAFE_DISTANCE: float = 10.0  # Safe Euclidean distance for lane changes and acceleration

# Global simulation time counter
step_count: int = 0


# -----------------------------------------------------------------------------
# Environment Initialization
# -----------------------------------------------------------------------------
def initialize_environment() -> gymnasium.Env:
    """
    Initializes the Highway environment with the desired configuration.
    """
    env_config = {
        "controlled_vehicles": 2,  # Two controlled vehicles
        "vehicles_count": 1,       # One additional vehicle (VUT)
        "simulation_frequency": SIMULATION_FREQUENCY,
        "policy_frequency": POLICY_FREQUENCY,
        "action": {
            "type": "MultiAgentAction",
            "action_config": {
                "type": "DiscreteMetaAction",
                "target_speeds": np.arange(0, 31, 3),
            },
        },
        "observation": {
            "type": "MultiAgentObservation",
            "observation_config": {"type": "Kinematics"},
        },
        "lanes_count": 3,
        "screen_height": 150,
        "screen_width": 1200,
    }
    env = gymnasium.make("highway-v0", render_mode="rgb_array", config=env_config)
    env.reset(seed=2)
    return env


# -----------------------------------------------------------------------------
# Time and Synchronization Utilities
# -----------------------------------------------------------------------------
def seconds(steps: int) -> float:
    """
    Converts simulation steps to seconds.
    """
    return steps / SIMULATION_FREQUENCY


def wait_seconds(duration: float):
    """
    Generator that yields sync requests until a specified duration (in seconds) has elapsed.
    """
    global step_count
    target_step = step_count + int(duration * SIMULATION_FREQUENCY)
    while step_count < target_step:
        yield sync(request=true)


# -----------------------------------------------------------------------------
# Maneuver Utility Functions
# -----------------------------------------------------------------------------
def fall_behind(behind_vehicle, in_front_vehicle, min_distance: float = 25.0, max_duration: float = float("inf")):
    """
    Commands the behind_vehicle to fall behind the in_front_vehicle until the specified
    minimum distance is achieved.
    """
    global step_count
    start_steps = step_count
    while not behind_vehicle.is_behind(in_front_vehicle, min_distance):
        logger.debug(
            f"fall_behind: {behind_vehicle.name} speed: {behind_vehicle.speed()}, "
            f"{in_front_vehicle.name} speed: {in_front_vehicle.speed()}"
        )
        if behind_vehicle.speed() + 2.0 > in_front_vehicle.speed():
            yield sync(request=behind_vehicle.SLOWER())
        elif behind_vehicle.speed() - 2.0 < in_front_vehicle.speed():
            if is_safe_to_accelerate(behind_vehicle, SAFE_DISTANCE, env):
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


def change_to_same_lane(vehicle, target_lane: int):
    """
    Executes a lane change maneuver for the vehicle until it reaches the target lane.
    The maneuver is only performed if the target lane is safe.
    """
    while vehicle.lane_index() != target_lane:
        logger.debug(f"change_to_same_lane: {vehicle.name} lane: {vehicle.lane_index()}, target: {target_lane}")
        if is_safe_to_change_lane(vehicle, target_lane, SAFE_DISTANCE, env):
            if vehicle.lane_index() > target_lane:
                yield sync(request=vehicle.LANE_LEFT())
            else:
                yield sync(request=vehicle.LANE_RIGHT())
        else:
            logger.info(f"{vehicle.name}: Not safe to change lane to {target_lane}")
        yield sync(request=vehicle.IDLE())
    yield sync(request=vehicle.IDLE())


def close_distance(behind_vehicle, in_front_vehicle, max_distance: float = 25.0, max_duration: float = float("inf")):
    """
    Adjusts the behind_vehicle's speed to reduce the gap with the in_front_vehicle until the
    distance is within a defined threshold.
    """
    global step_count
    start_steps = step_count
    while behind_vehicle.is_behind(in_front_vehicle, max_distance):
        logger.debug(
            f"close_distance: {behind_vehicle.name} speed: {behind_vehicle.speed()}, "
            f"{in_front_vehicle.name} speed: {in_front_vehicle.speed()}"
        )
        if behind_vehicle.speed() - 2.0 < in_front_vehicle.speed():
            if is_safe_to_accelerate(behind_vehicle, SAFE_DISTANCE, env):
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
    """
    Adjusts the behind_vehicle's speed until it closely matches the in_front_vehicle's speed.
    """
    while abs(behind_vehicle.speed() - in_front_vehicle.speed()) > 0.1:
        logger.debug(
            f"equalize_speeds: {behind_vehicle.name} speed: {behind_vehicle.speed()}, "
            f"{in_front_vehicle.name} speed: {in_front_vehicle.speed()}"
        )
        if behind_vehicle.speed() < in_front_vehicle.speed():
            if is_safe_to_accelerate(behind_vehicle, SAFE_DISTANCE, env):
                yield sync(request=behind_vehicle.FASTER())
            else:
                logger.info(f"{behind_vehicle.name}: Not safe to accelerate while equalizing speeds")
                yield sync(request=behind_vehicle.IDLE())
        else:
            yield sync(request=behind_vehicle.SLOWER())
    yield sync(request=behind_vehicle.IDLE())


def get_behind(behind_vehicle, in_front_vehicle):
    """
    Executes a sequence of maneuvers to position the behind_vehicle safely behind the in_front_vehicle.
    """
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
    Keeps the vehicle in an idle state indefinitely.
    """
    while True:
        yield sync(request=vehicle.IDLE())


# -----------------------------------------------------------------------------
# Behavioral Threads (BThreads)
# -----------------------------------------------------------------------------
@thread
def maintain_safe_distance_same_line():
    """
    Continuously monitors and maintains a safe longitudinal gap between the two controlled vehicles
    when they share the same lane.
    """
    safe_gap: float = 15.0  # Minimum longitudinal gap (x-direction)
    while True:
        if v1.lane_index() == v2.lane_index():
            trailing, leading = (v1, v2) if v1.position()[0] < v2.position()[0] else (v2, v1)
            gap = leading.position()[0] - trailing.position()[0]
            logger.debug(f"maintain_safe_distance: Gap between {trailing.name} and {leading.name} = {gap:.2f}")
            if gap < safe_gap:
                logger.info(f"{trailing.name}: Too close to {leading.name} (gap={gap:.2f}). Slowing down.")
                yield sync(request=trailing.SLOWER())
            else:
                yield sync(request=trailing.IDLE())
        else:
            yield sync(request=true)


@thread
def highway_env_bthread():
    """
    Acts as the central simulation loop. It synchronizes vehicle actions according to the SMT
    evaluation and advances the simulation by stepping the environment.
    """
    global step_count
    controlled_vehicles = [v1, v2]
    while True:
        event = yield sync(waitFor=true)
        logger.debug(
            f"highway_env_bthread: step_count: {step_count}, "
            f"SMT eval: {event.eval(v1.vehicle_smt_var)}, {event.eval(v2.vehicle_smt_var)}"
        )
        actions = []
        for vehicle in controlled_vehicles:
            act_val = event.eval(vehicle.vehicle_smt_var)
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


def overtaking_maneuver(vehicle: ControllableVehicle):
    """
    Defines the overtaking maneuver for a given vehicle. The maneuver comprises:
      1. Positioning behind the VUT.
      2. Executing a safe lane change for overtaking.
      3. Accelerating to pass the VUT.
      4. Reintegrating into the original lane and matching speed with the VUT.
    """
    @thread
    def maneuver():
        logger.info(f"{vehicle.name}: Starting overtaking maneuver")
        # Phase 1: Positioning
        yield from get_behind(vehicle, vut)
        yield from wait_seconds(0.5)

        # Phase 2: Lane Change for Overtaking
        original_lane = vehicle.lane_index()
        logger.info(f"{vehicle.name}: Changing lane for overtaking (original lane: {original_lane})")
        if original_lane > 0:
            if is_safe_to_change_lane(vehicle, original_lane - 1, SAFE_DISTANCE, env):
                yield sync(request=vehicle.LANE_LEFT())
            else:
                logger.info(f"{vehicle.name}: Not safe to change lane left for overtaking")
        else:
            if is_safe_to_change_lane(vehicle, original_lane + 1, SAFE_DISTANCE, env):
                yield sync(request=vehicle.LANE_RIGHT())
            else:
                logger.info(f"{vehicle.name}: Not safe to change lane right for overtaking")
        yield from wait_seconds(0.5)

        # Phase 3: Acceleration to Overtake
        while vehicle.position()[0] <= vut.position()[0] + SAFE_DISTANCE:
            logger.info(f"{vehicle.name}: Overtaking: pos: {vehicle.position()[0]} vs. VUT: {vut.position()[0]}")
            if is_safe_to_accelerate(vehicle, SAFE_DISTANCE, env):
                yield sync(request=vehicle.FASTER())
            else:
                logger.info(f"{vehicle.name}: Not safe to accelerate during overtaking")
                yield sync(request=vehicle.IDLE())

        # Phase 4: Reintegrate and Equalize Speed
        yield from change_to_same_lane(vehicle, original_lane)
        yield from equalize_speeds(vehicle, vut)
        yield sync(request=vehicle.IDLE())
        logger.info(f"{vehicle.name}: Overtaking maneuver completed.")

    return maneuver()


# -----------------------------------------------------------------------------
# Main Simulation Entry Point
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    # Initialize the environment and create vehicle instances.
    env = initialize_environment()
    v1_action = Const("v1_action", Actions)
    v2_action = Const("v2_action", Actions)

    # In multi-agent setups, indices 0 and 2 are reserved for controlled vehicles.
    v1 = ControllableVehicle(0, env, v1_action, "v1")
    v2 = ControllableVehicle(2, env, v2_action, "v2")
    vut = Vehicle(1, env, "vut")

    # Assemble BThreads for the simulation.
    bthreads = [
        highway_env_bthread(),
        # Uncomment the following line to enable safe distance monitoring between controlled vehicles:
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
