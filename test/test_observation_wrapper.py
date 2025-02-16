import unittest

import numpy as np

from src.observation_wrapper import *


class TestObservationWrapper(unittest.TestCase):

    def setUp(self):
        # Mock-Daten vorbereiten
        # sind "echte" Daten, die mittels der reserach observationTesting.py generiert wurden
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

    # angepasste Mock-Daten, um Grenzfälle zu testen
    def obs_with_exactly_minimum_distance(self):
        return (
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
                [0.0250, -0.2073627, -0.0008373, 0.02286064],
                [0.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0]
            ], dtype=np.float32),
            np.array([
                [0.46298012, 0.7073627, 0.3116627, 0.02286064],
                [-0.05738926, -0.2073627, 0.0008373, -0.02286064],
                [-0.0250, -0.2073627, 0.0008373, -0.02286064],
                [0.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0]
            ], dtype=np.float32)
        )

    def obs_with_greater_minimum_distance(self):
        return (
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
                [0.0251, -0.2073627, -0.0008373, 0.02286064],
                [0.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0]
            ], dtype=np.float32),
            np.array([
                [0.46298012, 0.7073627, 0.3116627, 0.02286064],
                [-0.05738926, -0.2073627, 0.0008373, -0.02286064],
                [-0.0251, -0.2073627, 0.0008373, -0.02286064],
                [0.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0]
            ], dtype=np.float32)
        )

    def obs_with_exactly_minimum_distance_y_greater_zero(self):
        return (
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
                [0.0250, 0.2073627, -0.0008373, 0.02286064],
                [0.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0]
            ], dtype=np.float32),
            np.array([
                [0.46298012, 0.7073627, 0.3116627, 0.02286064],
                [-0.05738926, 0.2073627, 0.0008373, -0.02286064],
                [-0.0250, 0.2073627, 0.0008373, -0.02286064],
                [0.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0]
            ], dtype=np.float32)
        )

    def obs_with_greater_minimum_distance_y_greater_zero(self):
        return (
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
                [0.0251, 0.2073627, -0.0008373, 0.02286064],
                [0.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0]
            ], dtype=np.float32),
            np.array([
                [0.46298012, 0.7073627, 0.3116627, 0.02286064],
                [-0.05738926, 0.2073627, 0.0008373, -0.02286064],
                [-0.0251, 0.2073627, 0.0008373, -0.02286064],
                [0.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0]
            ], dtype=np.float32)
        )

    def obs_distance_more_than_one_vehicle_on_same_line(self):
        return (
            np.array([
                [0.35432303, 0.5, 0.3125, 0.0],
                [0.1234, 0.0, 0.0, 0.0],
                [0.05126785, 0.0, -0.0008373, 0.02286064],
                [0.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0]
            ], dtype=np.float32),
            np.array([
                [0.4055909, 0.5, 0.3125, 0.0],
                [-0.05126785, 0.0, 0.0, 0.0],
                [0.0251, 0.0, -0.0008373, 0.02286064],
                [0.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0]
            ], dtype=np.float32),
            np.array([
                [0.46298012, 0.7073627, 0.3116627, 0.02286064],
                [-0.05738926, 0.0123, 0.0008373, -0.02286064],
                [-0.0251, 0.0, 0.0008373, -0.02286064],
                [0.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0]
            ], dtype=np.float32)
        )

    # is_left_lane_clear tests
    def test_left_lane_clear(self):
        obs_wrapper = ObservationWrapper(self.mock_array, self.features)
        self.assertTrue(obs_wrapper.is_left_lane_clear(0))

    def test_left_lane_clear_y_less_than_zero_inside_minimum_distance_interval(self):
        obs_wrapper = ObservationWrapper(self.obs_with_exactly_minimum_distance(), self.features)
        self.assertFalse(obs_wrapper.is_left_lane_clear(2))
        self.assertFalse(obs_wrapper.is_left_lane_clear(1))

    def test_left_lane_clear_y_less_than_zero_minimum_distance_enough(self):
        obs_wrapper = ObservationWrapper(self.obs_with_greater_minimum_distance(), self.features)
        self.assertTrue(obs_wrapper.is_left_lane_clear(2))
        self.assertTrue(obs_wrapper.is_left_lane_clear(1))

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

    # y < 0 test
    def test_left_lane_clear_y_greater_than_zero_inside_minimum_distance_interval(self):
        obs_wrapper = ObservationWrapper(self.obs_with_exactly_minimum_distance_y_greater_zero(), self.features)
        self.assertFalse(obs_wrapper.is_right_lane_clear(2))
        self.assertFalse(obs_wrapper.is_right_lane_clear(1))

    def test_left_lane_clear_y_greater_than_zero_minimum_distance_enough(self):
        obs_wrapper = ObservationWrapper(self.obs_with_greater_minimum_distance_y_greater_zero(), self.features)
        self.assertTrue(obs_wrapper.is_right_lane_clear(2))
        self.assertTrue(obs_wrapper.is_right_lane_clear(1))

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

    def test_distance_one_leading_vehicle_one_behind(self):
        obs_wrapper = ObservationWrapper(self.obs_distance_more_than_one_vehicle_on_same_line(), self.features)
        self.assertEqual(0.0251, obs_wrapper.get_distance_to_leading_vehicle(1))

    def test_distance_no_leading_vehicle(self):
        obs_wrapper = ObservationWrapper(self.obs_distance_more_than_one_vehicle_on_same_line(), self.features)
        self.assertEqual(0, obs_wrapper.get_distance_to_leading_vehicle(2))

    # im Gegensatz zum ersten Test dieser Methode, wird hie explizit getestet, ob auch ein geringerer Wert
    # überschrieben wird, wenn das Vehicle sich in der Observation "hinter" dem anderen Vehicle befindet
    def test_distance_multiple_leading_vehicels(self):
        obs_wrapper = ObservationWrapper(self.obs_distance_more_than_one_vehicle_on_same_line(), self.features)
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

    # test with vx and vy = 0
    def test_get_velocity(self):
        obs_wrapper = ObservationWrapper(self.mock_array, self.features)
        self.assertEqual(0.3125, obs_wrapper.get_velocity(0))

    # test with vx and vy
    def test_get_velocity(self):
        obs_wrapper = ObservationWrapper(self.mock_array, self.features)
        self.assertEqual(0.3125, obs_wrapper.get_velocity(2))

if __name__ == '__main__':
    unittest.main()