from highway_env.vehicle.behavior import IDMVehicle

def make_idm_vehicle(core_env):
    ego = core_env.unwrapped.vehicle
    idm = IDMVehicle.create_from(ego)
    idm.target_speed = 25.0
    core_env.unwrapped.vehicle = idm
    core_env.unwrapped.controlled_vehicles[0] = idm
    i = core_env.unwrapped.road.vehicles.index(ego)
    core_env.unwrapped.road.vehicles[i] = idm
