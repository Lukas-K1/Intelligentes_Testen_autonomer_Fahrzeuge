"""
Simulationsvarianten für Constraint-Violations in dem abstrakten Überholszenario.
Diese Datei enthält Simulationen eines möglichen konkreten Szenarios, die jeweils einen der Constraints verletzen.
Jede Simulation sendet am Ende ein END-Event, das die finale Auswertung der Constraints
auslöst.

Folgende Simulationen sind enthalten:
  - valid_demo_simulation: Korrekte Simulation, die alle Constraints erfüllt.
  - invalid_position_simulation: Verletzung der Positions-Constraint (falscher Start und/oder Ende (Abstand zu VUT)).
  - invalid_duration_simulation: Verletzung der Duration-Constraint (zu wenige STEP-Events aka zu kurze Simulation).
  - invalid_functional_action_simulation: Verletzung der Functional Action Constraint
      (Intervall zwischen LANE_CHANGE und SPEED_UP zu kurz).
  - invalid_speed_simulation: Verletzung der Speed Limit Constraint (Geschwindigkeit außerhalb des zulässigen Bereichs).
"""

from bppy import BEvent, sync, thread

from overtake_constraints import (END_RELATIVE_POS, MAX_SIM_STEPS,
                                  START_RELATIVE_POS)


# Neue, spezifische Factory-Methoden für Events:
def make_position_update(distance: float) -> BEvent:
    return BEvent("POSITION_UPDATE", data={"distance_to_vut": distance})

def make_step() -> BEvent:
    return BEvent("STEP")

def make_lane_change(step: int) -> BEvent:
    return BEvent("LANE_CHANGE", data={"step": step})

def make_speed_up(step: int) -> BEvent:
    return BEvent("SPEED_UP", data={"step": step})

def make_speed_update(speed: float) -> BEvent:
    return BEvent("SPEED_UPDATE", data={"speed": speed})

def make_end() -> BEvent:
    return BEvent("END")


@thread
def valid_demo_simulation():
    """
    Simuliert exemplarisch Events für das Szenario:
      - Initiale POSITION_UPDATE mit START_RELATIVE_POS. (Startposition: 50m hinter VUT)
      - STEP-Events zur Zeitzählung.
      - Funktionale Aktionen (LANE_CHANGE bei Step 2, SPEED_UP bei Step 15).
      - SPEED_UPDATE-Events mit zulässiger Geschwindigkeit.
      - Abschließende POSITION_UPDATE mit END_RELATIVE_POS.
      - Am Ende wird ein END-Event gesendet.
    """
    step = 0
    # Startposition
    yield sync(request=make_position_update(START_RELATIVE_POS))
    while True:
        step += 1
        yield sync(request=make_step())

        if step == MAX_SIM_STEPS:
            yield sync(request=make_position_update(END_RELATIVE_POS))
        else:
            yield sync(request=make_position_update(0))

        if step == 2:
            yield sync(request=make_lane_change(step))
        if step == 15:
            yield sync(request=make_speed_up(step))

        yield sync(request=make_speed_update(20.0))

        if step >= MAX_SIM_STEPS:
            break

    yield sync(request=make_end())


@thread
def invalid_position_simulation():
    """
    Simulation, die die Position Constraint verletzt.
    Hier werden falsche Start- und Endpositionen gesendet.
    """
    step = 0
    # Falsche Startposition: statt -50 wird 0 gesendet.
    yield sync(request=make_position_update(0))
    while True:
        step += 1
        yield sync(request=make_step())

        # Immer falsche Positionsupdates
        yield sync(request=make_position_update(0))

        if step == MAX_SIM_STEPS:
            # Falsche Endposition: statt 50 wird 0 gesendet.
            yield sync(request=make_position_update(0))
            break

        if step == 2:
            yield sync(request=make_lane_change(step))
        if step == 15:
            yield sync(request=make_speed_up(step))

        yield sync(request=make_speed_update(20.0))
    yield sync(request=make_end())


@thread
def invalid_duration_simulation():
    """
    Simulation, die die Duration Constraint verletzt, indem sie zu wenige STEP-Events liefert.
    Hier wird die Simulation bereits nach 5 Steps beendet (5 < MIN_SIM_STEPS).
    """
    step = 0
    yield sync(request=make_position_update(START_RELATIVE_POS))
    while True:
        step += 1
        yield sync(request=make_step())
        yield sync(request=make_position_update(0))

        if step == 2:
            yield sync(request=make_lane_change(step))
        if step == 3:
            yield sync(request=make_speed_up(step))

        yield sync(request=make_speed_update(20.0))
        if step >= 5:
            break
    yield sync(request=make_end())


@thread
def invalid_functional_action_simulation():
    """
    Simulation, die die Functional Action Constraint verletzt,
    indem das Intervall zwischen LANE_CHANGE und SPEED_UP zu kurz ist.
    Hier wird LANE_CHANGE bei Step 2 und SPEED_UP bereits bei Step 5 gesendet (Intervall = 3, zu kurz).
    """
    step = 0
    yield sync(request=make_position_update(START_RELATIVE_POS))
    while True:
        step += 1
        yield sync(request=make_step())

        if step == MAX_SIM_STEPS:
            yield sync(request=make_position_update(END_RELATIVE_POS))
        else:
            yield sync(request=make_position_update(0))

        if step == 2:
            yield sync(request=make_lane_change(step))
        if step == 5:
            yield sync(request=make_speed_up(step))

        yield sync(request=make_speed_update(20.0))

        if step >= MAX_SIM_STEPS:
            break
    yield sync(request=make_end())


@thread
def invalid_speed_simulation():
    """
    Simulation, die die Speed Limit Constraint verletzt,
    indem ein SPEED_UPDATE-Event eine Geschwindigkeit außerhalb des zulässigen Bereichs meldet.
    Hier wird z. B. eine Geschwindigkeit von 30.0 m/s gesendet (über MAX_SPEED).
    """
    step = 0
    yield sync(request=make_position_update(START_RELATIVE_POS))
    while True:
        step += 1
        yield sync(request=make_step())

        if step == MAX_SIM_STEPS:
            yield sync(request=make_position_update(END_RELATIVE_POS))
        else:
            yield sync(request=make_position_update(0))

        if step == 2:
            yield sync(request=make_lane_change(step))
        if step == 15:
            yield sync(request=make_speed_up(step))

        # Verletzung: Geschwindigkeit außerhalb des zulässigen Bereichs (z. B. 30.0 m/s)
        yield sync(request=make_speed_update(30.0))

        if step >= MAX_SIM_STEPS:
            break
    yield sync(request=make_end())
