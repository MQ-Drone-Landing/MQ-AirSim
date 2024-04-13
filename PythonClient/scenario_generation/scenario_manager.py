# import rospy
import airsim
import random
import numpy as np
from pyquaternion import Quaternion
import math
import time
import cv2

class ScenarioManager():
    """
    Class for managing scenarios in AirSim simulation.

    Args:
        sim_mode (str): Simulation mode, either 'drone' or 'cv'.
        host_ip (str): IP address of the host machine.

    Attributes:
        sim_mode (str): Simulation mode.
        client (airsim.MultirotorClient or airsim.VehicleClient): AirSim API client.
        current_scenario (None): Current scenario.
        scenario_objects (list): Dynamic scenario objects in the current scenario.

    """

    def __init__(self, sim_mode='drone', host_ip='localhost') -> None:
        """
        Initializes the ScenarioManager object.

        Args:
            sim_mode (str): Simulation mode, either 'drone' or 'cv'.
            host_ip (str): IP address of the host machine.

        """
        self.sim_mode = sim_mode
        if sim_mode == 'cv':
            self.client = airsim.VehicleClient(host_ip)
            # set downward camera
            self.client.simSetCameraPose('0', airsim.Pose(airsim.Vector3r(0, 0, 0),
                                         airsim.to_quaternion(math.radians(-90), 0, 0)))
        else:
            self.client = airsim.MultirotorClient(host_ip)

        self.client.simEnableWeather(True)
        self.current_scenario = None
        self.scenario_objects = []

    def get_objects_pool(self, scenario):
        """
        Get the pool of dynamic objects for a given scenario.

        Args:
            scenario: The scenario for which to get the dynamic objects pool.

        Returns:
            dict: A dictionary containing the dynamic objects pool.

        """
        dynamic_objects_pool = {}
        bps = self.map_config['actor_type'].values()
        for bp in bps:
            obj_pool = {}
            bp_objs = self.client.simListSceneObjects('{}.*'.format(bp))
            for obj_name in bp_objs:
                obj_pose = self.client.simGetObjectPose(obj_name)
                print(obj_name, obj_pose)
                obj_pool[obj_name] = {"pose": obj_pose, "occupied": False}
            dynamic_objects_pool[bp] = obj_pool
        
        return dynamic_objects_pool

    def set_marker(self, marker_pose, marker_name='cube_marker0_13'):
        """
        Set the pose of a marker object.

        Args:
            scenario_pose: The pose of the scenario.
            marker_name (str): The name of the marker object.

        Returns:
            airsim.Pose: The pose of the marker object.

        """

        success = self.client.simSetObjectPose(marker_name, marker_pose)
        if success:
            print('set marker {} at ({}, {}, {}) successfully'.format(marker_name, marker_pose.position.x_val,
                    marker_pose.position.y_val, marker_pose.position.z_val))
            
        marker_pose = self.client.simGetObjectPose(marker_name)
        return marker_pose

    def set_weather(self, params):
        """
        Set the weather parameters in the simulation.

        Args:
            params (list): List of weather parameters.

        """
        self.client.simSetWeatherParameter(airsim.WeatherParameter.Rain, min(1, params[0]))
        self.client.simSetWeatherParameter(airsim.WeatherParameter.Roadwetness, min(1, params[1]))
        self.client.simSetWeatherParameter(airsim.WeatherParameter.Snow, min(1, params[2]))
        self.client.simSetWeatherParameter(airsim.WeatherParameter.RoadSnow, min(1, params[3]))
        self.client.simSetWeatherParameter(airsim.WeatherParameter.MapleLeaf, min(1, params[4]))
        self.client.simSetWeatherParameter(airsim.WeatherParameter.RoadLeaf, min(1, params[5]))
        self.client.simSetWeatherParameter(airsim.WeatherParameter.Dust, min(1, params[6]))
        self.client.simSetWeatherParameter(airsim.WeatherParameter.Fog, min(1, params[7])) 
        if self.sim_mode != 'cv':    
            wind = airsim.Vector3r(min(5, params[8]*5), min(5, params[8]*5), 0)
            self.client.simSetWind(wind)

    def reset_npc(self, npc_name):
        """
        Reset the pose of an NPC (non-player character) object.

        Args:
            npc_name (str): The name of the NPC object.

        """
        print('reset npc: ', npc_name)
        success = self.client.simSetObjectPose(npc_name, self.dynamic_objects_pool[npc_name[:-2]][npc_name]['pose'])
        if success:
            print('reset actor {} successfully'.format(npc_name))
            self.dynamic_objects_pool[npc_name[:-2]][npc_name]['occupied'] = False

    def reset_env(self):
        """
        Reset the environment by resetting the dynamic objects and markers.

        """
        for i, obj in enumerate(self.scenario_objects):
            self.reset_npc(obj)
            time.sleep(1)

        self.scenario_objects = []
        markers = ['cube_marker{}'.format(i) for i in range(3)]

        for i, marker in enumerate(markers):
            self.client.simSetObjectPose(marker, airsim.Pose(airsim.Vector3r(100, 100 + 5 * i, 0.5),
             airsim.Quaternionr(w_val=1, x_val=0, y_val=0, z_val=0)))

    def get_current_scene(self, camera_name='0', image_type=0, image_encoding='rgb'):
        """
        Get the current scene from a camera.

        Args:
            camera_name (str): The name of the camera.
            image_type (int): The type of the image.
            image_encoding (str): The encoding of the image.

        Returns:
            numpy.ndarray: The image array.
            airsim.Pose: The pose of the camera.

        """
        if image_type == 0:
            responses = self.client.simGetImages([airsim.ImageRequest(camera_name, image_type, False, False)])
        elif image_type == 5:
            responses = self.client.simGetImages([airsim.ImageRequest(camera_name, image_type, False, False)])

        response = responses[0]
        img1d = np.fromstring(response.image_data_uint8, dtype=np.uint8) 
        img = img1d.reshape(response.height, response.width, 3)
        if image_encoding == 'bgr' and image_type == 0:
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        camera_body_pose = airsim.Pose(response.camera_position, response.camera_orientation)
        
        return img, camera_body_pose

    def get_segmentation_mapping(self):
        """
        Get the segmentation mapping for different objects in the scene.

        Returns:
            dict: A dictionary containing the segmentation mapping.

        """
        colors = {}
        requests = airsim.ImageRequest("0", airsim.ImageType.Segmentation, False, False)

        for cls_id in range(20):
            self.client.simSetSegmentationObjectID(".*", cls_id, is_name_regex=True)
            response = self.client.simGetImages([requests])[0]
            img1d = np.frombuffer(response.image_data_uint8, dtype=np.uint8)
            img_rgb = img1d.reshape(response.height, response.width, 3)

            color = tuple(np.unique(img_rgb.reshape(-1, img_rgb.shape[-1]), axis=0)[0])
            print(f"{cls_id}\t{color}")
            colors[cls_id] = color
        
        return colors

    def set_segmentation(self):
        """
        Set the segmentation for different objects in the scene.

        Returns:
            int: The segmentation ID.

        """
        self.client.simSetSegmentationObjectID("[\w]*", -1, True)

        filtered_objs = ['House', 'Fir', 'Fence', 'Car', 'Power_line', 'Roof', 'Swimming', 'Rock', 'Hedge', 'Wall', 'Tree', 'npc', 'SUV', 'Birch']
        seg_id = 1
        for obj in filtered_objs:
            self.client.simSetSegmentationObjectID("[\w]*{}[\w]*".format(obj), seg_id, True)
            seg_id += 1

        for i in range(4):
            self.client.simSetSegmentationObjectID("cube_marker{}".format(i), seg_id)
        
        return seg_id

    def get_all_npcs(self):
        """
        Get a list of all NPCs (non-player characters) in the scene.

        Returns:
            list: A list of NPC names.

        """
        npcs = self.client.simListSceneObjects('npc*')
        return npcs

    def add_npc(self, npc_type, scenario_pose):
        """
        Add an NPC (non-player character) to the scene.

        Args:
            npc_type (str): The type of the NPC.
            scenario_pose: The pose of the scenario.

        """
        for obj_name, obj_status in self.dynamic_objects_pool[npc_type].items():
            if not obj_status['occupied']:
                pose = airsim.Pose(airsim.Vector3r(scenario_pose.x, scenario_pose.y, -scenario_pose.z))
                success = self.client.simSetObjectPose(obj_name, pose)
                if success:
                    print('add actor {} at ({}, {}, {}) successfully'.format(obj_name, scenario_pose.x,
                            scenario_pose.y, scenario_pose.z))
                    self.scenario_objects.append(obj_name)
                    obj_status['occupied'] = True
                    break
                else:
                    print('failed to add actor {} at ({}, {}, {})'.format(obj_name, scenario_pose.x,
                            scenario_pose.y, scenario_pose.z))
        #     return False, None
        # return obj_name
    
    def set_drone_pose(self, pose):
        if self.sim_mode == 'cv':
            drone_name = ''
        else:
            drone_name = 'Copter'


        self.client.simSetVehiclePose(pose, True, vehicle_name=drone_name)
        if self.sim_mode != 'cv':
            self.client.armDisarm(False)
        return self.client.simGetVehiclePose(drone_name)
        

    def set_npc_pose(self, npc_name, pose):
        # q1 = Quaternion(axis=[0., 0., 1.], angle=scenario_pose.angle)
        # orientation = airsim.Quaternionr(w_val=q1.elements[0], x_val=q1.elements[1], y_val=q1.elements[2], z_val=q1.elements[3])

        # pose = airsim.Pose(airsim.Vector3r(scenario_pose.x, scenario_pose.y, -scenario_pose.z), orientation)
        self.client.simSetObjectPose(npc_name, pose)


    def get_pose(self, obj_name='npc_person_1'):
        # print(npc_name)
        pose = self.client.simGetObjectPose(obj_name)
        # print(pose)
        return pose
    
    def move_npc_to(self, npc_name, pose, speed=0.5):

        # q1 = Quaternion(axis=[0., 0., 1.], angle=angle)
        # orientation = airsim.Quaternionr(w_val=q1.elements[0], x_val=q1.elements[1], y_val=q1.elements[2], z_val=q1.elements[3])
        # pose = airsim.Pose(airsim.Vector3r(scenario_pose.x, scenario_pose.y, -scenario_pose.z), orientation)  
        curernt_pose = self.get_pose(npc_name)

        print("set npc speed: ", speed)
        self.client.simSetNPCSpeed(npc_name, speed)     
        result = self.client.simSetNPCMoveTo(npc_name, pose)
        if result:
            print('{} move to ({} {} {})'.format(npc_name, pose.position.x_val, pose.position.y_val, pose.position.z_val))

    def set_time_of_day(self, params):
        hour, minute = params[0], params[1]
        hour_time = int(hour * 24)
        min_time = int(minute * 60)
        sim_time = '2023-09-06 {}:{}:00'.format(hour_time, min_time)

        self.client.simSetTimeOfDay(True, start_datetime = sim_time, is_start_datetime_dst = True,
         celestial_clock_speed = 1, update_interval_secs = 1, move_sun = True)
    

    def validate_scenario(self, scenario):
        # validate and rectify the scenario in the simulation environment
        # we need to validate whether the markers can be placed on the ground,
        
        # validate_tp_marker
        while True:
            self.set_marker(scenario.tp_marker.pose, marker_name='cube_marker{}'.format(scenario.tp_marker.id))
            time.sleep(3)
            marker_pose = self.get_pose('cube_marker{}'.format(scenario.tp_marker.id))
            if abs(marker_pose.position.z_val) > 1:
                scenario.tp_marker.mutate() 
            else:
                break
        all_marker_pos = []
        pose = self.get_pose('cube_marker{}'.format(scenario.tp_marker.id))
        all_marker_pos.append((pose.position.x_val, pose.position.y_val))
        # set fp_markers
        while len(all_marker_pos) < len(scenario.fp_markers) + 1:
            while True:
                fp_marker = scenario.fp_markers[len(all_marker_pos)]
                self.set_marker(fp_marker.pose, marker_name='cube_marker{}'.format(fp_marker.id))
                time.sleep(3)
                marker_pose = self.get_pose('cube_marker{}'.format(fp_marker.id))
                pos = (marker_pose.position.x_val, marker_pose.position.y_val)
                if abs(marker_pose.position.z_val) > 1:
                    fp_marker.mutate() 
                elif all(distance_2d(pos, marker_pos) > 2 for marker_pos in all_marker_pos):
                    pose = self.get_pose('cube_marker{}'.format(fp_marker.id))
                    all_marker_pos.append(pos)
                    break
        
        return scenario

    def set_scenario(self, scenario):
        self.current_scenario = scenario
        # print('current scenario: ', scenario)


    # set all actors at the initial position
    def load_scenario(self):
        scenario = self.current_scenario

        # set drone pose for cv and simple flight mode
        # if self.sim_mode != 'ardupilot':
        #     if self.sim_mode == 'cv':
        #         self.set_drone_pose(scenario.drone_start_pose)
        #     else:
        #         self.set_drone_pose(scenario.drone_start_pose)
        # create the landing scenario from the scenario configuration
        self.reset_env()
        time.sleep(1)
        self.set_marker(scenario.tp_marker.pose, marker_name='cube_marker{}'.format(scenario.tp_marker.id))
        # time.sleep(3)
        print('set marker at: ', self.get_pose('cube_marker{}'.format(scenario.tp_marker.id)))
        for marker in scenario.fp_markers:
            self.set_marker(marker.pose, marker_name='cube_marker{}'.format(marker.id))
        

        
        # set weather and time
        self.set_weather(scenario.weather.to_vec())
        self.set_time_of_day(scenario.time.to_vec())

        # set dynamic actors

        for actor in scenario.actors:
            # print('{} init ({} {} {})'.format(actor.type, actor.start_pose.x, actor.start_pose.y, -actor.start_pose.z))
            # if abs(actor.start_pose.x - 1) < 1 and abs(actor.start_pose.y - 1) < 1:
            #     actor.start_pose.x += random.uniform(3, 5)
            #     actor.start_pose.y += random.uniform(3, 5)
            self.add_npc(self.map_config["actor_type"][actor.type], actor.start_pose)
            # if not success:
            #     actor.type = -1

        
    # if the actors are not static, move them to the destination
    def run_scenario(self):
        scenario = self.current_scenario
        # print('11111111111111111111',self.dynamic_objects)
        if len(self.scenario_objects) != 0:
            for i, actor in enumerate(scenario.actors):
                if actor.type == -1:
                    continue
                # print(actor.end_pose)
                # print('actor', i)
                try:
                    print('move actor {}'.format(self.scenario_objects[i]))
                    self.move_npc_to(self.scenario_objects[i], actor.end_pose, actor.speed)
                except:
                    pass


