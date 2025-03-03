from observation_wrapper import ObservationWrapper


class ActionWrapper:
    def __init__(self, action):
        self.action = action


    def set_action(self, action):
        self.action = action


    def __getattr__(self, item):
        return getattr(self.action, item)

    def decide_action(self, env, obs, obs_wrapper: ObservationWrapper, v_id: int, space: float) -> int:
        """
        Decides the action to be taken by the vehicle based on the current observation.
        :param obs: the current highway env observation
        :param env: the highway environment
        :param obs_wrapper: The observation wrapper containing functionality based on the current observation
        :param v_id: The id of the vehicle
        :param space: The space needed for changing the lane without collision
        :return: The action to be taken
        """
        istuple = len(obs) >= 2
        is_idm = env.unwrapped.road.vehicles[1].__class__.__name__ == "IDMVehicle"

        if istuple and not is_idm:
            return self.define_multiagent_action(env, obs_wrapper, v_id, space)
        else:
            return self.define_action_nonagent_vut(env, obs_wrapper, v_id, space)


    def define_multiagent_action(self, env, obs_wrapper: ObservationWrapper, v_id: int, space: float) -> int:
        """
        Decides the action to be taken by the vehicle based on the current observation.
        :param env: the highway environment
        :param obs_wrapper: The observation wrapper containing functionality based on the current observation
        :param v_id: The id of the vehicle
        :param space: The space needed for changing the lane without collision
        :return: The action to be taken
        """
        distance = obs_wrapper.get_distance_to_leading_vehicle(v_id)
        right_clear = obs_wrapper.is_right_lane_clear(v_id, space, space)
        left_clear = obs_wrapper.is_left_lane_clear(v_id, space, space)
        same_lane = obs_wrapper.is_in_same_lane(v_id, 1)
        velocity = obs_wrapper.get_velocity(v_id)
        lane = env.unwrapped.road.vehicles[v_id].lane_index
        current_lane = lane[2]
        other_lane_info = env.unwrapped.road.vehicles[1].lane_index[2]
        vehicles = env.unwrapped.road.vehicles
        print(vehicles)

        if distance > 35 and same_lane:
            return 3
        elif 15 > distance > 10 and same_lane and (right_clear or left_clear) and current_lane != 0:
            return 0
        elif 15 > distance > 10 and right_clear and not left_clear and same_lane and current_lane != 3:
            return 2
        elif not right_clear and 15 > distance > 10 and not left_clear and same_lane and (
                current_lane != 0 or current_lane != 3):
            return 4
        elif not right_clear and 15 > distance > 10 and left_clear and same_lane and current_lane != 0:
            return 0
        elif 35 > distance > 10 and same_lane:
            return 1
        elif distance == 0 and right_clear and current_lane - other_lane_info < 0:
            return 2
        elif distance == 0 and right_clear and current_lane - other_lane_info > 0:
            return 0
        elif not same_lane:
            return 1
        elif distance == 0 and not same_lane and right_clear and not left_clear:
            return 2
        elif distance == 0 and not same_lane and left_clear and not right_clear:
            return 0
        elif velocity < 24 and same_lane:
            return 3
        elif 24 < velocity < 28:
            return 1
        elif distance == 0 and same_lane and 30 > velocity > 25:
            return 4
        elif distance < 12 and same_lane:
            return 4
        return 1

    def define_action_nonagent_vut(self, env, obs_wrapper: ObservationWrapper, v_id: int, space: float) -> int:
        """
        Decides the action to be taken by the vehicle based on the current observation.
        :param env: the highway environment
        :param obs_wrapper: The observation wrapper containing functionality based on the current observation
        :param v_id: The id of the vehicle
        :param space: The space to needed for changing the lane without collision
        :return: The action to be taken
        """
        distance = obs_wrapper.get_distance_to_leading_vehicle(v_id)
        right_clear = obs_wrapper.is_right_lane_clear(v_id, space, space)
        print(right_clear)
        left_clear = obs_wrapper.is_left_lane_clear(v_id, space, space)
        print(left_clear)
        velocity = obs_wrapper.get_velocity(v_id)
        lane = env.unwrapped.road.vehicles[v_id].lane_index
        current_lane = lane[2]
        print(current_lane)
        other_lane_info = env.unwrapped.road.vehicles[1].lane_index[2]
        current_vehicle = env.unwrapped.road.vehicles[v_id]
        vehicles = env.unwrapped.road.vehicles
        # print(vehicles)
        road_neighbours = env.unwrapped.road.neighbour_vehicles(current_vehicle)
        print(road_neighbours)

        if distance > 35 and road_neighbours[0] is not None:
            return 3
        elif not right_clear and 15 > distance > 10 and left_clear and road_neighbours[
            0] is not None and current_lane != 0:
            return 0
        elif right_clear and 15 > distance > 10 and left_clear and road_neighbours[0] is not None and current_lane == 0:
            return 2
        elif 15 > distance > 10 and right_clear and not left_clear and road_neighbours[
            0] is not None and current_lane != 3:
            return 2
        elif not right_clear and 15 > distance > 10 and not left_clear and road_neighbours[0] is not None:
            return 4
        elif 35 > distance > 10 and road_neighbours[0] is not None:
            return 1
        elif distance == 0 and right_clear and current_lane - other_lane_info < 0 and current_lane in [2,
                                                                                                       3] and current_lane == 2:
            return 2
        elif distance == 0 and right_clear and current_lane - other_lane_info > 0 and current_lane in [2,
                                                                                                       3] and current_lane == 3:
            return 0
        elif road_neighbours[0] is None:
            return 1
        elif road_neighbours[1] is None and road_neighbours[0] is None:
            return 1
        elif road_neighbours[1] is None and current_lane == 3:
            return 1
        elif distance == 0 and road_neighbours[1] is None and right_clear and not left_clear and current_lane != 3:
            return 2
        elif distance == 0 and road_neighbours[1] is None and left_clear and not right_clear and current_lane != 0:
            return 0
        elif velocity < 24 and road_neighbours[0] is not None:
            return 3
        elif 24 < velocity < 28:
            return 1
        elif distance == 0 and road_neighbours[0] is not None and 30 > velocity > 25:
            return 4
        elif distance < 12 and road_neighbours[0] is not None:
            return 4
        return 1