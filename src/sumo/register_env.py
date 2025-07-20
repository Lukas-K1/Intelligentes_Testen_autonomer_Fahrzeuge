from gymnasium.envs.registration import register

register(
    id="SumoEnv-v0",  # 👈 how you’ll call it via gym.make
    entry_point="sumo_env:SumoEnv",  # module:class
)