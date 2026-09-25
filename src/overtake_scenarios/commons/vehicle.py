class Vehicle:
    def __init__(self, v_index, env, name=""):
        self.v_index = v_index
        self.env = env
        self.env_vehicle = env.unwrapped.road.vehicles[v_index]
        self.name = name

    def position(self):
        return self.env_vehicle.position  # (x, y)

    def lane_index(self):
        li = self.env_vehicle.lane_index
        # Falls die lane_index als Tuple zurückkommt, verwende den dritten Wert
        if isinstance(li, tuple):
            return li[2]
        return li

    def speed(self):
        return self.env_vehicle.speed

    def is_behind(self, other, margin=0.0):
        return self.position()[0] + margin < other.position()[0]
