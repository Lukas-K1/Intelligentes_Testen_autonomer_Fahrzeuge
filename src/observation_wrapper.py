import warnings

import numpy as np


class VehicleNotFoundError(Exception):
    pass

class ObservationWrapper:

    def __init__(self, observation, features: list[str]):
        """
        Konstruktor
        :param observation: Die von der Environment zurückgegebene Observation.
        :param features: Ein Dictionary, das die features, welches die observation in der korrekten Reihenfolge als
        Dictionary enthält.

        Important: In dieser ersten Umsetzung wird davon ausgegangen, dass die Observation vom Typ Kinematics ist.
        Zudem ist es auf Basis der HighwayEnv entwickelt, d.h. es in dieser frühen Phase ist er in anderen Environments
        mit Vorsicht zu nutzen.
        """
        self.observation = observation
        # features sind unveränderbar nach der Initialisierung
        self.__features: list[str] = features if features is not None else []

    def set_observation(self, observation):
        self.observation = observation

    def is_right_lane_clear(self, vehicle_id, minimal_distance_to_front: float = 0.025,
                            minimal_distance_to_back: float = 0.025) -> bool:
        """
        Check, ob die vom übergebenen Fahrzeug rechte Spur frei ist.
        :param vehicle_id: Die ID des Fahrzeugs , für das die Überprüfung durchgeführt werden soll.
        :param minimal_distance_to_front: Der minimale Abstand, der nach vorne eingehalten werden soll.
            default-Wert ist 0.025, weil ein Auto 5m lang ist und in der normalisierten Observation 0.025 entspricht.
        :param minimal_distance_to_back: Der minimale Abstand, der nach hinten eingehalten werden soll.
            default-Wert ist 0.025, weil ein Auto 5m lang ist und in der normalisierten Observation 0.025 entspricht.
        :returns: True, wenn die rechte Spur im Bereich des übergebenen Abstandes nach vorne und hinten frei ist.

        Important: Die Fahrzeug-ID ist die Position des Fahrzeugs in der Observation.
        """
        try:
            values = self.__get_values_for_vehicle(vehicle_id)
            for i in range(1, (values.shape[0] - 1)):
                # check, if y für die Werte aus Sicht der ego-vehicles größer 0 ist (dann rechts vom ego-vehicle)
                # theoretisch, um nur die nächstgelegene Spur zu nehmen, muss y noch eingeschränkt werden + lane_size
                if values[i][self.__features.index("y")] > 0:
                    x_of_vehicle_i = values[i][self.__features.index("x")]
                    if -minimal_distance_to_back <= x_of_vehicle_i <= minimal_distance_to_front:
                        return False
            return True
        except VehicleNotFoundError:
            warnings.warn("The Vehicle was not found in the observation. The return value will always be False")
            return False
        except ValueError as e:
            warnings.warn("The following feature is not observed, which is necessary for the calculation. The return value will always be False. Missing feature:" + str(e))
            return False

    def is_left_lane_clear(self, vehicle_id, minimal_distance_to_front: float = 0.025,
                            minimal_distance_to_back: float = 0.025) -> bool:
        """
        Check, ob die vom übergebenen Fahrzeug linke Spur frei ist.
        :param vehicle_id: Die ID des Fahrzeugs , für das die Überprüfung durchgeführt werden soll.
        :param minimal_distance_to_front: Der minimale Abstand, der nach vorne eingehalten werden soll.
            default-Wert ist 0.025, weil ein Auto 5m lang ist und in der normalisierten Observation 0.025 entspricht.
        :param minimal_distance_to_back: Der minimale Abstand, der nach hinten eingehalten werden soll.
            default-Wert ist 0.025, weil ein Auto 5m lang ist und in der normalisierten Observation 0.025 entspricht.
        :returns: True, wenn die linke Spur im Bereich des übergebenen Abstandes nach vorne und hinten frei ist.

        Important: Die Fahrzeug-ID ist die Position des Fahrzeugs in der Observation.
        """
        try:
            values = self.__get_values_for_vehicle(vehicle_id)
            for i in range(1, (values.shape[0] - 1)):
                if values[i][self.__features.index("y")] < 0:
                    x_of_vehicle_i = values[i][self.__features.index("x")]
                    if -minimal_distance_to_back <= x_of_vehicle_i <= minimal_distance_to_front:
                        return False
            return True
        except VehicleNotFoundError:
            warnings.warn("The Vehicle was not found in the observation. The return value will always be False")
            return False
        except ValueError as e:
            warnings.warn("The following feature is not observed, which is necessary for the calculation. The return value will always be False. Missing feature:" + str(e))
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
                if not round(values[i][self.__features.index("y")], 1) == 0:
                    continue
                vehicle_i_distance = values[i][self.__features.index("x")]
                if vehicle_i_distance > 0:
                    if shortest_distance is None:
                        shortest_distance = vehicle_i_distance
                    elif shortest_distance > vehicle_i_distance:
                        shortest_distance = vehicle_i_distance

            return shortest_distance if shortest_distance is not None else 0
        except VehicleNotFoundError:
            warnings.warn("The Vehicle was not found in the observation. The return value will always be zero.")
            return 0
        except ValueError as e:
            warnings.warn("The following feature is not observed, which is necessary for the calculation. "
                          "The return value will always be False. Missing feature:" + str(e),)
            return False

    def get_velocity(self, vehicle_id) -> float:
        """
        Ermittelt die Gesamtgeschwindigkeit des übergebenen Fahrzeugs.
        :param vehicle_id: Die ID des Fahrzeugs , für das die Überprüfung durchgeführt werden soll.
        :returns: Die Geschwindigkeit des Fahrzeugs. Sollte die Geschwindigkeit nicht ermittelt werden können, ist es 0.

        Note: Es werden die beiden features vx und vy benötigt, um die Geschwindigkeit zu berechnen.
        Important: Die Fahrzeug-ID ist die Position des Fahrzeugs in der Observation.
        """
        try:
            values = self.__get_values_for_vehicle(vehicle_id)
            vx =  values[0][self.__features.index("vx")]
            vy = values[0][self.__features.index("vy")]
            """
            Die Berechnung basiert auf den beiden unabhängigen Geschwindigkeiten vx, vy und werden mittels
            des Satzes von Pythagoras genutzt, um die Gesamtgeschwindigkeit des Fahrzeuges zu berechnen.
            """
            return np.sqrt(vx**2 + vy**2)
        except VehicleNotFoundError:
            warnings.warn("The Vehicle was not found in the observation. The return value will always be zero.")
            return 0
        except ValueError as e:
            warnings.warn("The following feature is not observed, which is necessary for the calculation. The return value will always be False. Missing feature:" + str(e))
            return False

    def __get_values_for_vehicle(self, vehicle_id):
        try:
         return self.observation[vehicle_id]
        except IndexError:
           raise VehicleNotFoundError("Vehicle not found in observation.")