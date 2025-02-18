import unittest
from typing import List, Tuple

import numpy as np

from demo.demo_overtaking_multiagent import decide_action, decide_passiv


class MyTestCase(unittest.TestCase):
    # a nd array containing an example oberservation of the environment
    obs_left = (np.array([
        [1., 55, 8, 25],
        [1., 75, 8, 20]], dtype=np.float32),
                np.array([
                    [1., 75, 8, 20],
                    [1., 55, 8, 25]], dtype=np.float32))

    # unit test cases for mutliagent overtake scenario
    def test_decide_action_left(self):
        self.assertEqual(0, decide_action(self.obs_left[0], 4.0))

    def test_decide_action_right(self):
        obs = (np.array([
            [1., 30, 2, 22],
            [1., 40, 2, 20]], dtype=np.float32),
               np.array([
                   [1., 40, 2, 20],
                   [1., 30, 2, 22]], dtype=np.float32))
        self.assertEqual(2, decide_action(obs[0], 4.0))

    def test_decide_action_speed_up(self):
        obs = (np.array([
            [1., 107, 8, 20],
            [1., 30, 8, 20]], dtype=np.float32),
               np.array([
                   [1., 30, 8, 20],
                   [1., 107, 8, 20]], dtype=np.float32))
        self.assertEqual(3, decide_action(obs[0], 4.0))

    def test_decide_action_maintain_speed(self):
        obs = (np.array([
            [1., 50, 8, 20],
            [1., 45, 8, 26]], dtype=np.float32),
               np.array([
                   [1., 45, 8, 26],
                   [1., 50, 8, 20]], dtype=np.float32))
        self.assertEqual(4, decide_action(obs[0], 4.0))

    def test_decide_action_idle(self):
        obs = (np.array([
            [1., 50, 8, 20],
            [1., 70, 4, 20]], dtype=np.float32),
               np.array([
                   [1., 70, 4, 20],
                   [1., 50, 8, 20]], dtype=np.float32))
        self.assertEqual(1, decide_action(obs[0], 4.0))


    def test_decide_passiv_speed_up(self):
        obs = (np.array([
            [1., 107, 8, 20],
            [1., 30, 8, 20]], dtype=np.float32),
               np.array([
                   [1., 30, 8, 20],
                   [1., 107, 8, 20]], dtype=np.float32))
        self.assertEqual(3, decide_passiv(obs[1], 4.0))

    def test_decide_passiv_maintain_speed(self):
        obs = (np.array([
            [1., 50, 8, 20],
            [1., 45, 8, 26]], dtype=np.float32),
               np.array([
                   [1., 45, 8, 26],
                   [1., 50, 8, 20]], dtype=np.float32))
        self.assertEqual(4, decide_passiv(obs[1], 4.0))

    def test_decide_passiv_idle(self):
        obs = (np.array([
            [1., 50, 8, 20],
            [1., 61, 12, 20]], dtype=np.float32),
               np.array([
                   [1., 61, 12, 20],
                   [1., 50, 8, 20]], dtype=np.float32))
        self.assertEqual(1, decide_passiv(obs[1], 4.0))


if __name__ == '__main__':
    unittest.main()
