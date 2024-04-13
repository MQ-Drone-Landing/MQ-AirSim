import airsim
from scenario_generation.components.marker import Marker
from scenario_generation.components.weather import Weather
from scenario_generation.components.time import Time
from scenario_generation.scenario import Scenario
from scenario_generation.components.actor import Actor

def person_near_marker_scenario():
    tp_marker = Marker(0, 0, airsim.Pose(airsim.Vector3r(10, -12, -0.55)))
    fp_markers = []
    drone_start_pose = airsim.Pose(airsim.Vector3r(0, 0, 0))
    gps_pose = airsim.Pose(airsim.Vector3r(10, -20, 0))
    marker_sample_radius = 10
    # actors = [Actor(0, Pose(-9, 0, 0), Pose(-9, 0, 0), 0), Actor(3, Pose(-10, 0, 0.3), Pose(-10, 0, 0.2), 0)]
    actor_1 = Actor('person', airsim.Pose(airsim.Vector3r(-1, 0, 0)), airsim.Pose(airsim.Vector3r(-15, 0, 0)), speed=0.5, mode=1, name='actor_1')
    actors = [actor_1]

    static_objs = []
    weather = Weather(*([0] * 9))
    time = Time(0.5, 0.5)
    # actors = []

    
    scenario = Scenario(tp_marker, fp_markers, drone_start_pose, gps_pose, marker_sample_radius, actors, weather, time)

    return scenario