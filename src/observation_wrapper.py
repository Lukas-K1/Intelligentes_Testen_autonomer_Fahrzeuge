import warnings

import numpy as np


class VehicleNotFoundError(Exception):
    pass

class ObservationWrapper:

    def __init__(self, observation):
        """
        Konstruktor
        :param observation: Die von der Environment zurückgegebene Observation. Dabei müssen die features
        ["x", "y", "vx", "vy"] in dieser Reihenfolge, die ersten der Observation sein.

        Important: In dieser ersten Umsetzung wird davon ausgegangen, dass die Observation vom Typ Kinematics ist.
        Zudem ist es auf Basis der HighwayEnv entwickelt, d.h. es in dieser frühen Phase ist er in anderen Environments
        mit Vorsicht zu nutzen. Zudem wird empfohlen, die Konfiguration der Obseration mit dem Parameter
        "normalize": False zu verwenden. Dann können die Distanzen fachlich in Metern interpretiert und die
        Gecshwindigkeiten in m/s werden. Ansonsten basieren die Berechnungen auf den normalisierten Werten der Observation.
        """
        self.observation = observation

    def set_observation(self, observation):
        self.observation = observation

    def is_right_lane_clear(self, vehicle_id, minimal_distance_to_front: float,
                            minimal_distance_to_back: float) -> bool:
        """
        Check, ob die vom übergebenen Fahrzeug rechte Spur frei ist.
        :param vehicle_id: Die ID des Fahrzeugs , für das die Überprüfung durchgeführt werden soll.
        :param minimal_distance_to_front: Der minimale Abstand, der nach vorne eingehalten werden soll.
        :param minimal_distance_to_back: Der minimale Abstand, der nach hinten eingehalten werden soll.
        :returns: True, wenn die rechte Spur im Bereich des übergebenen Abstandes nach vorne und hinten frei ist.

        Important: Die Fahrzeug-ID ist die Position des Fahrzeugs in der Observation.
        """
        try:
            values = self.__get_values_for_vehicle(vehicle_id)
            for i in range(1, (values.shape[0] - 1)):
                # check, if y für die Werte aus Sicht der ego-vehicles größer 0 ist (dann rechts vom ego-vehicle)
                # theoretisch, um nur die nächstgelegene Spur zu nehmen, muss y noch eingeschränkt werden + lane_size
                if values[i][1] > 0:
                    x_of_vehicle_i = values[i][0]
                    if -minimal_distance_to_back <= x_of_vehicle_i <= minimal_distance_to_front:
                        return False
            return True
        except VehicleNotFoundError:
            warnings.warn("The Vehicle was not found in the observation. The return value will always be False")
            return False

    def is_left_lane_clear(self, vehicle_id, minimal_distance_to_front: float,
                            minimal_distance_to_back: float) -> bool:
        """
        Check, ob die vom übergebenen Fahrzeug linke Spur frei ist.
        :param vehicle_id: Die ID des Fahrzeugs , für das die Überprüfung durchgeführt werden soll.
        :param minimal_distance_to_front: Der minimale Abstand, der nach vorne eingehalten werden soll.
        :param minimal_distance_to_back: Der minimale Abstand, der nach hinten eingehalten werden soll.
        :returns: True, wenn die linke Spur im Bereich des übergebenen Abstandes nach vorne und hinten frei ist.

        Important: Die Fahrzeug-ID ist die Position des Fahrzeugs in der Observation.
        """
        try:
            values = self.__get_values_for_vehicle(vehicle_id)
            for i in range(1, (values.shape[0] - 1)):
                if values[i][1] < 0:
                    x_of_vehicle_i = values[i][0]
                    if -minimal_distance_to_back <= x_of_vehicle_i <= minimal_distance_to_front:
                        return False
            return True
        except VehicleNotFoundError:
            warnings.warn("The Vehicle was not found in the observation. The return value will always be False")
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
            for i in range(1, (values.shape[0] - 1)):
                # hier wird auf eine Stelle gerundet, da sonst dieser Vergleich zu ungenau wird und nie eintritt.
                if not round(values[i][1], 1) == 0:
                    continue
                vehicle_i_distance = values[i][0]
                if vehicle_i_distance > 0:
                    if shortest_distance is None:
                        shortest_distance = vehicle_i_distance
                    elif shortest_distance > vehicle_i_distance:
                        shortest_distance = vehicle_i_distance

            return shortest_distance if shortest_distance is not None else 0
        except VehicleNotFoundError:
            warnings.warn("The Vehicle was not found in the observation. The return value will always be zero.")
            return 0

    def get_velocity(self, vehicle_id) -> float:
        """
        Ermittelt die Gesamtgeschwindigkeit des übergebenen Fahrzeugs.
        :param vehicle_id: Die ID des Fahrzeugs , für das die Überprüfung durchgeführt werden soll.
        :returns: Die Geschwindigkeit des Fahrzeugs. Sollte die Geschwindigkeit nicht ermittelt werden können, ist es 0.
        """
        try:
            values = self.__get_values_for_vehicle(vehicle_id)
            vx =  values[0][2]
            vy = values[0][3]
            """
            Die Berechnung basiert auf den beiden unabhängigen Geschwindigkeiten vx, vy und werden mittels
            des Satzes von Pythagoras genutzt, um die Gesamtgeschwindigkeit des Fahrzeuges zu berechnen.
            """
            return np.sqrt(vx**2 + vy**2)
        except VehicleNotFoundError:
            warnings.warn("The Vehicle was not found in the observation. The return value will always be zero.")
            return 0

    def __get_values_for_vehicle(self, vehicle_id):
        try:
         return self.observation[vehicle_id]
        except IndexError:
           raise VehicleNotFoundError("Vehicle not found in observation.")