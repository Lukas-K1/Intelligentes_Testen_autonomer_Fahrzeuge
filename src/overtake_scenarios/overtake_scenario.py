import logging

import gymnasium
import highway_env
import numpy as np
from bppy import BProgram, SMTEventSelectionStrategy, sync, thread, true
from highway_env.vehicle.controller import MDPVehicle
from z3 import *

from src.overtake_scenarios.commons.controllable_vehicle import \
    ControllableVehicle
from src.overtake_scenarios.commons.vehicle import Vehicle
from src.overtake_scenarios.commons.z3_actions import *

# ---- Logging configuration ----
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---- Configuration ----
simulation_frequency = 20
policy_frequency = 4

env = gymnasium.make(
    "highway-v0",
    render_mode="rgb_array",
    config={
        "controlled_vehicles": 1,  # Nur ein kontrolliertes Fahrzeug
        "vehicles_count": 1,  # Ein zusätzliches Fahrzeug (VUT)
        "simulation_frequency": simulation_frequency,
        "policy_frequency": policy_frequency,
    },
)
env.unwrapped.config.update(
    {
        "action": {"type": "DiscreteMetaAction", "target_speeds": [18, 21, 23]},
        "observation": {"type": "Kinematics"},
        "lanes_count": 3,
        "screen_height": 150,
        "screen_width": 1200,
    }
)
env.reset()

v1_action = Const("v1_action", Actions)

# ---- Fahrzeuge erstellen ----
v1 = ControllableVehicle(0, env, v1_action, "v1")
vut = Vehicle(1, env, "vut")

for vehicle in env.unwrapped.road.vehicles:
    if isinstance(vehicle, MDPVehicle):
        vehicle.target_speeds = np.linspace(-5, 45, 50)

# ---- Globale Variablen und Hilfsfunktionen ----
step_count = 0


def seconds(steps):
    return steps / simulation_frequency


def wait_seconds(sec):
    global step_count
    target = step_count + int(sec * simulation_frequency)
    while step_count < target:
        yield sync(request=true)


# ---- Utility Functions ----
def fall_behind(
    behind_vehicle, in_front_vehicle, min_distance=25.0, max_duration=float("inf")
):
    global step_count
    step_count_t0 = step_count
    while not behind_vehicle.is_behind(in_front_vehicle, min_distance):
        logger.debug(
            f"fall_behind: behind_vehicle speed: {behind_vehicle.speed()}, in_front_vehicle speed: {in_front_vehicle.speed()}"
        )
        if behind_vehicle.speed() + 2.0 > in_front_vehicle.speed():
            yield sync(request=behind_vehicle.SLOWER())
        elif behind_vehicle.speed() - 2.0 < in_front_vehicle.speed():
            yield sync(request=behind_vehicle.FASTER())
        else:
            yield sync(request=behind_vehicle.IDLE())
        if seconds(step_count - step_count_t0) >= max_duration:
            logger.warning("fall_behind: TIMED INTERRUPT")
            break
    yield sync(request=behind_vehicle.IDLE())


def change_to_same_lane(vehicle, target_lane):
    while vehicle.lane_index() != target_lane:
        logger.debug(
            f"change_to_same_lane: vehicle lane: {vehicle.lane_index()}, target lane: {target_lane}"
        )
        if vehicle.lane_index() > target_lane:
            yield sync(request=vehicle.LANE_LEFT())
        else:
            yield sync(request=vehicle.LANE_RIGHT())
        yield sync(
            request=vehicle.IDLE()
        )  # Zum Syncen, damit der Spurwechsel korrekt abschließt
    yield sync(request=vehicle.IDLE())


def close_distance(
    behind_vehicle, in_front_vehicle, max_distance=25.0, max_duration=float("inf")
):
    global step_count
    step_count_t0 = step_count
    while behind_vehicle.is_behind(in_front_vehicle, max_distance):
        logger.debug(
            f"close_distance: behind_vehicle speed: {behind_vehicle.speed()}, in_front_vehicle speed: {in_front_vehicle.speed()}"
        )
        if behind_vehicle.speed() - 2.0 < in_front_vehicle.speed():
            yield sync(request=behind_vehicle.FASTER())
        elif behind_vehicle.speed() + 2.0 > in_front_vehicle.speed():
            yield sync(request=behind_vehicle.SLOWER())
        else:
            yield sync(request=behind_vehicle.IDLE())
        if seconds(step_count - step_count_t0) >= max_duration:
            logger.warning("close_distance: TIMED INTERRUPT")
            break
    yield sync(request=behind_vehicle.IDLE())


