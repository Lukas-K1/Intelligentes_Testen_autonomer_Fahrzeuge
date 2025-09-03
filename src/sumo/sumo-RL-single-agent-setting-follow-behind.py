import os
import sys
import time

import gymnasium as gym
import register_env
import traci
from bppy import *
from gymnasium.spaces import Box
from z3 import *

from src.sumo.action_enum import *
from src.sumo.sumo_vehicle import *

# Create symbolic variables that can take any value from the Actions enum (for SMT-based events in BPpy)
v1_action = Const("v1_action", Actions)
v2_action = Const("v2_action", Actions)

# action_vars = [v1_action, v2_action]
action_vars = [v1_action]


v1: SumoControllableVehicle = SumoControllableVehicle(
    "veh_manual_1",
    ["entry", "longEdge", "exit"],
    typeID="manual",
    depart_time=0,
    depart_pos=30.0,
    depart_lane=1,
    depart_speed="avg",
    vehicle_color=(255, 0, 0),  # red
    lane_change_mode=0,
    speed_mode=0,
    vehicle_smt_var=v1_action,
)

controllable_vehicles = [v1]
vut: SumoVehicle = SumoVehicle("vut")

config_path = "../../sumo-maps/autobahn/autobahn.sumocfg"
driving_env = gym.make("SumoEnv-v0", sumo_config_file=config_path, controllable_vehicles=[v1])
driving_env.reset()

action_map = {LANE_LEFT: 0, IDLE: 1, LANE_RIGHT: 2, FASTER: 3, SLOWER: 4}


def wait_seconds(seconds):
    step_count_t0 = step_count
    target_step_count = int(seconds / 0.05) + step_count
    while step_count < target_step_count:
        print(f"waited {(step_count - step_count_t0) * 0.05} seconds.")
        yield sync(request=True)


def seconds(steps):
    return steps * 0.05


step_count = 0


def fall_behind(
    behind_vehicle: SumoControllableVehicle,
    in_front_vehicle: SumoVehicle,
    min_distance=25.0,
    max_duration=float("inf"),
):
    global step_count
    step_count_t0 = step_count
    while not behind_vehicle.is_behind_by_x(in_front_vehicle, min_distance):
        # behind_vehicle must slow down, but only until it is 2.0 slower than in_front_vehicle
        if behind_vehicle.speed() + 2.0 > in_front_vehicle.speed():
            #yield sync(request= v1_action == SLOWER)
            yield sync(request=behind_vehicle.SLOWER())
        elif behind_vehicle.speed() - 2.0 < in_front_vehicle.speed():
            yield sync(request=behind_vehicle.FASTER())
        else:
            yield sync(request=behind_vehicle.IDLE())
        if seconds(step_count - step_count_t0) >= max_duration:
            print("TIMED INTERRUPT")
            break


def change_to_same_lane(
    vehicle_to_change_lane: SumoControllableVehicle, other_vehicle: SumoVehicle
):
    while vehicle_to_change_lane.lane_index() != other_vehicle.lane_index():
        if vehicle_to_change_lane.lane_index() < other_vehicle.lane_index():
            yield sync(request=vehicle_to_change_lane.LANE_LEFT())
        else:
            yield sync(request=vehicle_to_change_lane.LANE_RIGHT())


def close_distance(
    behind_vehicle: SumoControllableVehicle,
    in_front_vehicle: SumoVehicle,
    max_distance=25.0,
    max_duration=float("inf"),
):
    global step_count
    step_count_t0 = step_count
    while behind_vehicle.is_behind_by_x(in_front_vehicle, max_distance):
        # behind_vehicle must speed up down, but only until it is 2.0 faster than in_front_vehicle
        if behind_vehicle.speed() - 2.0 < in_front_vehicle.speed():
            yield sync(request=behind_vehicle.FASTER())
        elif behind_vehicle.speed() + 2.0 > in_front_vehicle.speed():
            yield sync(request=behind_vehicle.SLOWER())
        else:
            yield sync(request=behind_vehicle.IDLE())
        if seconds(step_count - step_count_t0) >= max_duration:
            print("TIMED INTERRUPT")
            break


def equalize_speeds(
    controllable_vehicle: SumoControllableVehicle, other_vehicle: SumoVehicle
):
    while (
        abs(controllable_vehicle.speed() - other_vehicle.speed()) <= 0.1
        and abs(controllable_vehicle.speed() - other_vehicle.speed()) <= 0.1
    ):
        if controllable_vehicle.speed() > other_vehicle.speed():
            yield sync(request=controllable_vehicle.SLOWER())
        else:
            yield sync(request=controllable_vehicle.FASTER())
        # yield from wait_seconds(0.1)


