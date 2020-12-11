import bpy

from src.camera.CameraInterface import CameraInterface
from src.utility.Config import Config
from src.utility.ItemCollection import ItemCollection
import math
import sys
import os
def build_environment_texture_background(world: bpy.types.World, hdri_path: str, rotation: float = 0.0) -> None:
    world.use_nodes = True
    node_tree = world.node_tree

    environment_texture_node = node_tree.nodes.new(type="ShaderNodeTexEnvironment")
    environment_texture_node.image = bpy.data.images.load(hdri_path)

    mapping_node = node_tree.nodes.new(type="ShaderNodeMapping")
    if bpy.app.version >= (2, 81, 0):
        mapping_node.inputs["Rotation"].default_value = (0.0, 0.0, rotation)
    else:
        mapping_node.rotation[2] = rotation

    tex_coord_node = node_tree.nodes.new(type="ShaderNodeTexCoord")

    node_tree.links.new(tex_coord_node.outputs["Generated"], mapping_node.inputs["Vector"])
    node_tree.links.new(mapping_node.outputs["Vector"], environment_texture_node.inputs["Vector"])
    node_tree.links.new(environment_texture_node.outputs["Color"], node_tree.nodes["Background"].inputs["Color"])

    arrange_nodes(node_tree)

def arrange_nodes(node_tree: bpy.types.NodeTree, verbose: bool = False) -> None:
    max_num_iters = 2000
    epsilon = 1e-05
    target_space = 50.0

    second_stage = False

    fix_horizontal_location = True
    fix_vertical_location = True
    fix_overlaps = True

    if verbose:
        print("-----------------")
        print("Target nodes:")
        for node in node_tree.nodes:
            print("- " + node.name)

    # In the first stage, expand nodes overly
    target_space *= 2.0

    # Gauss-Seidel-style iterations
    previous_squared_deltas_sum = sys.float_info.max
    for i in range(max_num_iters):
        squared_deltas_sum = 0.0

        if fix_horizontal_location:
            for link in node_tree.links:
                k = 0.9 if not second_stage else 0.5
                threshold_factor = 2.0

                x_from = link.from_node.location[0]
                x_to = link.to_node.location[0]
                w_from = link.from_node.width
                signed_space = x_to - x_from - w_from
                C = signed_space - target_space
                grad_C_x_from = -1.0
                grad_C_x_to = 1.0

                # Skip if the distance is sufficiently large
                if C >= target_space * threshold_factor:
                    continue

                lagrange = C / (grad_C_x_from * grad_C_x_from + grad_C_x_to * grad_C_x_to)
                delta_x_from = -lagrange * grad_C_x_from
                delta_x_to = -lagrange * grad_C_x_to

                link.from_node.location[0] += k * delta_x_from
                link.to_node.location[0] += k * delta_x_to

                squared_deltas_sum += k * k * (delta_x_from * delta_x_from + delta_x_to * delta_x_to)

        if fix_vertical_location:
            k = 0.5 if not second_stage else 0.05
            socket_offset = 20.0

            def get_from_socket_index(node: bpy.types.Node, node_socket: bpy.types.NodeSocket) -> int:
                for i in range(len(node.outputs)):
                    if node.outputs[i] == node_socket:
                        return i
                assert False

            def get_to_socket_index(node: bpy.types.Node, node_socket: bpy.types.NodeSocket) -> int:
                for i in range(len(node.inputs)):
                    if node.inputs[i] == node_socket:
                        return i
                assert False

            for link in node_tree.links:
                from_socket_index = get_from_socket_index(link.from_node, link.from_socket)
                to_socket_index = get_to_socket_index(link.to_node, link.to_socket)
                y_from = link.from_node.location[1] - socket_offset * from_socket_index
                y_to = link.to_node.location[1] - socket_offset * to_socket_index
                C = y_from - y_to
                grad_C_y_from = 1.0
                grad_C_y_to = -1.0
                lagrange = C / (grad_C_y_from * grad_C_y_from + grad_C_y_to * grad_C_y_to)
                delta_y_from = -lagrange * grad_C_y_from
                delta_y_to = -lagrange * grad_C_y_to

                link.from_node.location[1] += k * delta_y_from
                link.to_node.location[1] += k * delta_y_to

                squared_deltas_sum += k * k * (delta_y_from * delta_y_from + delta_y_to * delta_y_to)

        if fix_overlaps and second_stage:
            k = 0.9
            margin = 0.5 * target_space

            # Examine all node pairs
            for node_1 in node_tree.nodes:
                for node_2 in node_tree.nodes:
                    if node_1 == node_2:
                        continue

                    x_1 = node_1.location[0]
                    x_2 = node_2.location[0]
                    w_1 = node_1.width
                    w_2 = node_2.width
                    cx_1 = x_1 + 0.5 * w_1
                    cx_2 = x_2 + 0.5 * w_2
                    rx_1 = 0.5 * w_1 + margin
                    rx_2 = 0.5 * w_2 + margin

                    # Note: "dimensions" and "height" may not be correct depending on the situation
                    def get_height(node: bpy.types.Node) -> float:
                        if node.dimensions.y > epsilon:
                            return node.dimensions.y
                        elif math.fabs(node.height - 100.0) > epsilon:
                            return node.height
                        else:
                            return 200.0

                    y_1 = node_1.location[1]
                    y_2 = node_2.location[1]
                    h_1 = get_height(node_1)
                    h_2 = get_height(node_2)
                    cy_1 = y_1 - 0.5 * h_1
                    cy_2 = y_2 - 0.5 * h_2
                    ry_1 = 0.5 * h_1 + margin
                    ry_2 = 0.5 * h_2 + margin

                    C_x = math.fabs(cx_1 - cx_2) - (rx_1 + rx_2)
                    C_y = math.fabs(cy_1 - cy_2) - (ry_1 + ry_2)

                    # If no collision, just skip
                    if C_x >= 0.0 or C_y >= 0.0:
                        continue

                    # Solve collision for the "easier" direction
                    if C_x > C_y:
                        grad_C_x_1 = 1.0 if cx_1 - cx_2 >= 0.0 else -1.0
                        grad_C_x_2 = -1.0 if cx_1 - cx_2 >= 0.0 else 1.0
                        lagrange = C_x / (grad_C_x_1 * grad_C_x_1 + grad_C_x_2 * grad_C_x_2)
                        delta_x_1 = -lagrange * grad_C_x_1
                        delta_x_2 = -lagrange * grad_C_x_2

                        node_1.location[0] += k * delta_x_1
                        node_2.location[0] += k * delta_x_2

                        squared_deltas_sum += k * k * (delta_x_1 * delta_x_1 + delta_x_2 * delta_x_2)
                    else:
                        grad_C_y_1 = 1.0 if cy_1 - cy_2 >= 0.0 else -1.0
                        grad_C_y_2 = -1.0 if cy_1 - cy_2 >= 0.0 else 1.0
                        lagrange = C_y / (grad_C_y_1 * grad_C_y_1 + grad_C_y_2 * grad_C_y_2)
                        delta_y_1 = -lagrange * grad_C_y_1
                        delta_y_2 = -lagrange * grad_C_y_2

                        node_1.location[1] += k * delta_y_1
                        node_2.location[1] += k * delta_y_2

                        squared_deltas_sum += k * k * (delta_y_1 * delta_y_1 + delta_y_2 * delta_y_2)

        if verbose:
            print("Iteration #" + str(i) + ": " + str(previous_squared_deltas_sum - squared_deltas_sum))

        # Check the termination conditiion
        if math.fabs(previous_squared_deltas_sum - squared_deltas_sum) < epsilon:
            if second_stage:
                break
            else:
                target_space = 0.5 * target_space
                second_stage = True

        previous_squared_deltas_sum = squared_deltas_sum


