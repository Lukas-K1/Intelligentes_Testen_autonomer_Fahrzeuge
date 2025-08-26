# src/sumo/sumo-env-multi-agent-setting-intersection.py
import logging
import sys
import time
import traceback

import gymnasium as gym
import register_env  # registriert "SumoEnv-v0"
import traci
from bppy import *
from z3 import Const

from src.sumo.action_enum import *
from src.sumo.sumo_env import SumoEnv  # <- deine robuste Env
from src.sumo.sumo_vehicle import SumoControllableVehicle, SumoVehicle

# -----------------------------------------------------------------------------
# Logging Setup
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("intersection")

# -----------------------------------------------------------------------------
# Globaler Step Counter (nur Prints)
# -----------------------------------------------------------------------------
step_count = 0

# -----------------------------------------------------------------------------
# SMT-Variablen (Actions)
# -----------------------------------------------------------------------------
v_south_action = Const("v_south_action", Actions)
v_east_action = Const("v_east_action", Actions)

# -----------------------------------------------------------------------------
# Vehicles (konkretes Szenario)
# -----------------------------------------------------------------------------
v_east = SumoControllableVehicle(
    vehicle_id="veh_east",
    route_edges=[
        "Edge_East_to_Middle",
        "Edge_East_to_Intersection",
        "Edge_West_from_Intersection",
        "Edge_West_from_Middle",
    ],
    typeID="manual",
    depart_time=5.0,
    depart_pos=10.0,
    depart_lane=0,
    depart_speed="avg",
    vehicle_color=(0, 255, 0),
    lane_change_mode=31,
    speed_mode=31,
    vehicle_smt_var=v_east_action,
)

v_south = SumoControllableVehicle(
    vehicle_id="veh_south",
    route_edges=[
        "Edge_South_to_Middle",
        "Edge_South_to_Intersection",
        "Edge_North_from_Intersection",
        "Edge_North_from_Middle",
    ],
    typeID="manual",
    depart_time=0.0,
    depart_pos=5.0,
    depart_lane=0,
    depart_speed="avg",
    vehicle_color=(255, 0, 0),
    lane_change_mode=31,
    speed_mode=31,
    vehicle_smt_var=v_south_action,
)

controllable_vehicles = [v_east, v_south]
vut = SumoVehicle("vut")

# internal control flags
_allowed_south = False  # once set True, v_south can speed up

# global Action-Flags
current_actions = {"veh_east": IDLE, "veh_south": IDLE}

# -----------------------------------------------------------------------------
# Gym Env create
# -----------------------------------------------------------------------------
config_path = "../../sumo-maps/intersection/intersection_v2.sumocfg"
try:
    env = gym.make(
        "SumoEnv-v0",
        sumo_config_file=config_path,
        controllable_vehicles=[v_east, v_south],
    )
    log.info("Gym Env erstellt.")
except Exception as e:
    log.exception("Fehler beim Erstellen der Gym-Umgebung: %s", e)
    raise

# reset
try:
    env.reset()
    log.info("Env.reset() erfolgreich")
    log.debug("Vehicles after reset: %s", traci.vehicle.getIDList())
except Exception as e:
    log.exception("Env.reset() fehlgeschlagen: %s", e)
    raise

traci.gui.trackVehicle("View #0", v_south.vehicle_id)

# -----------------------------------------------------------------------------
# Action Mapping
# -----------------------------------------------------------------------------
action_map = {LANE_LEFT: 0, IDLE: 1, LANE_RIGHT: 2, FASTER: 3, SLOWER: 4}


# ---------------------------
# Abstract check: Stop + Pass
# ---------------------------
def seconds(steps):
    return steps * 0.05  # same step-length like SumoEnv


def await_condition(condition_function, deadline_seconds=float("inf")) -> bool:
    """warte bis condition_function() True wird oder Deadline überschreitet.
    Gibt True/False zurück. Tick-getrieben mittels yield sync(waitFor=true)."""
    global step_count
    step_count_t0 = step_count
    while seconds(step_count - step_count_t0) <= deadline_seconds:
        try:
            if condition_function():
                return True
        except Exception as e:
            log.debug("[AWAIT] condition check failed: %s", e)
        yield sync(waitFor=true)
    return False