def get_behind(behind_vehicle: SumoControllableVehicle, in_front_vehicle: SumoVehicle):
    yield from fall_behind(behind_vehicle, in_front_vehicle)
    yield from change_to_same_lane(behind_vehicle, in_front_vehicle)
    yield from close_distance(behind_vehicle, in_front_vehicle)
    yield from equalize_speeds(behind_vehicle, in_front_vehicle)


def stay_behind(behind_vehicle: SumoControllableVehicle, in_front_vehicle: SumoVehicle):
    while True:
        yield from fall_behind(behind_vehicle, in_front_vehicle, 20.0)
        yield from change_to_same_lane(behind_vehicle, in_front_vehicle)
        yield from close_distance(behind_vehicle, in_front_vehicle, 20.0)
        yield from equalize_speeds(behind_vehicle, in_front_vehicle)
        # yield from wait_seconds(0.1)


@thread
def follow_behind(
    behind_vehicle: SumoControllableVehicle,
    in_front_vehicle: SumoVehicle,
    delay_seconds: float = 0.0,
):
    # " serial: "
    # yield from wait_seconds(delay_seconds)
    yield from get_behind(behind_vehicle, in_front_vehicle)
    yield from stay_behind(behind_vehicle, in_front_vehicle)


@thread
def vehicle_follows_vut():
    yield from follow_behind(v1, vut)


def await_condition(
    condition_function, deadline_seconds=float("inf"), local_reward=0.0
) -> Bool:
    global step_count
    step_count_t0 = step_count
    while seconds(step_count - step_count_t0) <= deadline_seconds:
        if condition_function():
            return BoolVal(True)
        yield sync(waitFor=BoolVal(True), localReward=local_reward)
        print(
            f" +++  waited {seconds(step_count-step_count_t0)} seconds for condition."
        )
    return BoolVal(False)


@thread
def abstract_scenario_2():
    # cond 1.
    satisfied = yield from await_condition(
        lambda: v1.is_behind_by_x(vut), local_reward=10.0
    )
    if not satisfied:
        print("################ UNSAT")
        return
    else:
        print("################ COND 1 SAT")
    # cond 2.
    satisfied = yield from await_condition(
        lambda: v1.lane_index() == vut.lane_index(), local_reward=10.0
    )
    if not satisfied:
        print("################ UNSAT")  # -> local_reward = -100.0 ???
        return
    else:
        print("################ COND 2 SAT")


# def parallel(*bthreads):
#     for bt in bthreads:
#         b_program.add_bthread(bt)
#     yield sync(waitFor=true)  # needs to be here, otherwise there might be problem w


@thread
def sumo_env_bthread():
    global step_count
    while True:
        # set vehicle_id to one of in this scenario to let it the gui follow that vehicle
        # vut, veh_manual_1, veh_manual_2
        traci.gui.trackVehicle("View #0", "veh_manual_1")
        collisions = traci.simulation.getCollisions()
        if collisions:
            print("Collision detected! Exiting simulation...")
            traci.close()
            raise SystemExit()

        e = yield sync(waitFor=BoolVal(True))

        actions = []
        for vehicle in controllable_vehicles:
            action_vehicle = e.eval(vehicle.vehicle_smt_var)
            if action_vehicle in action_map:
                actions.append(action_map[action_vehicle])
            else:
                actions.append(4)  # default is IDLE
        actions_tuple = tuple(actions)

        print(f"actions_tuple: {actions_tuple}")
        obs, reward, truncated, terminated, _ = driving_env.step(actions_tuple)
        print(f"OBSERVATION in step {step_count}: {obs}")
        step_count += 1


# if __name__ == "__main__":
#     # setup_sumo_connection(config_path)
#     # setup_sumo_vehicles()
#     # Creating a BProgram with the defined b-threads, SMTEventSelectionStrategy,
#     # and a listener to print the selected events
#     b_program = BProgram(
#         bthreads=[sumo_env_bthread(),
#                   vehicle_follows_vut(), # concrete scenarios / manually crafted implementation -> to be learned by RL
#                   abstract_scenario_2()], # abstract scenarios / declarative / spec / target / rewards
#         event_selection_strategy=SMTEventSelectionStrategy(),
#         listener=PrintBProgramRunnerListener(),
#     )
#     b_program.run()


import numpy as np


