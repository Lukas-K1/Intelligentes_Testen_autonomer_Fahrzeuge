import traci

from src.sumo.action_enum import *


class SumoVehicle:
    """
    A class representing a controllable vehicle in SUMO.
    Inherits from SumoVehicle and adds methods for controlling the vehicle.
    """

    def __init__(self, vehicle_id: str):
        self.vehicle_id = vehicle_id

    def speed(self):
        """
        Get the current speed of the vehicle.

        Returns:
            float: The current speed of the vehicle in m/s.
        """
        return traci.vehicle.getSpeed(self.vehicle_id)

    def lane_index(self):
        """
        Get the current lane index of the vehicle.

        Returns:
            int: The index of the lane the vehicle is currently in.
        """
        return traci.vehicle.getLaneIndex(self.vehicle_id)

    def is_behind_by_x(self, other_vehicle, threshold=0.0):
        """
        Check if the vehicle is behind another vehicle by a certain threshold.
        :param other_vehicle: id of the other vehicle to check against
        :param threshold: a distance threshold in meters
        :return: true if this vehicle is behind the other vehicle by more than the threshold
        """
        x_self, _ = traci.vehicle.getPosition(self.vehicle_id)
        x_other, _ = traci.vehicle.getPosition(other_vehicle.vehicle_id)
        return x_self < x_other - threshold


class SumoControllableVehicle(SumoVehicle):
    """
    A class representing a controllable vehicle in SUMO.
    Inherits from SumoVehicle and adds methods for controlling the vehicle.
    """

    def __init__(self, vehicle_id: str, vehicle_smt_var):
        """
        Initialize the SumoControllableVehicle with a vehicle ID.

        Args:
            vehicle_id (str): The ID of the vehicle in SUMO.
        """
        super().__init__(vehicle_id)
        self.vehicle_smt_var = vehicle_smt_var

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
