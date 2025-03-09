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

# ---- Logging configuration ----
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.DEBUG,
)
logger = logging.getLogger(__name__)

# ---- Environment Configuration ----
# Wir konfigurieren die Env so, dass 2 kontrollierte Fahrzeuge (insgesamt 3 Fahrzeuge) vorhanden sind:
simulation_frequency = 20
policy_frequency = 4

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
                "target_speeds": [20, 21, 22, 23, 24, 25],
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
env.reset()

# ---- Z3 Setup für SMT-basierte Aktionen ----
Actions, (LANE_LEFT, IDLE, LANE_RIGHT, FASTER, SLOWER) = EnumSort(
    "Actions", ["LANE_LEFT", "IDLE", "LANE_RIGHT", "FASTER", "SLOWER"]
)
v1_action = Const("v1_action", Actions)
v2_action = Const("v2_action", Actions)

# ---- Fahrzeugklassen ----
class Vehicle:
    def __init__(self, v_index, env, name=""):
        self.v_index = v_index
        self.env = env
        self.env_vehicle = env.unwrapped.road.vehicles[v_index]
        self.name = name

    def position(self):
        return self.env_vehicle.position  # (x, y)

    def lane_index(self):
        li = self.env_vehicle.lane_index
        # Falls als Tuple zurückgegeben, verwende den dritten Wert (typischerweise für MultiAgent)
        if isinstance(li, tuple):
            return li[2]
        return li

    def speed(self):
        return self.env_vehicle.speed

    def is_behind(self, other, margin=0.0):
        return self.position()[0] + margin < other.position()[0]

class ControllableVehicle(Vehicle):
    def __init__(self, v_index, env, vehicle_smt_var, name=""):
        super().__init__(v_index, env, name)
        self.vehicle_smt_var = vehicle_smt_var

    # Diese Methoden dienen zur Anforderung von Aktionen in sync()-Requests.
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

# ---- Fahrzeuge erstellen ----
# In MultiAgent-Setups sind oft die Indizes 0 und 2 für kontrollierte Fahrzeuge reserviert.
v1 = ControllableVehicle(0, env, v1_action, "v1")
v2 = ControllableVehicle(2, env, v2_action, "v2")
vut = Vehicle(1, env, "vut")

# ---- Globale Variablen und Zeitfunktionen ----
step_count = 0
def seconds(steps):
    return steps / simulation_frequency

def wait_seconds(sec):
    global step_count
    target = step_count + int(sec * simulation_frequency)
    while step_count < target:
        yield sync(request=true)

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
            yield sync(request=behind_vehicle.FASTER())
        else:
            yield sync(request=behind_vehicle.IDLE())
        if seconds(step_count - start_steps) >= max_duration:
            logger.warning("fall_behind: TIMED INTERRUPT")
            break
    yield sync(request=behind_vehicle.IDLE())

def change_to_same_lane(vehicle, target_lane):
    while vehicle.lane_index() != target_lane:
        logger.debug(f"change_to_same_lane: {vehicle.name} lane: {vehicle.lane_index()}, target: {target_lane}")
        if vehicle.lane_index() > target_lane:
            yield sync(request=vehicle.LANE_LEFT())
        else:
            yield sync(request=vehicle.LANE_RIGHT())
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
            yield sync(request=behind_vehicle.FASTER())
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
            yield sync(request=behind_vehicle.FASTER())
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

# ---- BThread: Simulationsschleife ----
@thread
def highway_env_bthread():
    global step_count
    # Liste der kontrollierten Fahrzeuge
    controlled_vehicles = [v1, v2]
    while True:
        # Warten auf irgendein Ereignis (SMTEventSelectionStrategy)
        ev = yield sync(waitFor=true)
        logger.debug(f"highway_env_bthread: step_count: {step_count}, SMT eval: {ev.eval(v1.vehicle_smt_var)}, {ev.eval(v2.vehicle_smt_var)}")
        actions = []
        for vehicle in controlled_vehicles:
            # Abbildung: LANE_LEFT -> 0, IDLE -> 1, LANE_RIGHT -> 2, FASTER -> 3, SLOWER -> 4
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
        # Phase 1: Positionierung – hinter den VUT kommen
        yield from get_behind(vehicle, vut)
        yield from wait_seconds(0.5)
        # Phase 2: Ausscheren – in Überholspur wechseln
        original_lane = vehicle.lane_index()
        logger.info(f"{vehicle.name}: Changing lane for overtaking (original lane: {original_lane})")
        if original_lane > 0:
            yield sync(request=vehicle.LANE_LEFT())
        else:
            yield sync(request=vehicle.LANE_RIGHT())
        yield from wait_seconds(0.5)
        # Phase 3: Überholen – beschleunigen, bis das Fahrzeug den VUT überholt (x-Position > VUT + Sicherheitsabstand)
        safe_distance = 10.0
        while vehicle.position()[0] <= vut.position()[0] + safe_distance:
            logger.info(f"{vehicle.name}: Overtaking: pos: {vehicle.position()[0]} vs. VUT: {vut.position()[0]}")
            yield sync(request=vehicle.FASTER())
        # Phase 4: Wiedereinscheren – zurück in die Originalspur wechseln
        yield from change_to_same_lane(vehicle, original_lane)
        yield from equalize_speeds(vehicle, vut)
        yield from wait_seconds(1)
        logger.info(f"{vehicle.name}: Overtaking maneuver completed.")
    return maneuver()

# ---- Main Program ----
def main():
    bthreads = [
        highway_env_bthread(),
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
