import math
from typing import Optional, Tuple

import traci

from src.sumo.action_enum import *


class SumoVehicle:
    """
    A class representing a controllable vehicle in SUMO.
    Inherits from SumoVehicle and adds methods for controlling the vehicle.
    """

    def __init__(
        self,
        vehicle_id: str,
        route_edges: str = ["entry", "longEdge", "exit"],
        typeID: str = "manual",
        depart_time: float = 0,
        depart_pos: float = 0.0,
        depart_lane: int = 0,
        depart_speed: str = "avg",
        vehicle_color: Tuple[int, int, int] = (0, 255, 0),
        lane_change_mode: int = 0,
        speed_mode: int = 0,
    ):

        self.vehicle_id = vehicle_id
        self.route_edges = route_edges
        self.typeID = typeID
        self.depart_time = depart_time
        self.depart_pos = depart_pos
        self.depart_lane = depart_lane
        self.depart_speed = depart_speed
        self.vehicle_color = vehicle_color
        self.lane_change_mode = lane_change_mode
        self.speed_mode = speed_mode

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

    def position(self) -> tuple[float, float]:
        """Get the (x, y) position of the vehicle in meters."""
        return traci.vehicle.getPosition(self.vehicle_id)

    def lane_position(self) -> float:
        """Get the position of the vehicle along its current lane in meters."""
        return traci.vehicle.getLanePosition(self.vehicle_id)

    def distance_to(self, other: "SumoVehicle", mode="euclidean") -> float:
        """
        Calculate the distance to another vehicle.
        :param other: the other vehicle
        :param mode: "lane" for lane-based distance, "euclidean" for straight-line distance
        """
        if mode == "lane":
            if traci.vehicle.getLaneID(self.vehicle_id) == traci.vehicle.getLaneID(
                other.vehicle_id
            ):
                return abs(self.lane_position() - other.lane_position())
            else:
                # Fallback: euklidisch
                x1, y1 = self.position()
                x2, y2 = other.position()
                return math.hypot(x2 - x1, y2 - y1)
        elif mode == "euclidean":
            x1, y1 = self.position()
            x2, y2 = other.position()
            return math.hypot(x2 - x1, y2 - y1)
        else:
            raise ValueError(f"Unknown mode {mode}")


class SumoControllableVehicle(SumoVehicle):
    """
    A class representing a controllable vehicle in SUMO.
    Inherits from SumoVehicle and adds methods for controlling the vehicle.
    """

    def __init__(
        self,
        vehicle_id: str,
        route_edges: str = ["entry", "longEdge", "exit"],
        typeID: str = "manual",
        depart_time: int = 0,
        depart_pos: float = 0.0,
        depart_lane: int = 0,
        depart_speed: str = "avg",
        vehicle_color: Tuple[int, int, int] = (0, 255, 0),
        lane_change_mode: int = 0,
        speed_mode: int = 0,
        vehicle_smt_var=None,
    ):
        """
        Initialize the SumoControllableVehicle with a vehicle ID.

        Args:
            vehicle_id (str): The ID of the vehicle in SUMO.
        """
        super().__init__(
            vehicle_id,
            route_edges,
            typeID,
            depart_time,
            depart_pos,
            depart_lane,
            depart_speed,
            vehicle_color,
            lane_change_mode,
            speed_mode,
        )
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
