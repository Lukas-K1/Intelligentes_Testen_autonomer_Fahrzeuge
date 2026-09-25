from src.overtake_scenarios.commons.vehicle import Vehicle
from src.overtake_scenarios.commons.z3_actions import *


class ControllableVehicle(Vehicle):
    def __init__(self, v_index, env, vehicle_smt_var, name=""):
        super().__init__(v_index, env, name)
        self.vehicle_smt_var = vehicle_smt_var

    # Action-Methoden für sync()-Requests
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