@thread
def abstract_check_stop_and_pass(
    stop_speed_threshold: float = 0.1,
    wait_stop_seconds: float = 100.0,
    wait_pass_seconds: float = 100.0,
):
    """
    Abstraktes Szenario:
      1) Warte bis veh_south speed <= stop_speed_threshold (innerhalb wait_stop_seconds)
      2) Dann warte bis veh_east auf der westlichen Seite ist (innerhalb wait_pass_seconds)
    Loggt Ergebnis (SAT / UNSAT).
    """
    log.info("[BTHREAD] abstract_check_stop_and_pass gestartet.")
    # wait until vehicle spawned
    while True:
        ids = set(traci.vehicle.getIDList())
        if "veh_south" in ids and "veh_east" in ids:
            break
        yield sync(waitFor=true)

    # Cond 1: veh_south stopped (speed <= threshold)
    def south_stopped():
        try:
            return traci.vehicle.getSpeed("veh_south") <= stop_speed_threshold
        except Exception:
            return False

    stopped = yield from await_condition(
        south_stopped, deadline_seconds=wait_stop_seconds
    )
    if not stopped:
        log.warning(
            "[ABSTRACT] UNSAT: veh_south hat nicht gestoppt innerhalb %.1fs",
            wait_stop_seconds,
        )
        return
    log.info("[ABSTRACT] COND1 SAT: veh_south gestoppt.")

    # Cond 2: veh_east passed
    west_edges = {"Edge_West_from_Intersection", "Edge_West_from_Middle"}

    def east_passed_west():
        try:
            road = traci.vehicle.getRoadID("veh_east")
            return isinstance(road, str) and road in west_edges
        except Exception:
            return False

    log.info(
        "[ABSTRACT] Warte darauf, dass 'veh_east' Westseite erreicht (edges=%s)",
        west_edges,
    )
    passed = yield from await_condition(
        east_passed_west, deadline_seconds=wait_pass_seconds
    )
    if not passed:
        log.warning(
            "[ABSTRACT] UNSAT: veh_east hat Westseite nicht erreicht innerhalb %.1fs",
            wait_pass_seconds,
        )
        return

    log.info(
        "[ABSTRACT] SAT: veh_south gestoppt und veh_east hat die Kreuzung passiert."
    )


# -----------------------------------------------------------------------------
# BThread: right of way for v_east
# -----------------------------------------------------------------------------
@thread
def right_of_way_scenario():
    log.info("[BTHREAD] right_of_way_scenario gestartet")

    STOP_TRIGGER_DISTANCE = 30.0  # 30 Meters distance to intersection

    while True:
        ids = set(traci.vehicle.getIDList())
        if v_east.vehicle_id in ids and v_south.vehicle_id in ids:
            log.debug("[BTHREAD] Beide Fahrzeuge in SUMO vorhanden: %s", ids)
            break
        yield sync(waitFor=true)

    global _allowed_south

    while True:
        try:
            ids = set(traci.vehicle.getIDList())
            if v_east.vehicle_id not in ids or v_south.vehicle_id not in ids:
                yield sync(waitFor=true)
                continue

            east_road = traci.vehicle.getRoadID(v_east.vehicle_id)
            log.debug("[SCEN] v_east road=%s", east_road)

            # compute distance-to-end
            try:
                lane_id = traci.vehicle.getLaneID(
                    v_east.vehicle_id
                )  # for example "Edge_East_to_Intersection"
                lane_pos = traci.vehicle.getLanePosition(v_east.vehicle_id)
                lane_length = traci.lane.getLength(lane_id)
                distance_to_junction = lane_length - lane_pos
                log.debug(
                    "[SCEN] v_east lane=%s lane_pos=%.2f lane_len=%.2f dist_to_junc=%.2f",
                    lane_id,
                    lane_pos,
                    lane_length,
                    distance_to_junction,
                )
            except Exception as e:
                log.debug("[SCEN] Konnte Distanz zu Junction nicht berechnen: %s", e)
                distance_to_junction = None

            # Stop veh_south if veh_east is to close to intersection
            if east_road == "Edge_East_to_Intersection":
                if (
                    distance_to_junction is not None
                    and distance_to_junction <= STOP_TRIGGER_DISTANCE
                ):
                    log.debug(
                        "[SCEN] v_east ist <= %.1fm vor Kreuzung -> stoppe v_south",
                        STOP_TRIGGER_DISTANCE,
                    )
                    _allowed_south = False
                    current_actions["veh_south"] = SLOWER
                    current_actions["veh_east"] = FASTER
                else:
                    # if veh_east not close enough, do as before (allowed_south)
                    log.debug(
                        "[SCEN] v_east auf Edge_East_to_Intersection, aber noch %.2fm entfernt -> warte",
                        (
                            distance_to_junction
                            if distance_to_junction is not None
                            else -1.0
                        ),
                    )
                    if _allowed_south:
                        current_actions["veh_south"] = FASTER
                    else:
                        current_actions["veh_south"] = IDLE
                    current_actions["veh_east"] = FASTER

            # v_east passed the intersection
            elif east_road == "Edge_West_from_Intersection":
                log.debug(
                    "[SCEN] v_east auf Edge_West_from_Intersection -> erlaube v_south"
                )
                _allowed_south = True
                current_actions["veh_south"] = FASTER
                current_actions["veh_east"] = FASTER

            elif east_road == "Edge_West_from_Middle":
                log.debug(
                    "[SCEN] v_east auf Edge_West_from_Middle -> stoppe v_east, erlaube v_south"
                )
                _allowed_south = True
                current_actions["veh_east"] = SLOWER
                current_actions["veh_south"] = FASTER

            # Default settings for vehicle
            else:
                if _allowed_south:
                    current_actions["veh_south"] = FASTER
                    current_actions["veh_east"] = FASTER
                else:
                    current_actions["veh_south"] = IDLE
                    current_actions["veh_east"] = IDLE

        except Exception as e:
            log.exception("[BTHREAD] Exception in right_of_way_scenario loop: %s", e)

        yield sync(waitFor=true)