class BPObservationSpaceBox(Box):
    """
    A base class used to represent a BProgram-based continuous-valued observation space. This is an abstract class
    that requires the implementation of `bp_state_to_gym_space` methods.
    """

    @property
    def np_random(self):
        return super().np_random

    @property
    def shape(self):
        return super().shape

    def sample(self):
        pass

    def seed(self, seed=None):
        return super().seed(seed)

    def contains(self, x):
        pass

    def __contains__(self, x):
        return super().__contains__(x)

    def __setstate__(self, state):
        super().__setstate__(state)

    def to_jsonable(self, sample_n):
        return super().to_jsonable(sample_n)

    def from_jsonable(self, sample_n):
        return super().from_jsonable(sample_n)

    def bp_state_to_gym_space(self, bthreads_states):
        """
        Abstract method that transforms the bprogram's state, received as a list of bthreads statements, to a gym space
        representation.
        """
        raise NotImplementedError("bp_state_to_gym_space not implemented")


# ---- Normalization parameters (tweak to taste) ----
_POS_RANGE_M = 100.0  # +/- meters around the env vehicle are mapped to [-1, 1]
_SPEED_RANGE = 30.0  # +/- m/s relative speed mapped to [-1, 1]
_ENV_IDX = 1  # <-- you said the second row is the env vehicle


def _clip_div(value: np.ndarray, max_abs: float) -> np.ndarray:
    """Scale to [-1, 1] by dividing with max_abs and clipping."""
    if max_abs <= 0:
        raise ValueError("max_abs must be positive")
    return np.clip(value / max_abs, -1.0, 1.0)


def _make_relative(obs: np.ndarray, env_idx: int) -> np.ndarray:
    """
    Make all vehicles relative to the env vehicle's state.
    Assumes rows are vehicles; columns are [speed, x, y].
    After this, env row becomes [0, 0, 0].
    """
    if obs.ndim != 2 or obs.shape[1] < 3:
        raise ValueError(f"Expected obs shape [N, >=3], got {obs.shape}")
    if not (0 <= env_idx < obs.shape[0]):
        raise IndexError(f"env_idx {env_idx} out of bounds for {obs.shape[0]} vehicles")

    env_speed = obs[env_idx, 0]
    env_pos = obs[env_idx, 1:3]  # [x, y]

    rel = obs.copy()
    rel[:, 0] = rel[:, 0] - env_speed  # relative speed
    rel[:, 1:3] = rel[:, 1:3] - env_pos[None]  # relative position
    return rel


def _normalize_rel_obs(rel_obs: np.ndarray) -> np.ndarray:
    """
    Normalize columns: speed -> [-1,1] via _SPEED_RANGE, x/y -> [-1,1] via _POS_RANGE_M.
    Values beyond range are clipped.
    """
    out = rel_obs.astype(np.float32, copy=True)
    out[:, 0] = _clip_div(out[:, 0], _SPEED_RANGE)  # v_rel
    out[:, 1] = _clip_div(out[:, 1], _POS_RANGE_M)  # x_rel
    out[:, 2] = _clip_div(out[:, 2], _POS_RANGE_M)  # y_rel
    return out


def _extract_obs_or_none(bthreads_states):
    """Return first valid ndarray from a bthread local 'obs', else None."""
    for bt in bthreads_states:
        loc = bt.get("locals", {})
        arr = loc.get("obs", None)
        if isinstance(arr, np.ndarray) and arr.ndim == 2 and arr.shape[1] >= 3:
            return arr
    return None


class SumoObservationSpace(BPObservationSpaceBox):
    def __init__(self, dim: tuple[int, int]):
        # normalized to [-1, 1], fixed shape = (num_vehicles, 3)
        super().__init__(low=-1.0, high=1.0, shape=dim, dtype=np.float32)

    def bp_state_to_gym_space(self, bthreads_states):
        # 1) extract raw obs from the bprogram state
        obs = _extract_obs_or_none(bthreads_states)
        if obs is None or obs.size == 0:
            return np.zeros(self.shape, dtype=np.float32)
        # obs is expected as ndarray [[speed, x, y], ...]

        # 2) recenter/relative to env vehicle
        rel_obs = _make_relative(obs, env_idx=_ENV_IDX)

        # 3) normalize and clip to [-1, 1]
        norm_obs = _normalize_rel_obs(rel_obs)

        return norm_obs


from bp_env_smt import BPActionSpace, BPEnvSMT


