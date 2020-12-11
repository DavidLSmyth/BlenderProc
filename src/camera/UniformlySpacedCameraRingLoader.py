import bpy
import math
from src.camera.CameraLoader import CameraLoader
from src.utility.ItemCollection import ItemCollection
#from src.utility.BlenderUtility import get_camera_positions_on_circle

def get_camera_positions_on_circle(circle_radius, num_angles, z_offset) -> float:
    '''Returns a generator containing (rotation, position) pairs, which can be used to update a camera position to track the origin around a circle.'''
    rotAngle  = 360 / num_angles
    for camera_pos_index in range(num_angles):
        angle = camera_pos_index * rotAngle
        #camera_object.rotation_euler.z = radians( angle )
        z_rotation_radians = math.radians(angle)
        camera_location = [circle_radius  * math.cos(z_rotation_radians), circle_radius * math.sin(z_rotation_radians), z_offset]#        camera_object.location = (radius * math.cos( radians(angle)), radius * math.sin(radians(angle)), 0)
        #yield z_rotation_radians, camera_location
        yield camera_location


class UniformlySpacedCameraRingLoader(CameraLoader):

    def __init__(self, config):
        super().__init__(config)

    def run(self):

        #circle_radius, num_angles, z_offset
        super().run()
        locations = get_camera_positions_on_circle(self.config.get_int("circle_radius", 2),
                                                self.config.get_int("number_of_angles", 24),
                                                self.config.get_int("z_offset", 0)
                                                )

        #set extrinsic params based on yaml params
        extrinsics_config = []

        for location in locations:
            extrinsics_config.append({"location": location})


        self.cam_pose_collection.add_items_from_dicts(extrinsics_config)