# -----------------------------------------------------------------------------
# Tick BThread
# -----------------------------------------------------------------------------
@thread
def tick_bthread():
    while True:
        yield sync(request=true)


# -----------------------------------------------------------------------------
# BThread: SUMO-Env
# -----------------------------------------------------------------------------
@thread
def sumo_env_bthread():
    global step_count
    log.info("[BTHREAD] sumo_env_bthread gestartet.")

    while True:
        # wait for the Z3 true tick
        e = yield sync(waitFor=true)
        actions = []
        for vehicle in controllable_vehicles:
            vid = vehicle.vehicle_id
            act = current_actions.get(vid, IDLE)
            actions.append(action_map[act])

        try:
            obs_local, reward, terminated, truncated, info = env.step(tuple(actions))
            done = all(
                v not in traci.vehicle.getIDList() for v in ["veh_south", "veh_east"]
            )
            if done:
                print("Alle Fahrzeuge haben das Netz verlassen → Simulation beendet.")
                traci.close()
                sys.exit(0)

            log.debug(
                "[STEP] %d actions=%s terminated=%s truncated=%s",
                step_count,
                actions,
                terminated,
                truncated,
            )
        except Exception as step_e:
            log.error("[BTHREAD] Exception in env.step(): %r", step_e)
            traceback.print_exc()
            raise

        # States of vehicle Log
        try:
            for vehicle in controllable_vehicles:
                if vehicle.vehicle_id in traci.vehicle.getIDList():
                    r = traci.vehicle.getRoadID(vehicle.vehicle_id)
                    sp = traci.vehicle.getSpeed(vehicle.vehicle_id)
                    lp = traci.vehicle.getLanePosition(vehicle.vehicle_id)
                    log.debug(
                        "[STATUS] %s | road=%s pos=%.1f speed=%.2f",
                        vehicle.vehicle_id,
                        r,
                        lp,
                        sp,
                    )
        except Exception as e:
            log.debug("Fahrzeuge konnten nicht abgefragt werden: %s", e)

        step_count += 1


# -----------------------------------------------------------------------------
# BProgram start
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    try:
        b_program = BProgram(
            bthreads=[
                sumo_env_bthread(),
                right_of_way_scenario(),
                tick_bthread(),
                abstract_check_stop_and_pass(),
            ],
            event_selection_strategy=SMTEventSelectionStrategy(),
            listener=PrintBProgramRunnerListener(),
        )
        log.info("BProgram wird gestartet …")
        traci.gui.trackVehicle("View #0", v_south.vehicle_id)
        b_program.run()
    except KeyboardInterrupt:
        log.info("Abbruch durch Benutzer, schließe SUMO …")
        try:
            traci.close()
        except Exception:
            pass
    except Exception as e:
        log.exception("Unbehandelte Exception im Main: %s", e)
        try:
            traci.close()
        except Exception:
            pass
        raise