def create_vignette_node(node_tree: bpy.types.NodeTree) -> bpy.types.Node:
    vignette_node_group = add_vignette_node_group()

    node = node_tree.nodes.new(type='CompositorNodeGroup')
    node.name = "Vignette"
    node.node_tree = vignette_node_group

    return node

def add_vignette_node_group() -> bpy.types.NodeGroup:
    group = bpy.data.node_groups.new(type="CompositorNodeTree", name="Vignette")

    input_node = group.nodes.new("NodeGroupInput")
    group.inputs.new("NodeSocketColor", "Image")
    group.inputs.new("NodeSocketFloat", "Amount")
    group.inputs["Amount"].default_value = 0.2
    group.inputs["Amount"].min_value = 0.0
    group.inputs["Amount"].max_value = 1.0

    lens_distortion_node = group.nodes.new(type="CompositorNodeLensdist")
    lens_distortion_node.inputs["Distort"].default_value = 1.000

    separate_rgba_node = group.nodes.new(type="CompositorNodeSepRGBA")

    blur_node = group.nodes.new(type="CompositorNodeBlur")
    blur_node.filter_type = 'GAUSS'
    blur_node.size_x = 300
    blur_node.size_y = 300
    blur_node.use_extended_bounds = True

    mix_node = group.nodes.new(type="CompositorNodeMixRGB")
    mix_node.blend_type = 'MULTIPLY'

    output_node = group.nodes.new("NodeGroupOutput")
    group.outputs.new("NodeSocketColor", "Image")

    group.links.new(input_node.outputs["Amount"], mix_node.inputs["Fac"])
    group.links.new(input_node.outputs["Image"], mix_node.inputs[1])
    group.links.new(input_node.outputs["Image"], lens_distortion_node.inputs["Image"])
    group.links.new(lens_distortion_node.outputs["Image"], separate_rgba_node.inputs["Image"])
    group.links.new(separate_rgba_node.outputs["A"], blur_node.inputs["Image"])
    group.links.new(blur_node.outputs["Image"], mix_node.inputs[2])
    group.links.new(mix_node.outputs["Image"], output_node.inputs["Image"])

    arrange_nodes(group)

    return group

def clean_nodes(nodes: bpy.types.Nodes) -> None:
    for node in nodes:
        nodes.remove(node)

