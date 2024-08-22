from ..client import MultirotorClient
from ..types import *
from .utils import sample_position_on_circle
from ..utils import to_quaternion
from .components.config import ACTOR_TYPE, BP_TYPE
from .components.weather import Weather
from .components.actor import Actor
from .components.time import Time
from .components.marker import Marker
import random
from .scenario import Scenario

def generate_random_scenario(client, x_range, y_range, radius, z_dist=None):
    # set a random marker position
    x = random.uniform(x_range[0], x_range[1])
    y = random.uniform(y_range[0], y_range[1])
    z = client.simGetGroundHeight(x, y)
    marker_position = Vector3r(x, y, z)
    tp_marker = Marker(0, None, Pose(marker_position), 'tp')

    # set a target gps position within the raidus range of the marker position
    # gps_pose = Pose(Vector3r(0, 10, 0))
    in_radius = random.uniform(0, radius)
    x, y = sample_position_on_circle(marker_position, in_radius)
    if not z_dist:
        z_dist = random.uniform(5, 30)
    gps_pose = Pose(Vector3r(x, y, z - z_dist), to_quaternion(0, 0, math.radians(random.uniform(-90, 90))))

    fp_markers= []
    drone_start_pose = Pose(Vector3r(0, 0, 0))
    weather = Weather(*([random.uniform(0, 0.2)] * 9))
    time = Time(random.random(), random.random())
    actors = []

    scenario = Scenario(tp_marker, fp_markers, drone_start_pose, gps_pose, radius, actors, weather, time)
    return scenario