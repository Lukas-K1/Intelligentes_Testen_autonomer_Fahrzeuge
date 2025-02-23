"""
Abstraktes Szenario für Überhol-Testfall in bpPy.
Constraints (als Konstanten definiert):
  - Start: Agent 50m hinter VUT, Ende: Agent 50m vor VUT.
  - Dauer: 10–40 Steps (5–20 Sekunden, 1s = 2 Steps).
  - Funktionale Aktionen: Mindestens 1 LANE_CHANGE und 1 SPEED_UP in genau dieser Reihenfolge.
  - Intervalle zwischen den funktionalen Aktionen: 10–30 Steps (5–15 Sekunden).
  - Geschwindigkeitsbegrenzung: 13.9 m/s ≤ speed ≤ 27.8 m/s.

Alle Constraints warten abschließend auf ein END-Event, das am Ende der Simulation ausgelöst wird.
Hinweis: Zum Vergleich von Events verwenden wir ausschließlich Matcher-Funktionen, die den Event-Namen prüfen.
"""

import logging
from bppy import (
    BProgram, BEvent, thread, sync,
    SimpleEventSelectionStrategy, All
)
from overtake_constraints import (
    MAX_SIM_STEPS, START_RELATIVE_POS, END_RELATIVE_POS, MIN_ACTION_INTERVAL_STEPS, MAX_ACTION_INTERVAL_STEPS,
    MIN_SPEED, MAX_SPEED, MIN_SIM_STEPS
)


# Logging konfigurieren
logging.basicConfig(format='[%(asctime)s --- %(levelname)s] %(message)s', level=logging.INFO, datefmt='%m/%d/%Y %H:%M:%S')
logger = logging.getLogger(__name__)

def make_event(name, data=None):
    """
    Erzeugt ein neues Event mit dem angegebenen Namen und Payload.
    """
    return BEvent(name, data=data or {})

def is_position_update(e):
    return e.name == "POSITION_UPDATE"

def is_step(e):
    return e.name == "STEP"

def is_lane_change(e):
    return e.name == "LANE_CHANGE"

def is_speed_up(e):
    return e.name == "SPEED_UP"

def is_speed_update(e):
    return e.name == "SPEED_UPDATE"

def is_end(e):
    return e.name == "END"

@thread
def position_constraint():
    """
    Prüft, ob der Agent zu Beginn am START und am Ende am END ist.
    Erwartet POSITION_UPDATE-Events mit dem Payload-Feld "agent_relative_position".
    """
    start_valid = None
    end_valid = False
    while True:
        evt = yield sync(waitFor=All())
        if is_end(evt):
            break
        if not is_position_update(evt):
            continue
        pos = evt.data.get("agent_relative_position")
        if pos is None:
            continue
        if start_valid is None:
            start_valid = (pos == START_RELATIVE_POS)
        if pos == END_RELATIVE_POS:
            end_valid = True
    # Finales Reporting auf Basis des END-Events
    if start_valid is True and end_valid:
        logger.info("Position Constraint erfüllt.")
    else:
        logger.error("Position Constraint verletzt: Startbedingung und/oder Endbedingung nicht erfüllt.")

@thread
def duration_constraint():
    """
    Überwacht die Simulationsdauer anhand von STEP-Events.
    Final: Es muss eine Anzahl von Steps zwischen MIN_SIM_STEPS und MAX_SIM_STEPS liegen.
    """
    step_count = 0
    while True:
        evt = yield sync(waitFor=All())
        if is_end(evt):
            break
        if not is_step(evt):
            continue
        step_count += 1
    if MIN_SIM_STEPS <= step_count <= MAX_SIM_STEPS:
        logger.info("Duration Constraint erfüllt: {} Steps.".format(step_count))
    else:
        logger.error(
            "Duration Constraint verletzt: {} Steps (erwartet zwischen {} und {}).".format(
                step_count, MIN_SIM_STEPS, MAX_SIM_STEPS
            )
        )

