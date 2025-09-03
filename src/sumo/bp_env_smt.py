import warnings

import gymnasium as gym
from bppy import And, Bool, Implies, Int, Not, Or, false, is_true, true
from bppy.gym import BPEnv, BPObservationSpace, SimpleBPObservationSpace
from bppy.utils.z3helper import *

from src.sumo.bp_action_space import BPActionSpace


class BPEnvSMT(BPEnv):
    def __init__(
        self,
        bprogram_generator,
        action_list,
        observation_space=None,
        action_space=None,
        reward_function=None,
        steps_per_episode=None
    ):
        """
        Initializes the BPEnv environment.

        Parameters
        ----------
        bprogram_generator : function
            A function that generates a new instance of the BProgram.
        action_list : list
            List of all events defined as actions.
        observation_space : :class:`BPObservationSpace <bppy.gym.bp_observation_space.BPObservationSpace>`, optional
            Space of possible observations. Defaults to
            :class:`SimpleBPObservationSpace <bppy.gym.simple_bp_observation_space.SimpleBPObservationSpace>`.
        reward_function : function, optional
            A custom function to compute the reward. If not provided, the default reward is the sum of all b-thread
            rewards.
        """
        self.metadata = {}
        self.bprogram = None
        self.bprogram_generator = bprogram_generator
        #self.action_space = BPActionSpace(action_list)
        self.event_list = action_list
        self.reward_function = reward_function
        if self.reward_function is None:
            self.reward_function = lambda rewards: sum(filter(None, rewards))
        self.observation_space = observation_space
        if self.observation_space is None:
            self.observation_space = SimpleBPObservationSpace(
                self.bprogram_generator, action_list
            )
        self.last_state = None
        self.done_flag = Bool("done")
        self.step_count = 0
        self.steps_per_episode = steps_per_episode

    def step(self, action):
        """
        Executes the given action and returns the resulting observation, reward, done flag, and additional information.

        Parameters
        ----------
        action : int
            An index representing the event to be executed.

        Returns
        -------
        observation : object
            The state of the environment after executing the action.
        reward : float
            The reward obtained by executing the action.
        done : bool
            Whether the episode has ended.
        truncated : bool
            Not used for this environment.
        info : dict
            Additional information for debugging.
        """

        print("")
        self.step_count += 1
        print(f"### Called env.step() {self.step_count}, selected action (index) is {action}")
        #print(f"### Called env.step() {self.count}, selected action (index) is {action}, type is {type(action)}")
        #print(f" action space is {self.action_space}")

        if self.bprogram is None:
            raise RuntimeError("You must call reset() before calling step()")
        # if not self.action_space.contains(action):
        #     return self._state(), 0, True, None, {"message": "Last event is disabled"}
        additional_constraint = self.event_list[action]

        #print(f"additional_constraint is : {additional_constraint}")


        # print("action:", additional_constraint)
        model = self.bprogram.event_selection_strategy.select(
            self.bprogram.tickets + [{"request": additional_constraint}]
        )

        def is_done():
            return (is_true(model.evaluate(self.done_flag))
                    or (self.step_count > self.steps_per_episode))

        done = is_done()

        self.bprogram.advance_bthreads(self.bprogram.tickets, model)
        local_reward = self._reward()
        # print("----------------------")
        # print("reward:", local_reward)
        # print("action:", action)
        # print(self._state().reshape((4,4)))
        # print("----------------------")
        while not done and not self._step_done():
            model = self.bprogram.event_selection_strategy.select(
                self.bprogram.tickets + [{"block": additional_constraint}]
            )
            self.bprogram.advance_bthreads(self.bprogram.tickets, model)
            # print(self._state().reshape((4, 4)))
            done = is_done()

        return self._state(), local_reward, done, done, {}



    def reset(self, seed=None, options=None):
        """
        Resets the environment to its initial state.

        Parameters
        ----------
        seed : int, optional
            A seed for the random number generator.
        options : dict, optional
            Additional options for resetting the environment.

        Returns
        -------
        observation : object
            The initial state of the environment.
        info : dict
            Not used for this environment.
        """
        print("### Called env.reset()")
        gym.Env.reset(self, seed=seed, options=options)
        self.bprogram = self.bprogram_generator()
        # if isinstance(self.bprogram.event_selection_strategy, SolverBasedEventSelectionStrategy):
        #     raise NotImplementedError("SolverBasedEventSelectionStrategy is currently not supported")
        #self.action_space.bprogram = self.bprogram
        self.bprogram.setup()
        while not self._step_done():
            model = self.bprogram.event_selection_strategy.select(self.bprogram.tickets)
            self.bprogram.advance_bthreads(self.bprogram.tickets, model)
            # print(self.observation_space.bp_state_to_gym_space(self._bthreads_states()).reshape((4,4)))
        return self.observation_space.bp_state_to_gym_space(self._bthreads_states()), {}

    def render(self, mode="human"):
        """
        Not implemented for this environment.
        """
        raise NotImplementedError()

    def close(self):
        """
        Closes the environment, releasing any resources.
        """
        self.bprogram = None

    def get_state(self):
        """
        Returns the current state of the environment.
        """
        return self._state()

    def _bthreads_states(self):
        return [
            dict([k, v] for k, v in statement.items() if k != "bt")
            for statement in self.bprogram.tickets
        ]

    def _state(self):
        return self.observation_space.bp_state_to_gym_space(self._bthreads_states())

    def _bthreads_rewards(self):
        return [x.get("localReward") for x in self.bprogram.tickets]

    def _reward(self):
        return self.reward_function(self._bthreads_rewards())

    def _step_done(self):
        if any(["request" in x for x in self.bprogram.tickets]):
            # print("step not done")
            return False
        else:
            # print("step done")
            return True