def build_scene_composition(scene: bpy.types.Scene) -> None:
    scene.use_nodes = True
    clean_nodes(scene.node_tree.nodes)

    render_layer_node = scene.node_tree.nodes.new(type="CompositorNodeRLayers")

    vignette_node = create_vignette_node(scene.node_tree)
    vignette_node.inputs["Amount"].default_value = 0.70

    lens_distortion_node = scene.node_tree.nodes.new(type="CompositorNodeLensdist")
    lens_distortion_node.inputs["Distort"].default_value = -0.050
    lens_distortion_node.inputs["Dispersion"].default_value = 0.080

    color_correction_node = scene.node_tree.nodes.new(type="CompositorNodeColorCorrection")
    color_correction_node.master_saturation = 1.10
    color_correction_node.master_gain = 1.40

    glare_node = scene.node_tree.nodes.new(type="CompositorNodeGlare")
    glare_node.glare_type = 'GHOSTS'
    glare_node.iterations = 2
    glare_node.quality = 'HIGH'

    composite_node = scene.node_tree.nodes.new(type="CompositorNodeComposite")

    scene.node_tree.links.new(render_layer_node.outputs['Image'], vignette_node.inputs['Image'])
    scene.node_tree.links.new(vignette_node.outputs['Image'], lens_distortion_node.inputs['Image'])
    scene.node_tree.links.new(lens_distortion_node.outputs['Image'], color_correction_node.inputs['Image'])
    scene.node_tree.links.new(color_correction_node.outputs['Image'], glare_node.inputs['Image'])
    scene.node_tree.links.new(glare_node.outputs['Image'], composite_node.inputs['Image'])

    arrange_nodes(scene.node_tree)


class CameraLoader(CameraInterface):
    """ Loads camera poses from the configuration and sets them as separate keypoints.
        Camera poses can be specified either directly inside the config or in an extra file.

        Example 1: Loads camera poses from file <args:0>, followed by the pose file format and setting the fov in radians.

        {
          "module": "camera.CameraLoader",
          "config": {
            "path": "<args:0>",
            "file_format": "location rotation/value",
            "intrinsics": {
              "fov": 1
            }
          }
        }

        Example 2: More examples for parameters in "intrinsics". Here cam_K is a camera matrix. Check
                   CameraInterface for more info on "intrinsics".

        "intrinsics": {
          "fov_is_half": true,
          "interocular_distance": 0.05,
          "stereo_convergence_mode": "PARALLEL",
          "convergence_distance": 0.00001,
          "cam_K": [650.018, 0, 637.962, 0, 650.018, 355.984, 0, 0 ,1],
          "resolution_x": 1280,
          "resolution_y": 720
        }

    **Configuration**:

    .. csv-table::
       :header: "Parameter", "Description"

       "cam_poses", "Optionally, a list of dicts, where each dict specifies one cam pose. See CameraInterface for which "
                    "properties can be set. Type: list of dicts. Default: []."
       "path", "Optionally, a path to a file which specifies one camera position per line. The lines has to be "
               "formatted as specified in 'file_format'. Type: string. Default: ""."
       "file_format", "A string which specifies how each line of the given file is formatted. The string should contain "
                      "the keywords of the corresponding properties separated by a space. See next table for allowed "
                      "properties. Type: string. Default: ""."
       "default_cam_param", "A dict which can be used to specify properties across all cam poses. Type: dict. Default: {}."
       "intrinsics", "A dictionary containing camera intrinsic parameters. Type: dict. Default: {}."
    """


    def __init__(self, config):
        CameraInterface.__init__(self, config)
        # A dict specifying the length of parameters that require more than one argument. If not specified, 1 is assumed.
        self.number_of_arguments_per_parameter = {
            "location": 3,
            "rotation/value": 3,
            "cam2world_matrix": 16
        }
        self.cam_pose_collection = ItemCollection(self._add_cam_pose, self.config.get_raw_dict("default_cam_param", {}))

    def run(self):
        # Set intrinsics
        self._set_cam_intrinsics(bpy.context.scene.camera.data, Config(self.config.get_raw_dict("intrinsics", {})))

        self.cam_pose_collection.add_items_from_dicts(self.config.get_list("cam_poses", []))
        self.cam_pose_collection.add_items_from_file(self.config.get_string("path", ""),
                                                     self.config.get_string("file_format", ""),
                                                     self.number_of_arguments_per_parameter)


        if os.path.isfile(os.path.join(os.path.curdir,self.config.get_string("background_image", ""))):
            self.add_background_hdri()
        else:
            print("{} is not a valid file location, can't load background image".format(self.config.get_string("background_image", "")))

    def add_background_hdri(self):
        try:
            build_environment_texture_background(bpy.data.scenes["Scene"].world, self.config.get_string("background_image", ""))
            build_scene_composition(bpy.data.scenes["Scene"])
            print("added background image")
        except Exception as e:
            print("Couldn't create background image", e)

    def _add_cam_pose(self, config):
        """ Adds new cam pose + intrinsics according to the given configuration.

        :param config: A configuration object which contains all parameters relevant for the new cam pose.
        """

        # Collect camera object
        cam_ob = bpy.context.scene.camera

        # Set extrinsics from config
        self._set_cam_extrinsics(cam_ob, config)
