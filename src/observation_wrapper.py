import warnings

import numpy as np


class VehicleNotFoundError(Exception):
    pass

class ObservationWrapper:

    def __init__(self, observation, features: list[str], minium_distance: float = 0.025):
        """
        Konstruktor
        :param observation: Die von der Environment zurückgegebene Observation.
        :param features: Ein Dictionary, das die features, welches die observation in der korrekten Reihenfolge als
        Dictionary enthält.
        :param minimum_distance: Der minimale Abstand, der zu anderen Fahrzeugen eingehalten werden muss/ sollte.
        Der default-Wert von 0.025 hat sich als ausreichend erwiesen. Hängt wahrscheinlich mit der default-Länge eines
        Fahrzeuges von 5 Metern zusammen.

        Important: In dieser ersten Umsetzung wird davon ausgegangen, dass die Observation vom Typ Kinematics ist.
        Zudem ist es auf Basis der HighwayEnv entwickelt, d.h. es in dieser frühen Phase ist er in anderen Environments
        mit Vorsicht zu nutzen.
        """
        self.observation = observation
        # features sind unveränderbar nach der Initialisierung
        self.__features: list[str] = features if features is not None else []
        self.minimum_distance = minium_distance

    def set_observation(self, observation):
        self.observation = observation

    def is_right_lane_clear(self, vehicle_id) -> bool:
        """
        Check, ob die vom übergebenen Fahrzeug rechte Spur frei ist.
        :param vehicle_id: Die ID des Fahrzeugs , für das die Überprüfung durchgeführt werden soll.

        Important: Die Fahrzeug-ID ist die Position des Fahrzeugs in der Observation.
        """
        try:
            values = self.__get_values_for_vehicle(vehicle_id)
            for i in range(1, (values.shape[0] - 1)):
                # check, if y für die Werte aus Sicht der ego-vehicles größer 0 ist (dann rechts vom ego-vehicle)
                # theoretisch, um nur die nächstgelegene Spur zu nehmen, muss y noch eingeschränkt werden + lane_size
                if values[i][self.__features.index("y")] > 0:
                    x_of_vehicle_i = values[i][self.__features.index("x")]
                    if -self.minimum_distance <= x_of_vehicle_i <= self.minimum_distance:
                        return False
            return True
        except VehicleNotFoundError:
            warnings.warn("The Vehicle was not found in the observation. The return value will always be False")
            return False
        except ValueError as e:
            warnings.warn("The following feature is not observed, which is necessary for the calculation. The return value will always be False. Missing feature:" + str(e))
            return False

    def is_left_lane_clear(self, vehicle_id) -> bool:
        """
        Check, ob die vom übergebenen Fahrzeug linke Spur frei ist.
        :param vehicle_id: Die ID des Fahrzeugs , für das die Überprüfung durchgeführt werden soll.
        """
        try:
            values = self.__get_values_for_vehicle(vehicle_id)
            for i in range(1, (values.shape[0] - 1)):
                if values[i][self.__features.index("y")] < 0:
                    x_of_vehicle_i = values[i][self.__features.index("x")]
                    if -self.minimum_distance <= x_of_vehicle_i <= self.minimum_distance:
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
        """
        try:
            shortest_distance: float = None
            values = self.__get_values_for_vehicle(vehicle_id)
            for i in range(1, (values.shape[0] - 1)):
                # hier wird auf eine Stelle gerundet, da sonst dieser Vergleich zu ungenau wird und nie eintritt.
                if round(values[i][self.__features.index("y")], 1) == 0:
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
            warnings.warn("The following feature is not observed, which is necessary for the calculation. The return value will always be False. Missing feature:" + str(e))
            return False

    def get_velocity(self, vehicle_id) -> float:
        """
        Ermittelt die Gesamtgeschwindigkeit des übergebenen Fahrzeugs.
        :param vehicle_id: Die ID des Fahrzeugs , für das die Überprüfung durchgeführt werden soll.

        Die Berechnung basiert auf den beiden unabhängigen Geschwindigkeiten vx und vy und werden mittels
        des Satzes von Pythagoras genutzt, um die Gesamtgeschwindigkeit des Fahrzeuges zu berechnen.
        Note: Aktuell wird hier der normalisierte Wert der Geschwindigkeit ermittelt.
        """
        try:
            values = self.__get_values_for_vehicle(vehicle_id)
            vx =  values[0][self.__features.index("vx")]
            vy = values[0][self.__features.index("vy")]
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

if __name__ == '__main__':
    wrapper = ObservationWrapper("Test", ["presence", "x", "y", "vx", "vy", "heading", "cos_h", "sin_h", "cos_d", "sin_d", "long_off", "lat_off", "ang_off"])
    print(wrapper.get_features().index("x"))
    print(wrapper.get_distance_to_front_vehicle(1))