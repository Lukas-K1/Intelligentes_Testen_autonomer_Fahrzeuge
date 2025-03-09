import warnings

import numpy as np
from gymnasium import Env


class VehicleNotFoundError(Exception):
    pass


class ObservationWrapper:
    """
    Diese Klasse dient dazu eine Observation aus HighwayEnv fachlich zu interpretieren.

    :attribute observation: Die von der Environment zurückgegebene Observation. Dabei müssen die features
    ["x", "y", "vx", "vy"] in genau dieser Reihenfolge, am Anfang der Observation stehen! Sonst kann die Korrektheit
    der Ergebnisse nicht gewährleistet werden.

    :attribute env: Das Environment, mit dem getestet wird. Wird für Daten zum Aufbau des Environments
    wie dem RoadNetwork benötigt, da diese nicht allein aus der Observation gelesen werden können.

    Die folgenden Werte der Observation-Config müssen wie folgt gesetzt sein:
    "absolute" = False -> Damit die Werte der anderen Fahrzeuge relativ zum betrachteten Fahrzeug angegeben werden.

    Note: In dieser ersten Umsetzung wird davon ausgegangen, dass die Observation vom Typ Kinematics ist.
    Zudem ist es auf Basis der HighwayEnv entwickelt, d.h. es in dieser frühen Phase ist er in anderen Environments
    mit Vorsicht zu nutzen. Zudem wird empfohlen, die Konfiguration der Obseration mit dem Parameter
    "normalize": False zu verwenden. Dann können die Distanzen fachlich in Metern interpretiert und die
    Gecshwindigkeiten in m/s werden. Ansonsten basieren die Berechnungen auf den normalisierten Werten der Observation.
    """

    def __init__(self, observation, env: Env = None):
        self.observation = observation
        self.env = env

    def set_observation(self, observation):
        self.observation = observation

    def is_right_lane_clear(
        self,
        vehicle_id,
        minimal_distance_to_front: float,
        minimal_distance_to_back: float,
    ) -> bool:
        """
        Check, ob die vom übergebenen Fahrzeug rechte Spur frei ist.
        :param vehicle_id: Die ID des Fahrzeugs , für das die Überprüfung durchgeführt werden soll.
        :param minimal_distance_to_front: Der minimale Abstand (als positiver Wert), der nach vorne eingehalten werden soll.
        :param minimal_distance_to_back: Der minimale Abstand (als positiver Wert), der nach hinten eingehalten werden soll.
        :returns: True, wenn die rechte Spur im Bereich des übergebenen Abstandes nach vorne und hinten frei ist. Sollten
        minimal_distance_to_front und minimal_distance_to_back beide 0 sein, wird False zurückgegeben.

        Important: Die Fahrzeug-ID ist die Position des Fahrzeugs in der Observation.
        """
        if minimal_distance_to_front == 0 and minimal_distance_to_back == 0:
            return False
        try:
            values = self.__get_values_for_vehicle(vehicle_id)
            for vehicle_i in range(1, (values.shape[0])):
                # check, if y für die Werte aus Sicht der ego-vehicles größer 0 ist (dann rechts vom ego-vehicle)
                # theoretisch, um nur die nächstgelegene Spur zu nehmen, muss y noch eingeschränkt werden + lane_size
                if values[vehicle_i][1] > 0:
                    x_of_vehicle_i = values[vehicle_i][0]
                    if (
                        -minimal_distance_to_back
                        <= x_of_vehicle_i
                        <= minimal_distance_to_front
                    ):
                        return False
            return True
        except VehicleNotFoundError:
            warnings.warn(
                "The Vehicle was not found in the observation. The return value will always be False"
            )
            return False

    def is_left_lane_clear(
        self,
        vehicle_id,
        minimal_distance_to_front: float,
        minimal_distance_to_back: float,
    ) -> bool:
        """
        Check, ob die vom übergebenen Fahrzeug linke Spur frei ist.
        :param vehicle_id: Die ID des Fahrzeugs , für das die Überprüfung durchgeführt werden soll.
        :param minimal_distance_to_front: Der minimale Abstand (als positiver Wert), der nach vorne eingehalten werden soll.
        :param minimal_distance_to_back: Der minimale Abstand (als positiver Wert), der nach hinten eingehalten werden soll.
        :returns: True, wenn die linke Spur im Bereich des übergebenen Abstandes nach vorne und hinten frei ist. Sollten
        minimal_distance_to_front und minimal_distance_to_back 0 sein, wird False zurückgegeben.

        Important: Die Fahrzeug-ID ist die Position des Fahrzeugs in der Observation.
        """
        if minimal_distance_to_front == 0 and minimal_distance_to_back == 0:
            return False
        try:
            values = self.__get_values_for_vehicle(vehicle_id)
            for vehicle_i in range(1, (values.shape[0])):
                if values[vehicle_i][1] < 0:
                    x_of_vehicle_i = values[vehicle_i][0]
                    if (
                        -minimal_distance_to_back
                        <= x_of_vehicle_i
                        <= minimal_distance_to_front
                    ):
                        return False
            return True
        except VehicleNotFoundError:
            warnings.warn(
                "The Vehicle was not found in the observation. The return value will always be False"
            )
            return False

    def get_distance_to_leading_vehicle(self, vehicle_id) -> float:
        """
        Ermittelt die Distanz zu einem auf der gleichen Spur vorausfahrenden Fahrzeug.
        :param vehicle_id: Die ID des Fahrzeugs , für das die Überprüfung durchgeführt werden soll.
        :returns: Die Distanz zum vorausfahrenden Fahrzeug. Sollte kein Fahrzeug vorausfahren, wird 0 zurückgegeben.

        Important: Die Fahrzeug-ID ist die Position des Fahrzeugs in der Observation.
        """
        try:
            shortest_distance: float = None
            values = self.__get_values_for_vehicle(vehicle_id)
            for vehicle_i in range(1, (values.shape[0])):
                # hier wird auf eine Stelle gerundet, da sonst dieser Vergleich zu ungenau wird und nie eintritt.
                if not round(values[vehicle_i][1], 1) == 0:
                    continue
                vehicle_i_distance = values[vehicle_i][0]
                if vehicle_i_distance > 0:
                    if shortest_distance is None:
                        shortest_distance = vehicle_i_distance
                    elif shortest_distance > vehicle_i_distance:
                        shortest_distance = vehicle_i_distance

            return shortest_distance if shortest_distance is not None else 0
        except VehicleNotFoundError:
            warnings.warn(
                "The Vehicle was not found in the observation. The return value will always be zero."
            )
            return 0

    def get_velocity(self, vehicle_id) -> float:
        """
        Ermittelt die Gesamtgeschwindigkeit des übergebenen Fahrzeugs.
        :param vehicle_id: Die ID des Fahrzeugs , für das die Überprüfung durchgeführt werden soll.
        :returns: Die Geschwindigkeit des Fahrzeugs. Sollte die Geschwindigkeit nicht ermittelt werden können, ist es 0.

        Important: Die Fahrzeug-ID ist die Position des Fahrzeugs in der Observation.
        """
        try:
            values = self.__get_values_for_vehicle(vehicle_id)
            vx = values[0][2]
            vy = values[0][3]
            """
            Die Berechnung basiert auf den beiden unabhängigen Geschwindigkeiten vx, vy und werden mittels
            des Satzes von Pythagoras genutzt, um die Gesamtgeschwindigkeit des Fahrzeuges zu berechnen.
            """
            return np.sqrt(vx**2 + vy**2)
        except VehicleNotFoundError:
            warnings.warn(
                "The Vehicle was not found in the observation. The return value will always be zero."
            )
            return 0

    def is_in_same_lane(self, vehicle1_id, vehicle2_id):
        """
        Überprüft, ob sich zwei Fahrzeuge auf der gleichen Spur befinden.
        :param vehicle1_id: die Position im Observation-Array des ersten Fahrzeugs
        :param vehicle2_id: die Position im Observation-Array des zweiten Fahrzeugs
        :return: True, wenn sich beide Fahrzeuge auf der gleichen Spur befinden, ansonsten False. Sollte mindestens ein
        Fahrzeug nicht in der observation gefunden werden, wird False zurückgegeben

        Important: Die vehicle_ids sind die Position des Fahrzeugs in der Observation.
        """
        try:
            values_vehicle1 = self.__get_values_for_vehicle(vehicle1_id)
            values_vehicle2 = self.__get_values_for_vehicle(vehicle2_id)
            return round(values_vehicle1[0][1]) == round(values_vehicle2[0][1])
        except VehicleNotFoundError:
            warnings.warn(
                "At least one vehicle was not found in the observation. The return value will always be False."
            )
            return False

    def is_in_lane(self, vehicle_id, lane_id) -> bool:
        """
        Prüft, ob sich ein gegebenes Fahrzeug auf einer bestimmten Lane befindet
        :param vehicle_id: Id des Fahrzeugs, für das die Lane geprüft werden soll.
        :param lane_id: Id der Lane, auf der sich das Fahrzeug befinden soll. Beginnend mit der rechten Spur
        (in Highway die unterste Spur)
        :param env: Environment, mit dem getestet wird
        :return: True, wenn sich das Fahrzeug auf der Lane befindet. Sonst False
        """
        # False, wenn das Fahrzeug nicht exisistiert
        try:
            vehicle_y = self.__get_values_for_vehicle(vehicle_id)[0][1]
        except VehicleNotFoundError:
            warnings.warn(
                "The Vehicle was not found in the observation. The return value will always be false."
            )
            return False

        # False, wenn aus Env nicht alle nötigen Daten gelesen werden können
        try:
            abstract_env = getattr(self.env, "env")
            highway = getattr(abstract_env, "env")
            road = getattr(highway, "road")
            network = getattr(road, "network")
        except AttributeError:
            warnings.warn(
                "The Environment was not set up properly. The return value will always be false."
            )
            return False

        # False, wenn Lane nicht existiert
        if (len(network.lanes_list()) - 1) < lane_id:
            return False

        # heading ist fest 0.0, weil aktuell nur highway-env betrachtet wird
        index = network.get_closest_lane_index(np.array([0, vehicle_y]), 0.0)

        # Tupel enthält "from", "to", "index"
        return index[2] == lane_id

    def __get_values_for_vehicle(self, vehicle_id):
        try:
            return self.observation[vehicle_id]
        except IndexError:
            raise VehicleNotFoundError("Vehicle not found in observation.")
