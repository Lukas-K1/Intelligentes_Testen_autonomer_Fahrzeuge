import gymnasium
import tensorboard
import highway_env
from stable_baselines3 import DQN
'''
env = gymnasium.make("highway-fast-v0")
model = DQN('MlpPolicy', env,
              policy_kwargs=dict(net_arch=[256, 256]),
              learning_rate=5e-4,
              buffer_size=15000,
              learning_starts=200,
              batch_size=32,
              gamma=0.8,
              train_freq=1,
              gradient_steps=1,
              target_update_interval=50,
              verbose=1,
              tensorboard_log="highway-fast_dqn/")
model.learn(int(1e6))
model.save("highway-fast_dqn/model")
'''
# Load and test saved model
model = DQN.load("highway-fast_dqn/model")
env = gymnasium.make('highway-v0', render_mode='rgb_array')
while True:
  done = truncated = False
  obs, info = env.reset()
  while not (done or truncated):
    action, _states = model.predict(obs, deterministic=True)
    obs, reward, done, truncated, info = env.step(action)
    env.render()