@thread
def functional_action_order():
    """
    Erzwingt: Zuerst LANE_CHANGE, dann SPEED_UP.
    Prüft, dass das Intervall (Payload "step") zwischen den Aktionen in [MIN_ACTION_INTERVAL_STEPS, MAX_ACTION_INTERVAL_STEPS] liegt.
    Zusätzlich müssen mindestens ein LANE_CHANGE und ein SPEED_UP erfolgt sein.
    """
    lane_change_step = None
    lane_change_count = 0
    speed_up_count = 0
    valid_time_between_actions = False
    order_violation = False
    while True:
        evt = yield sync(waitFor=All())
        if is_end(evt):
            break
        if is_lane_change(evt):
            lane_change_step = evt.data.get("step", 0)
            lane_change_count += 1
        elif is_speed_up(evt):
            if lane_change_step is None:
                order_violation = True
            else:
                speed_up_step = evt.data.get("step", 0)
                interval = speed_up_step - lane_change_step
                if MIN_ACTION_INTERVAL_STEPS <= interval <= MAX_ACTION_INTERVAL_STEPS:
                    valid_time_between_actions = True
                else:
                    order_violation = True
                speed_up_count += 1
                lane_change_step = None
    if lane_change_count >= 1 and speed_up_count >= 1 and valid_time_between_actions and not order_violation:
        logger.info("Functional Action Constraint erfüllt.")
    else:
        logger.error(
            "Functional Action Constraint verletzt: lane_change_count={}, speed_up_count={}, valid_time_between_actions={}, order_violation={}".format(
                lane_change_count, speed_up_count, valid_time_between_actions, order_violation
            )
        )

@thread
def speed_limit_constraint():
    """
    Stellt sicher, dass alle SPEED_UPDATE-Events (Payload: "speed") innerhalb der zulässigen Grenzen liegen.
    """
    violation_count = 0
    while True:
        evt = yield sync(waitFor=All())
        if is_end(evt):
            break
        if not is_speed_update(evt):
            continue
        speed = evt.data.get("speed")
        if speed is not None and (speed < MIN_SPEED or speed > MAX_SPEED):
            violation_count += 1
    if violation_count == 0:
        logger.info("Speed Limit Constraint erfüllt.")
    else:
        logger.error("Speed Limit Constraint verletzt: {} Geschwindigkeitsverstöße.".format(violation_count))

@thread
def valid_demo_simulation():
    """
    Simuliert exemplarisch Events für das Szenario:
      - Initiale POSITION_UPDATE mit START_RELATIVE_POS.
      - STEP-Events zur Zeitzählung.
      - Funktionale Aktionen (LANE_CHANGE bei Step 2, SPEED_UP bei Step 15) mit Payload "step".
      - SPEED_UPDATE-Events mit zulässiger Geschwindigkeit.
      - Abschließende POSITION_UPDATE mit END_RELATIVE_POS.
      - Am Ende wird ein END-Event gesendet, das alle Constraints final evaluieren lässt.
    """
    step = 0
    yield sync(request=make_event("POSITION_UPDATE", {"agent_relative_position": START_RELATIVE_POS}))
    while True:
        step += 1
        yield sync(request=make_event("STEP"))
        if step == MAX_SIM_STEPS:
            yield sync(request=make_event("POSITION_UPDATE", {"agent_relative_position": END_RELATIVE_POS}))
        else:
            yield sync(request=make_event("POSITION_UPDATE", {"agent_relative_position": 0}))
        if step == 2:
            yield sync(request=make_event("LANE_CHANGE", {"step": step}))
        if step == 15:
            yield sync(request=make_event("SPEED_UP", {"step": step}))
        yield sync(request=make_event("SPEED_UPDATE", {"speed": 20.0}))
        if step >= MAX_SIM_STEPS:
            break
    # Sende das END-Event, damit alle Constraints final ausgewertet werden
    yield sync(request=make_event("END"))

def main():
    bthreads = [
        position_constraint(),
        duration_constraint(),
        functional_action_order(),
        speed_limit_constraint(),
        valid_demo_simulation()
    ]
    bp = BProgram(
        bthreads=bthreads,
        event_selection_strategy=SimpleEventSelectionStrategy(),
    )
    bp.run()

if __name__ == "__main__":
    main()
