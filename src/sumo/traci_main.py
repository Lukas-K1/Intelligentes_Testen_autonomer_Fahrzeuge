import os
import sys

import traci


def setup_sumo_connection(config_path: str, sumo_gui=True):
    """
    Setup and start the SUMO-traci connection.

    Args:
        config_path (str): Path to the .sumocfg file, to set up the simulation environment.
        sumo_gui (bool): Whether to run sumo-gui or just sumo in command line.
    """
    # Check SUMO_HOME environment
    if "SUMO_HOME" not in os.environ:
        sys.exit("Please declare environment variable 'SUMO_HOME'")

    sumo_bin = "sumo-gui" if sumo_gui else "sumo"
    sumo_bin += ".exe" if sys.platform == "win32" else ""
    sumo_bin_path = os.path.join(os.environ["SUMO_HOME"], "bin", sumo_bin)

    if not os.path.isfile(sumo_bin_path):
        sys.exit(f"SUMO executable not found at: {sumo_bin_path}")

    # Append tools path for traci import
    tools = os.path.join(os.environ["SUMO_HOME"], "tools")
    sys.path.append(tools)

    sumo_config = [
        sumo_bin_path,
        "-c",
        config_path,
        "--step-length",
        "0.05",
        "--delay",
        "1000",
        "--lateral-resolution",
        "0.1",
    ]

    traci.start(sumo_config)
    traci.gui.setZoom("View #0", 600)
    traci.gui.setOffset("View #0", -100, -196)


if __name__ == "__main__":
    """
    IMPORTANT:
    Before running this script, ensure that the environment variable SUMO_HOME
    is correctly set in your system or your IDE's run configuration.

    In PyCharm:
    - Go to Run > Edit Configurations...
    - Select your run configuration
    - Add SUMO_HOME with the path to your SUMO installation under Environment variables

    Example (bash/zsh):
    export SUMO_HOME=/path/to/your/sumo-installation
    """

    vehicle_id = "normal.0"
    config_path = "../../sumo-maps/autobahn/autobahn.sumocfg"  # for an autobahn network

    setup_sumo_connection(config_path)

    step_count = 0
    vehicle_speed = 0
    total_speed = 0

    route_edges = ["entry", "longEdge", "exit"]  # Same as in your flow
    traci.vehicle.addFull(
        vehID="veh_manual_1",
        routeID="",  # We'll assign edges manually
        typeID="manual",
        depart=0,
        departPos=10.0,  # 10 meters into the entry edge
        departLane=1,
        departSpeed=14.15,
    )
    traci.vehicle.setRoute("veh_manual_1", route_edges)

    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        step_count += 1

        if vehicle_id in traci.vehicle.getIDList():
            vehicle_speed = traci.vehicle.getSpeed(vehicle_id)

        if step_count == 10:
            traci.vehicle.changeLane(vehicle_id, laneIndex=1, duration=10)
            traci.vehicle.changeLane("veh_manual_1", laneIndex=0, duration=10)
            traci.vehicle.slowDown(
                "veh_manual_1", 10, 1
            )  # Slow down to 10 m/s over 10 seconds

        print(f"Step {step_count}: Vehicle speed of {vehicle_id}: {vehicle_speed} m/s")
        print(f"Step {step_count}: Vehicle speed of {vehicle_id}: {vehicle_speed} m/s")

    traci.close()