def equalize_speeds(behind_vehicle, in_front_vehicle):
    while abs(behind_vehicle.speed() - in_front_vehicle.speed()) > 0.1:
        logger.debug(
            f"equalize_speeds: behind_vehicle speed: {behind_vehicle.speed()}, in_front_vehicle speed: {in_front_vehicle.speed()}"
        )
        if behind_vehicle.speed() < in_front_vehicle.speed():
            yield sync(request=behind_vehicle.FASTER())
        else:
            yield sync(request=behind_vehicle.SLOWER())
    yield sync(request=behind_vehicle.IDLE())


def get_behind(behind_vehicle, in_front_vehicle):
    logger.info("get_behind: Starting to get behind the in-front vehicle")
    yield from fall_behind(behind_vehicle, in_front_vehicle)
    target_lane = in_front_vehicle.lane_index()
    yield from change_to_same_lane(behind_vehicle, target_lane)
    yield from close_distance(behind_vehicle, in_front_vehicle)
    yield from equalize_speeds(behind_vehicle, in_front_vehicle)
    logger.info("get_behind: Completed getting behind the in-front vehicle")


# ---- BThread: Simulationsschleife ----
@thread
def highway_env_bthread():
    global step_count
    while True:
        evt = yield sync(waitFor=true)
        logger.debug(
            f"highway_env_bthread: step_count: {step_count}, action: {evt.eval(v1.vehicle_smt_var)}"
        )
        action_val = evt.eval(v1.vehicle_smt_var)
        if action_val == LANE_LEFT:
            action_index = 0
        elif action_val == LANE_RIGHT:
            action_index = 2
        elif action_val == FASTER:
            action_index = 3
        elif action_val == SLOWER:
            action_index = 4
        else:
            action_index = 1  # IDLE
        env.step(action_index)
        step_count += 1
        env.render()


# ---- BThread: Overtaking-Maneuver ----
@thread
def overtaking_maneuver():
    logger.info("overtaking_maneuver: Starting overtaking maneuver")
    # Phase 1: Positionierung – mittels Utility-Funktionen hinter den VUT kommen.
    yield from get_behind(v1, vut)

    # Kurze Wartephase zum Luftholen
    yield from wait_seconds(0.5)

    # Phase 2: Ausscheren – wechsle in eine Überholspur.
    logger.info("overtaking_maneuver: Changing lane for overtaking")
    original_lane = v1.lane_index()
    if original_lane > 0:
        yield sync(request=v1.LANE_LEFT())
    else:
        yield sync(request=v1.LANE_RIGHT())

    # Kurze Wartephase zum Luftholen
    yield from wait_seconds(0.5)

    # Phase 3: Überholen – beschleunige, bis v1 den VUT überholt (x-Position von v1 > x-Position von VUT + Abstand)
    safe_distance = 7.0  # Sicherheitsabstand zum Einscheren
    while v1.position()[0] <= vut.position()[0] + safe_distance:
        logger.debug(
            f"overtaking_maneuver: v1 pos: {v1.position()[0]}, vut pos: {vut.position()[0]}"
        )
        yield sync(request=v1.FASTER())

    # Phase 4: Wiedereinscheren – wechsle zurück in die ursprüngliche Spur.
    logger.info("overtaking_maneuver: Changing back to original lane")
    yield from change_to_same_lane(v1, original_lane)
    # Geschwindigkeit wieder anpassen. Wir sind ja keine Raser.
    logger.info("overtaking_maneuver: Equalizing speeds")
    yield from equalize_speeds(v1, vut)

    # Kurze Stabilisationsphase
    yield from wait_seconds(2)

    # Phase 5: Wiederholtes Einscheren vor dem VUT und Geschwindigkeit anpassen, falls es die Spur wechselt.
    # TODO: Aus irgendwelchen Gründen möchte das VUT nicht hinter uns sein. Wird Phase 5 einkommentiert, dann wird
    # das VUT immer die Spur wechseln und wir spielen "Fahr vor dem VUT"... Ist aber nicht wichtig. Überholen ist
    # ja schon geschehen.
    # while true:
    #     if vut.lane_index() != v1.lane_index():
    #         yield from change_to_same_lane(v1, vut.lane_index())
    #         yield from equalize_speeds(v1, vut)
    #     else :
    #         yield sync(request=v1.IDLE())

    logger.info("overtaking_maneuver: Overtaking maneuver completed.")


def main():
    bthreads = [
        highway_env_bthread(),
        overtaking_maneuver(),
    ]
    bp = BProgram(
        bthreads=bthreads,
        event_selection_strategy=SMTEventSelectionStrategy(),
    )
    bp.run()


if __name__ == "__main__":
    main()
