from bp_env import BPEnv


class BPEnvMask(BPEnv):
    def __init__(self):
        super().__init__()

    def action_masks(self):
        possible_events = self.action_space.possible_actions()
        return [action in possible_events for action in range(self.action_space.n)]