def init_bprogram():
    return BProgram(
        bthreads=[
            sumo_env_bthread(),
            # vehicle_follows_vut(), # commented out -> this behavior should be learned.
            abstract_scenario_2(),
        ],
        event_selection_strategy=SMTEventSelectionStrategy(),
        listener=PrintBProgramRunnerListener(),
    )


from itertools import product

from z3 import And


action_list = None

def get_action_list():
    """
    Build the list of joint-action SMT conditions for all vehicles in `action_vars`.
    For a single vehicle, returns:
        [v1_action == LANE_LEFT, v1_action == IDLE, ...]
    For multiple vehicles, returns conjunctions over the Cartesian product, e.g.:
        [ And(v1_action == LANE_LEFT, v2_action == LANE_LEFT),
          And(v1_action == LANE_LEFT, v2_action == IDLE),
          ... ]
    """
    global action_list
    if action_list != None:
        return action_list

    num_vehicles = len(action_vars)
    if num_vehicles == 0:
        return []

    act_consts = [LANE_LEFT, IDLE, LANE_RIGHT, FASTER, SLOWER]

    # Per-vehicle choice lists: [[v1==LL, v1==IDLE, ...], [v2==LL, v2==IDLE, ...], ...]
    per_vehicle_choices = [
        [action_vars[i] == a for a in act_consts] for i in range(num_vehicles)
    ]

    joint_actions = []
    for combo in product(*per_vehicle_choices):
        if num_vehicles == 1:
            joint_actions.append(combo[0])
        else:
            joint_actions.append(And(*combo))


    print(f"joint_actions: {joint_actions}")
    for a in joint_actions:
        print(f"type of {a} is {type(a)}")

    action_list = joint_actions
    return joint_actions


def calc_dim(features_per_vehicle: int = 3) -> tuple[int, int]:
    if features_per_vehicle <= 0:
        raise ValueError("features_per_vehicle must be positive")

    # Uses the global `action_vars` list of controllable vehicles
    num_agent_controlled_vehicles = len(action_vars)
    num_vehicles = 1 + num_agent_controlled_vehicles
    return (num_vehicles, features_per_vehicle)


env = BPEnvSMT(
    bprogram_generator=lambda: init_bprogram(),
    # TODO: write a function that returns a list of actions
    action_list=get_action_list(),  # num_nonVUT_vehicles: number of agent-controlled vehicles, VUT is uncontrollable
    observation_space=SumoObservationSpace(dim=calc_dim()),
    reward_function=lambda rewards: sum(filter(None, rewards)),
    steps_per_episode=500
)

from gymnasium.spaces import Discrete

env.action_space = Discrete(len(env.event_list))

import argparse
import json
import shutil
from glob import glob

import pandas as pd
from stable_baselines3.common.monitor import Monitor, load_results

parser = argparse.ArgumentParser()
parser.add_argument(
    "steps", type=int, nargs="?", default=1000, help="Number of training timesteps"
)
args = parser.parse_args()

STEPS = args.steps

log_dir = f"output/{STEPS}/"


if os.path.exists(log_dir) and os.path.isdir(log_dir):
    shutil.rmtree(log_dir)
with warnings.catch_warnings():
    from stable_baselines3 import PPO

    env = Monitor(env, log_dir)
    os.makedirs(log_dir, exist_ok=True)
    mdl = PPO("MlpPolicy", env, verbose=1)
    mdl.learn(total_timesteps=STEPS)


def load_results(path):
    monitor_files = glob(os.path.join(path, ".*")) + glob(os.path.join(path, "*"))
    data_frames, headers = [], []
    for file_name in monitor_files:
        with open(file_name) as file_handler:
            first_line = file_handler.readline()
            assert first_line[0] == "#"
            header = json.loads(first_line[1:])
            data_frame = pd.read_csv(file_handler, index_col=None)
            headers.append(header)
            data_frame["t"] += header["t_start"]
        data_frames.append(data_frame)
    data_frame = pd.concat(data_frames)
    data_frame.sort_values("t", inplace=True)
    data_frame.reset_index(inplace=True)
    data_frame["t"] -= min(header["t_start"] for header in headers)
    return data_frame


results = load_results(log_dir)
results["episode"] = results["index"] + 1
results["timesteps"] = results["episode"] * results["l"]
results["mean_reward"] = results["r"][::-1].rolling(200, min_periods=1).mean()[::-1]
results[["episode", "l", "timesteps", "r", "mean_reward"]].to_csv(
    os.path.join(log_dir, "results.csv"), index=False
)
print("results saved to", os.path.join(log_dir, "results.csv"))
