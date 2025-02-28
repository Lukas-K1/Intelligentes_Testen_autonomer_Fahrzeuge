import os

import numpy as np
from datetime import datetime


def generate_filename(base_name: str, extension: str, directory : str) -> str:
    """
    Generiert einen Dateinamen mit dem aktuellen Timestamp.

    :param directory: Verzeichnis der Datei
    :param base_name: Name der Datei.
    :param extension: Der Dateityp.
    :return: String, der den Dateinamen enthält .
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{base_name}_{timestamp}.{extension}"
    return os.path.join(directory, filename)


class ObservationLogger:
    """
    Klasse zum Speichern von Observations in einer Datei. Sollte nach jedem Step einmal aufgerufen werden.
    Standardmäßig wird die Datei im resources/logs Verzeichnis gespeichert. Existiert dieses nicht, wird es erzeugt.
    Die Daten werden im CSV-Format gespeichert. Der aktuelle Step wird mit gespeichert.

    Note: Kann mit der reset() Methode zurückgesetzt werden.

    :param directory: Verzeichnis, in dem die Datei gespeichert wird.
    :param format_of_coordinates: Formatierung der Koordinaten in der Observation.
    """

    def __init__(self, directory: str = "resources/logs", format_of_coordinates: str = "%.6f"):
        # Ensure the directory exists
        os.makedirs(directory, exist_ok=True)
        self.filename = generate_filename("simulation_log", "csv", directory)
        self.step_count = 0
        self.format = format_of_coordinates

    def reset(self):
        self.__init__()

    def save_observation(self, observation):
        """
        Speichert die Observation in einer Datei. Neue Einträge werden über eine neue Zeile separiert und den aktuellen
        Step separiert.

        :param observation: Die Observation.
        """

        matrix = np.asmatrix(observation[0])

        with open(self.filename, 'a') as f:
            f.write("Step " + str(self.step_count) + ": \n")
            self.step_count += 1
            np.savetxt(f, matrix, newline="\n", delimiter=",", fmt=self.format)

    def read_observations(self) -> []:
        """
        Liest die Observations wieder als Matrix aus der Datei ein.

        :return: Die Observation, wie sie gespeichert wurde.
        """
        observations = []
        with open(self.filename, 'r') as f:
            lines = f.readlines()
            current_matrix = []
            for line in lines:
                if line.startswith("Step"):
                    if current_matrix:
                        observations.append(np.array(current_matrix))
                        current_matrix = []
                else:
                    current_matrix.append([float(x) for x in line.strip().split(",")])
            if current_matrix:
                observations.append(np.array(current_matrix))
        return observations