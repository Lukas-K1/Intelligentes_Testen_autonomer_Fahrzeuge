import io
import unittest

from src.overtake_abstract_checker.demo_scenarios import *
from src.overtake_abstract_checker.overtake_abstract_checker import *


def run_bp_with_simulation(simulation_thread):
    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.INFO)
    logger = logging.getLogger()
    logger.addHandler(handler)

    bthreads = [
        simulation_thread(),
    ]
    bthreads.extend(get_checker_threads())

    bp = BProgram(
        bthreads=bthreads,
        event_selection_strategy=SimpleEventSelectionStrategy(),
    )
    bp.run()

    logger.removeHandler(handler)
    return log_stream.getvalue()


class TestDemoScenarios(unittest.TestCase):

    def test_valid_demo_simulation(self):
        log_output = run_bp_with_simulation(valid_demo_simulation)
        self.assertIn("Position Constraint erfüllt", log_output)
        self.assertIn("Duration Constraint erfüllt", log_output)
        self.assertIn("Functional Action Constraint erfüllt", log_output)
        self.assertIn("Speed Limit Constraint erfüllt", log_output)

    def test_invalid_position_simulation(self):
        log_output = run_bp_with_simulation(invalid_position_simulation)
        self.assertIn("Position Constraint verletzt", log_output)

    def test_invalid_duration_simulation(self):
        log_output = run_bp_with_simulation(invalid_duration_simulation)
        self.assertIn("Duration Constraint verletzt", log_output)

    def test_invalid_functional_action_simulation(self):
        log_output = run_bp_with_simulation(invalid_functional_action_simulation)
        self.assertIn("Functional Action Constraint verletzt", log_output)

    def test_invalid_speed_simulation(self):
        log_output = run_bp_with_simulation(invalid_speed_simulation)
        self.assertIn("Speed Limit Constraint verletzt", log_output)


if __name__ == "__main__":
    unittest.main()
