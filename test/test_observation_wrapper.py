import unittest

import numpy as np

from src.observation_wrapper import *


class TestObservationWrapper(unittest.TestCase):
    # Zwei Vehicles fahren auf der linken Spur 50m auseinander bei gleicher Geschwindigkeit. Ein weiteres Vehicle fährt
    # auf der mittleren Spur 25m vor dem einen und 25m hinter dem anderen, bie gleicher Geschwindigkeit.
    OBS_LEFT_LANE_CLEAR_TEST = (
        np.array([
            [100, 2, 25, 0],
            [-25, -2, 0.0, 0.0],
            [25, -2, 0, 0]
        ], dtype=np.float32),
        np.array([
            [75, 0, 25, 0],
            [25, 2, 0.0, 0.0],
            [50, 0, 0.0, 0.0]
        ], dtype=np.float32),
        np.array([
            [125, 0, 25, 0],
            [-25, -2, 0.0, 0],
            [-50, 0.0, 0.0, 0]
        ], dtype=np.float32)
    )

    # Zwei Vehicles fahren auf der rechten Spur 50m auseinander bei gleicher Geschwindigkeit. Ein weiteres Vehicle fährt
    # auf der mittleren Spur 25m vor dem einen und 25m hinter dem anderen, bie gleicher Geschwindigkeit.
    OBS_RIGHT_LANE_CLEAR_TEST = (
        np.array([
            [100, 2, 25, 0],
            [-25, 4, 0.0, 0.0],
            [25, 4, 0, 0]
        ], dtype=np.float32),
        np.array([
            [75, 4, 25, 0],
            [25, -2, 0.0, 0.0],
            [50, 0, 0.0, 0.0]
        ], dtype=np.float32),
        np.array([
            [125, 4, 25, 0],
            [-25, -2, 0.0, 0],
            [-50, 0, 0.0, 0]
        ], dtype=np.float32)
    )

    # Drei Vehicles fahren auf der rechten bei gleicher Geschwindigkeit. Das hinterste Auto auf der Spur hat einen Abstand
    # von 50m zum nächsten. Dieses hat nur noch einen Abstand von 25m zum vorderen.
    # Ein weiteres Vehicle fährt auf der mittleren Spur.
    OBS_DISTANCE_TO_LEADING_VEHICLE = (
        np.array([
            [100, 2, 25, 0],
            [-25, 4, 0.0, 0.0],
            [25, 4, 0, 0],
            [50, 4, 0, 0]
        ], dtype=np.float32),
        np.array([
            [75, 4, 25, 0],
            [25, -2, 0.0, 0.0],
            [75, 0, 0.0, 0.0],
            [50, 0, 0.0, 0.0]
        ], dtype=np.float32),
        np.array([
            [125, 4, 25, 0],
            [-25, -2, 0.0, 0],
            [-50, 0, 0.0, 0],
            [25, 0, 0, 0]
        ], dtype=np.float32),
        np.array([
            [150, 4, 25, 0],
            [-50, -2, 0.0, 0],
            [-25, 0, 0.0, 0],
            [-75, 0, 0, 0]
        ], dtype=np.float32)
    )

    # is_left_lane_clear tests

    def test_left_lane_clear(self):
        obs_wrapper = ObservationWrapper(self.OBS_LEFT_LANE_CLEAR_TEST)
        self.assertTrue(obs_wrapper.is_left_lane_clear(0,10,10))

    def test_left_lane_both_distances_zero(self):
        obs_wrapper = ObservationWrapper(self.OBS_LEFT_LANE_CLEAR_TEST)
        self.assertFalse(obs_wrapper.is_left_lane_clear(0,0,0))

    def test__left_lane_front_distance_zero(self):
        obs_wrapper = ObservationWrapper(self.OBS_LEFT_LANE_CLEAR_TEST)
        self.assertTrue(obs_wrapper.is_left_lane_clear(0,0,10))

    def test_left_lane_back_distance_zero(self):
        obs_wrapper = ObservationWrapper(self.OBS_LEFT_LANE_CLEAR_TEST)
        self.assertTrue(obs_wrapper.is_left_lane_clear(0,10,0))

    def test_left_lane_edge_distance(self):
        obs_wrapper = ObservationWrapper(self.OBS_LEFT_LANE_CLEAR_TEST)
        self.assertTrue(obs_wrapper.is_left_lane_clear(0,24,24))

    def test_left_lane_exact_distance_between_vehicles(self):
        obs_wrapper = ObservationWrapper(self.OBS_LEFT_LANE_CLEAR_TEST)
        self.assertFalse(obs_wrapper.is_left_lane_clear(0, 25, 25))

    def test_left_lane_edge_distance_greater(self):
        obs_wrapper = ObservationWrapper(self.OBS_LEFT_LANE_CLEAR_TEST)
        self.assertFalse(obs_wrapper.is_left_lane_clear(0,26,26))

    def test_left_lane_edge_distance_front_failed(self):
        obs_wrapper = ObservationWrapper(self.OBS_LEFT_LANE_CLEAR_TEST)
        self.assertFalse(obs_wrapper.is_left_lane_clear(0,26,24))

    def test_left_lane_edge_distance_back_failed(self):
        obs_wrapper = ObservationWrapper(self.OBS_LEFT_LANE_CLEAR_TEST)
        self.assertFalse(obs_wrapper.is_left_lane_clear(0,24,26))

    def test_left_lane_clear_vehicle_not_found(self):
        obs_wrapper = ObservationWrapper(np.array([]))
        self.assertFalse(obs_wrapper.is_left_lane_clear(1, 10, 10))

    # is_right_lane_clear tests

    def test_right_lane_clear(self):
        obs_wrapper = ObservationWrapper(self.OBS_RIGHT_LANE_CLEAR_TEST)
        self.assertTrue(obs_wrapper.is_right_lane_clear(0, 10, 10))

    def test_right_lane_both_distances_zero(self):
        obs_wrapper = ObservationWrapper(self.OBS_RIGHT_LANE_CLEAR_TEST)
        self.assertFalse(obs_wrapper.is_right_lane_clear(0, 0, 0))

    def test_right_lane_front_distance_zero(self):
        obs_wrapper = ObservationWrapper(self.OBS_RIGHT_LANE_CLEAR_TEST)
        self.assertTrue(obs_wrapper.is_right_lane_clear(0, 0, 10))

    def test_right_lane_back_distance_zero(self):
        obs_wrapper = ObservationWrapper(self.OBS_RIGHT_LANE_CLEAR_TEST)
        self.assertTrue(obs_wrapper.is_right_lane_clear(0, 10, 0))

    def test_right_lane_edge_distance(self):
        obs_wrapper = ObservationWrapper(self.OBS_RIGHT_LANE_CLEAR_TEST)
        self.assertTrue(obs_wrapper.is_right_lane_clear(0, 24, 24))

    def test_right_lane_exact_distance_between_vehicles(self):
        obs_wrapper = ObservationWrapper(self.OBS_RIGHT_LANE_CLEAR_TEST)
        self.assertFalse(obs_wrapper.is_right_lane_clear(0, 25, 25))

    def test_right_lane_edge_distance_greater(self):
        obs_wrapper = ObservationWrapper(self.OBS_RIGHT_LANE_CLEAR_TEST)
        self.assertFalse(obs_wrapper.is_right_lane_clear(0, 26, 26))

    def test_right_lane_edge_distance_front_failed(self):
        obs_wrapper = ObservationWrapper(self.OBS_RIGHT_LANE_CLEAR_TEST)
        self.assertFalse(obs_wrapper.is_right_lane_clear(0, 26, 24))

    def test_right_lane_edge_distance_back_failed(self):
        obs_wrapper = ObservationWrapper(self.OBS_RIGHT_LANE_CLEAR_TEST)
        self.assertFalse(obs_wrapper.is_right_lane_clear(0, 24, 26))

    def test_right_lane_clear_vehicle_not_found(self):
        obs_wrapper = ObservationWrapper(np.array([]))
        self.assertFalse(obs_wrapper.is_right_lane_clear(1, 10, 10))

    # get_distance_to_leading_vehicle tests

    def test_distance_no_leading_vehicle(self):
        obs_wrapper = ObservationWrapper(self.OBS_DISTANCE_TO_LEADING_VEHICLE)
        self.assertEqual(0, obs_wrapper.get_distance_to_leading_vehicle(0))

    # testet, ob der kürzeste Weg zum nächsten Fahrzeug genommen wird
    def test_distance_two_leading_vehicles(self):
        obs_wrapper = ObservationWrapper(self.OBS_DISTANCE_TO_LEADING_VEHICLE)
        self.assertEqual(50, obs_wrapper.get_distance_to_leading_vehicle(1))

    # testet, das nicht die Distanz zum hinteren Fahrzeug genommen wird
    def test_distance_in_between_two_vehicles(self):
        obs_wrapper = ObservationWrapper(self.OBS_DISTANCE_TO_LEADING_VEHICLE)
        self.assertEqual(25, obs_wrapper.get_distance_to_leading_vehicle(2))

    # teste, ob erkannt wird, dass kein Fahrzeug vorausfährt, obwohl mehrere auf der gleichen Fahrbahn fahren
    def test_distance_multiple_vehicels_on_same_lane_no_leading(self):
        obs_wrapper = ObservationWrapper(self.OBS_DISTANCE_TO_LEADING_VEHICLE)
        self.assertEqual(0, obs_wrapper.get_distance_to_leading_vehicle(3))

    def test_distance_to_leading_vehicle_not_found(self):
        obs_wrapper = ObservationWrapper(np.array([]))
        self.assertEqual(0, obs_wrapper.get_distance_to_leading_vehicle(1))

    # get_velocity tests
    def test_get_velocity_vehicle_not_found(self):
        obs_wrapper = ObservationWrapper(np.array([]))
        self.assertEqual(0, obs_wrapper.get_velocity(1))

    # test with vx and vy = 0
    def test_get_velocity(self):
        obs_wrapper = ObservationWrapper(self.OBS_LEFT_LANE_CLEAR_TEST)
        self.assertEqual(25, obs_wrapper.get_velocity(0))

    # is_in_same_lane tests
    def test_is_in_same_lane(self):
        obs_wrapper = ObservationWrapper(self.OBS_LEFT_LANE_CLEAR_TEST)
        self.assertTrue(obs_wrapper.is_in_same_lane(1, 2))

    def test_is_not_in_same_lane(self):
        obs_wrapper = ObservationWrapper(self.OBS_LEFT_LANE_CLEAR_TEST)
        self.assertFalse(obs_wrapper.is_in_same_lane(0, 2))

    def test_is_in_same_lane_vehicle_not_found(self):
        obs_wrapper = ObservationWrapper(np.array([]))
        self.assertFalse(obs_wrapper.is_in_same_lane(1, 2))

if __name__ == '__main__':
    unittest.main()