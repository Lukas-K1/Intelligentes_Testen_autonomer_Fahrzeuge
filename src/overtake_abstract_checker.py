"""
Abstraktes Szenario für Überhol-Testfall in bpPy.
Constraints (als Konstanten definiert):
  - Start: Agent 50m hinter VUT, Ende: Agent 50m vor VUT.
  - Dauer: 10–40 Steps (5–20 Sekunden, 1s = 2 Steps).
  - Funktionale Aktionen: Mindestens 1 LANE_CHANGE und 1 SPEED_UP in genau dieser Reihenfolge.
  - Intervalle zwischen den funktionalen Aktionen: 10–30 Steps (5–15 Sekunden).
  - Geschwindigkeitsbegrenzung: 13.9 m/s ≤ speed ≤ 27.8 m/s.

Hinweis: Um das Problem zu lösen, dass neue Events nie mit den konstanten Event-Objekten übereinstimmen,
definieren wir für jedes Event eine benannte Matcher-Funktion, die ausschließlich den Event-Namen vergleicht.
"""

from bppy import BProgram, BEvent, thread, sync, SimpleEventSelectionStrategy, PrintBProgramRunnerListener, All

# Konstanten
MIN_SIM_STEPS = 10
MAX_SIM_STEPS = 40
START_RELATIVE_POS = -50
END_RELATIVE_POS = 50
MIN_ACTION_INTERVAL_STEPS = 10
MAX_ACTION_INTERVAL_STEPS = 30
MIN_SPEED = 13.9
MAX_SPEED = 27.8

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

def is_idle(e):
    return e.name == "IDLE"

@thread
def position_constraint():
    """
    Prüft, ob der Agent zu Beginn am START und am Ende am END ist.
    Erwartet POSITION_UPDATE-Events mit Payload-Feld "agent_relative_position".
    """
    start_valid = None
    while True:
        evt = yield sync(waitFor=All())
        if not is_position_update(evt):
            yield sync()
            continue
        pos = evt.data.get("agent_relative_position")
        if pos is None:
            yield sync()  # Falls keine Positionsangabe vorhanden, überspringen
            continue
        if start_valid is None:
            start_valid = (pos == START_RELATIVE_POS)
        if pos == END_RELATIVE_POS:
            if start_valid:
                print("Position Constraint erfüllt.")
            else:
                print("Position Constraint verletzt: Startbedingung nicht erfüllt.")
        yield sync()

@thread
def duration_constraint():
    """
    Überwacht die Simulationsdauer anhand von STEP-Events.
    Gibt eine Warnung aus, wenn die Anzahl der Steps MAX_SIM_STEPS überschreitet.
    """
    step_count = 0
    while True:
        evt = yield sync(waitFor=All())
        if not is_step(evt):
            yield sync()
            continue
        step_count += 1
        if step_count > MAX_SIM_STEPS:
            print("Duration Constraint verletzt: Mehr als {} Steps.".format(MAX_SIM_STEPS))
        yield sync()

@thread
def functional_action_order():
    """
    Erzwingt: Zuerst LANE_CHANGE, dann SPEED_UP.
    Prüft, dass das Intervall (Payload "step") zwischen den Aktionen in [MIN_ACTION_INTERVAL_STEPS, MAX_ACTION_INTERVAL_STEPS] liegt.
    """
    lane_change_step = None
    while True:
        # Warten auf ein LANE_CHANGE- oder SPEED_UP-Event
        evt = yield sync(waitFor=All())
        if not is_lane_change(evt) and not is_speed_up(evt):
            yield sync()
            continue
        if evt.name == "LANE_CHANGE":
            if lane_change_step is None:
                lane_change_step = evt.data.get("step", 0)
        elif evt.name == "SPEED_UP":
            if lane_change_step is None:
                print("Functional Action Constraint verletzt: SPEED_UP vor LANE_CHANGE.")
            else:
                speed_up_step = evt.data.get("step", 0)
                interval = speed_up_step - lane_change_step
                if interval < MIN_ACTION_INTERVAL_STEPS or interval > MAX_ACTION_INTERVAL_STEPS:
                    print("Functional Action Constraint verletzt: Intervall {} nicht in [{}, {}].".format(
                        interval, MIN_ACTION_INTERVAL_STEPS, MAX_ACTION_INTERVAL_STEPS))
                else:
                    print("Functional Action Constraint erfüllt.")
                lane_change_step = None
        yield sync()

@thread
def speed_limit_constraint():
    """
    Stellt sicher, dass alle SPEED_UPDATE-Events (Payload: "speed") innerhalb der zulässigen Grenzen liegen.
    """
    while True:
        evt = yield sync(waitFor=All())
        if not is_speed_update(evt):
            yield sync()
            continue
        speed = evt.data.get("speed")
        if speed is not None and (speed < MIN_SPEED or speed > MAX_SPEED):
            print("Speed Limit Constraint verletzt: speed = {} m/s.".format(speed))
        yield sync()

@thread
def demo_simulation():
    """
    Simuliert exemplarisch Events für das Szenario:
      - Initiale POSITION_UPDATE mit START_RELATIVE_POS.
      - STEP-Events zur Zeitzählung.
      - Funktionale Aktionen (LANE_CHANGE bei Step 2, SPEED_UP bei Step 15) mit Payload "step".
      - SPEED_UPDATE-Events mit zulässiger Geschwindigkeit.
      - Eine abschließende POSITION_UPDATE mit END_RELATIVE_POS.
    """
    step = 0
    # Initiale Position setzen
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
        yield sync(request=make_event("IDLE"))
        if step >= MAX_SIM_STEPS + 5:
            break

def main():
    bthreads = [
        position_constraint(),
        duration_constraint(),
        functional_action_order(),
        speed_limit_constraint(),
        demo_simulation()
    ]
    bp = BProgram(
        bthreads=bthreads,
        event_selection_strategy=SimpleEventSelectionStrategy(),
        listener=PrintBProgramRunnerListener()
    )
    bp.run()

if __name__ == "__main__":
    main()
