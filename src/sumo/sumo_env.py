import os
import re
import subprocess
import sys
import time
from typing import Optional, Tuple

import gymnasium as gym
import numpy as np
import traci
from gymnasium import spaces

from src.sumo.sumo_vehicle import SumoVehicle


class SumoEnv(gym.Env):
    def __init__(self, sumo_config_file: str, controllable_vehicles: list[SumoVehicle]):
        # hier Sumo Setup machen initialisieren
        # wie wo welche Autos sein sollen etc.
        self.sumo_config_file = sumo_config_file
        self.controllable_vehicles = controllable_vehicles
        self.observation_space = spaces.Box(
            low=0, high=1e3, shape=(20, 5), dtype=np.float32
        )
        self.action_space = spaces.MultiDiscrete([5] * len(self.controllable_vehicles))
        self.episode = 0
        self.step_count = 0
        self.max_steps = 1000

    def _start_simulation(self, sumo_gui: bool = True):
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
        sumo_bin_path = os.path.join(os.environ["SUMO_HOME"], "bin", sumo_bin)

        if not os.path.isfile(sumo_bin_path):
            sys.exit(f"SUMO executable not found at: {sumo_bin_path}")

        # Append tools path for traci import
        tools = os.path.join(os.environ["SUMO_HOME"], "tools")
        sys.path.append(tools)

        sumo_config = [
            sumo_bin_path,
            "-c",
            self.sumo_config_file,
            "--step-length",
            "0.05",
            "--delay",
            "1000",
            "--lateral-resolution",
            "0.1",
            "--collision.action",
            "warn",
            "--time-to-teleport",
            "-1",
            "--start",
            "--quit-on-end",
        ]

        traci.start(sumo_config)
        traci.gui.setZoom("View #0", 600)
        traci.gui.setOffset("View #0", -100, -196)

    def build_vehicles(self):
        """
        Build and add vehicles to the simulation.
        :return:
        """
        # TODO: put it in the SumoVehicle class and make it a method
        # TODO: find a way to not have the vut vehicle hardcoded here, maybe in a .rou file, but it will only spawned after
        # the first step, so we need to add it manually here (for now?)
        route_edges = ["entry", "longEdge", "exit"]
        traci.vehicle.addFull(
            vehID="vut",
            routeID="",  # We'll assign edges manually
            typeID="vut",
            depart=0,
            departPos=15.0,  # 15 meters into the entry edge
            departLane=0,
            departSpeed="avg",
        )
        # Disable lane changes for manual vehicle
        traci.vehicle.setRoute("vut", route_edges)
        traci.vehicle.setColor("vut", [0, 0, 255])

        for vehicle in self.controllable_vehicles:
            traci.vehicle.addFull(
                vehID=vehicle.vehicle_id,
                routeID="",
                typeID=vehicle.typeID,
                depart=vehicle.depart_time,
                departPos=vehicle.depart_pos,
                departLane=vehicle.depart_lane,
                departSpeed=vehicle.depart_speed,
            )
            traci.vehicle.setRoute(vehicle.vehicle_id, vehicle.route_edges)
            traci.vehicle.setColor(vehicle.vehicle_id, vehicle.vehicle_color)
            traci.vehicle.setLaneChangeMode(
                vehicle.vehicle_id, vehicle.lane_change_mode
            )
            traci.vehicle.setSpeedMode(vehicle.vehicle_id, vehicle.speed_mode)

    def reset(self, seed: Optional[int] = None, **kwargs):
        if self.episode != 0:
            self.close()
        self.episode += 1

        if seed is not None:
            self.sumo_seed = seed
        self._start_simulation()
        self.build_vehicles()
        # Wait for the simulation to start, finish setting up vehicles, etc.
        time.sleep(2)

    def step(self, action):
        self._apply_action(action)
        traci.simulationStep()
        self.step_count += 1

        obs = self._get_obs()
        reward = self._get_reward()
        terminated = self.step_count >= self.max_steps
        truncated = False

        return obs, reward, terminated, truncated, {}

    def _apply_action(self, action):
        for i, vehicle in enumerate(self.controllable_vehicles):
            vehicle_id = vehicle.vehicle_id
            speed = traci.vehicle.getSpeed(vehicle_id)
            if action[i] == 0:
                if 0 <= traci.vehicle.getLaneIndex(vehicle_id) + 1 < 3:
                    traci.vehicle.changeLane(
                        vehicle_id, traci.vehicle.getLaneIndex(vehicle_id) + 1, 1
                    )
            elif action[i] == 1:
                traci.vehicle.setSpeed(
                    vehicle_id, speed
                )  # Idle action, maintain current speed
            elif action[i] == 2:
                if 0 <= traci.vehicle.getLaneIndex(vehicle_id) - 1 < 3:
                    traci.vehicle.changeLane(
                        vehicle_id, traci.vehicle.getLaneIndex(vehicle_id) - 1, 1
                    )
            elif action[i] == 3:
                traci.vehicle.setSpeed(vehicle_id, speed + 1)
            elif action[i] == 4:
                traci.vehicle.setSpeed(vehicle_id, max(0, speed - 1))

    def _get_obs(self) -> np.ndarray:
        obs = []

        for veh_id in traci.vehicle.getIDList():
            try:
                speed = traci.vehicle.getSpeed(veh_id)
                position = traci.vehicle.getPosition(veh_id)

                # Optional: include ID hash or vehicle role
                obs.append([speed, *position])

            except traci.TraCIException:
                obs.append([0.0, 0.0, 0.0, 0.0])  # or np.zeros(4)

        return np.array(obs, dtype=np.float32)

    def get_lane_number(lane_id: str) -> Optional[int]:
        import re
        match = re.search(r"_(\d+)$", lane_id)
        return int(match.group(1)) if match else None

    def _get_reward(self):
        return 1

    def _get_info(self):
        # TODO: Implement info logic
        pass

    def render(self):
        # TODO: Implement rendering logic
        pass

    def _render_frame(self):
        # TODO: Implement frame rendering logic
        pass

    def close(self):
        traci.close()