if __name__ == "__main__":
    # env = AirSimEnv('cv', '10.6.37.180')
    try:
        env = AirSimEnv('cv', '10.6.37.180')
    except:
        env = AirSimEnv('cv', '127.0.0.1')
    env.add_npc('npc_person_1', Pose(0, 10, 0))
    # env.reset_env()
    # time.sleep(3)
    # status, npc_name = env.add_npc('person_2', 2, 2, 1)
    # time.sleep(5)
    # env.get_pose('npc_vehicle_2')
    # env.client.simSetNPCVehicleThrottle('npc_vehicle_2', throttle=-0.5)
    # env.client.simSetNPCVehicleSteering('npc_vehicle_2', steering=0.5)
    # time.sleep(1)
    # env.client.simSetNPCVehicleThrottle('npc_vehicle_2', throttle=0)

    # env.npc_move_to('npc_vehicle_2', -1.89, 30, speed=300)
    # time.sleep(1)
    # env.set_marker(4, 2)
    # status, npc_name = env.add_npc('person_2', 0, 0, 1)
    # time.sleep(5)
    # env.get_npc_pose(npc_name)

    # if status:
    #     env.npc_move_to(npc_name, 10, 10, speed=300)
    # env.get_npc_pose('npc_deer_0')
    # env.set_npc('npc_person_1', 0, 0, -1)
    # env.set_time_of_day([0.2, 0.8])