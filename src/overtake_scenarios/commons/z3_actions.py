from z3 import EnumSort

Actions, (LANE_LEFT, IDLE, LANE_RIGHT, FASTER, SLOWER) = EnumSort(
    "Actions", ["LANE_LEFT", "IDLE", "LANE_RIGHT", "FASTER", "SLOWER"]
)