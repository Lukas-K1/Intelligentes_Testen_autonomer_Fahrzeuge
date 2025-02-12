import unittest

import numpy as np

from src.observation_wrapper import *


class TestObservationWrapper(unittest.TestCase):

    def setUp(self):
        # Mock-Daten vorbereiten
        self.mock_array = (
            np.array([
                [0.35432303, 0.5, 0.3125, 0.0],
                [0.05126785, 0.0, 0.0, 0.0],
                [0.10865711, 0.2073627, -0.0008373, 0.02286064],
                [0.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0]
            ], dtype=np.float32),
            np.array([
                [0.4055909, 0.5, 0.3125, 0.0],
                [-0.05126785, 0.0, 0.0, 0.0],
                [0.05738926, 0.2073627, -0.0008373, 0.02286064],
                [0.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0]
            ], dtype=np.float32),
            np.array([
                [0.46298012, 0.7073627, 0.3116627, 0.02286064],
                [-0.05738926, -0.2073627, 0.0008373, -0.02286064],
                [-0.10865711, -0.2073627, 0.0008373, -0.02286064],
                [0.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0]
            ], dtype=np.float32)
        )
        self.features = ["x", "y", "vx", "vy"]

    # is_left_lane_clear tests
    def test_left_lane_clear(self):
        obs_wrapper = ObservationWrapper(self.mock_array, self.features)
        self.assertTrue(obs_wrapper.is_left_lane_clear(0))

    def test_left_lane_clear_vehicle_not_found(self):
        obs_wrapper = ObservationWrapper(np.array([]), self.features)
        self.assertFalse(obs_wrapper.is_left_lane_clear(1))

    def test_left_lane_clear_feature_missing(self):
        obs_wrapper = ObservationWrapper(self.mock_array, [])
        self.assertFalse(obs_wrapper.is_left_lane_clear(0))

    # is_right_lane_clear tests
    def test_right_lane_clear(self):
        obs_wrapper = ObservationWrapper(self.mock_array, self.features)
        self.assertTrue(obs_wrapper.is_right_lane_clear(0))

    def test_right_lane_clear_vehicle_not_found(self):
        obs_wrapper = ObservationWrapper(np.array([]), self.features)
        self.assertFalse(obs_wrapper.is_right_lane_clear(1))

    def test_right_lane_clear_feature_missing(self):
        obs_wrapper = ObservationWrapper(self.mock_array, [])
        self.assertFalse(obs_wrapper.is_right_lane_clear(0))

    # get_distance_to_leading_vehicle tests
    def test_distance_to_leading_vehicle(self):
        obs_wrapper = ObservationWrapper(self.mock_array, self.features)
        self.assertEqual(0.05126785, obs_wrapper.get_distance_to_leading_vehicle(0))

    def test_distance_to_leading_feature_missing(self):
        obs_wrapper = ObservationWrapper(self.mock_array, [])
        self.assertEqual(0, obs_wrapper.get_distance_to_leading_vehicle(0))

    def test_distance_to_leading_vehicle_not_found(self):
        obs_wrapper = ObservationWrapper(np.array([]), self.features)
        self.assertEqual(0, obs_wrapper.get_distance_to_leading_vehicle(1))

    # get_velocity tests
    def test_get_velocity_vehicle_not_found(self):
        obs_wrapper = ObservationWrapper(np.array([]), self.features)
        self.assertEqual(0, obs_wrapper.get_velocity(1))

    def test_get_velocity_feature_missing(self):
        obs_wrapper = ObservationWrapper(self.mock_array, [])
        self.assertEqual(0, obs_wrapper.get_velocity(0))

if __name__ == '__main__':
    unittest.main()