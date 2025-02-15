import unittest
from typing import List, Tuple

from demo_overtaking import check_action_for_vehicle


class TestOvertaking(unittest.TestCase):

    def test_check_action_for_vehicle(self):
        test_cases: List[Tuple[List[float], List[float], float, int]] = [
            ([0, 50, 8, 20], [0, 30, 8, 25], 4.0, 0),  # Overtake to the left
            ([0, 50, 2, 20], [0, 30, 2, 22], 4.0, 2),  # Overtake to the right
            ([0, 107, 8, 20], [0, 30, 8, 20], 4.0, 3),  # Speed up
            ([0, 50, 8, 20], [0, 45, 8, 26], 4.0, 4),  # Maintain speed
            ([0, 50, 8, 20], [0, 60, 8, 20], 4.0, 1),  # Idle
        ]

        for current_vehicle, ego_vehicle, lane_width, expected in test_cases:
            with self.subTest(current_vehicle=current_vehicle, ego_vehicle=ego_vehicle, lane_width=lane_width):
                self.assertEqual(check_action_for_vehicle(current_vehicle, ego_vehicle, lane_width), expected)

if __name__ == "__main__":
    unittest.main()