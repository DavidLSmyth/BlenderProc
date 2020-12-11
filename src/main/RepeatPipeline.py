
import shutil
import os
import bpy

from src.utility.ConfigParser import ConfigParser
from src.utility.Utility import Utility, Config
from src.main.GlobalStorage import GlobalStorage

class RepeatPipeline:

    def __init__(self, persistent_obj_names, repeat_config_path, args, working_dir, temp_dir, should_perform_clean_up=False, avoid_rendering=False):
        """
        Inits the pipeline, by calling the constructors of all modules mentioned in the config.

        :param persistent_obj_names A list of names of objects to persist in the scene
        :param config_path path to the config
        :param args arguments which were provided to the run.py and are specified in the config file
        :param working_dir the current working dir usually the place where the run.py sits
        :param working_dir the directory where to put temporary files during the execution
        :param should_perform_clean_up if the generated temp file should be deleted at the end
        :param avoid_rendering if this is true all renderes are not executed (except the RgbRenderer,
                               where only the rendering call to blender is avoided) with this it is possible to debug
                               properly
        """
        Utility.working_dir = working_dir
        self.persistent_obj_names = persistent_obj_names

        # Clean up example scene or scene created by last run when debugging pipeline inside blender
        if should_perform_clean_up:
            self._cleanup(self.persistent_obj_names)

        #init_config_parser = ConfigParser(silent=True)
        #init_config = init_config_parser.parse(Utility.resolve_path(init_config_path), args)

        repeat_config_parser = ConfigParser(silent=True)
        repeat_config = repeat_config_parser.parse(Utility.resolve_path(repeat_config_path), args)

        if avoid_rendering:
            GlobalStorage.add_to_config_before_init("avoid_rendering", True)

        Utility.temp_dir = Utility.resolve_path(temp_dir)
        os.makedirs(Utility.temp_dir, exist_ok=True)

        self.repeat_modules = Utility.initialize_modules(repeat_config["modules"])

    def _cleanup(self, persistent_objs):
        """ Cleanup the scene by removing objects, orphan data and custom properties """
        self._remove_all_objects(persistent_objs)
        #self._remove_orphan_data()
        #self._remove_custom_properties()

    def _remove_all_objects(self, persistent_obj_names ):
        """ Removes all objects of the current scene """
        # Select all
        for obj in bpy.context.scene.objects:
            if obj.name not in persistent_obj_names:
                print("Deleting " + obj.name)
                obj.select_set(True)
            else:
                print("Not deleting " + obj.name)
        # Delete selection
        bpy.ops.object.delete()

    def _remove_orphan_data(self):
        """ Remove all data blocks which are not used anymore. """
        data_structures = [
            bpy.data.meshes,
            bpy.data.materials,
            bpy.data.textures,
            bpy.data.images,
            bpy.data.brushes,
            bpy.data.cameras,
            bpy.data.actions,
            bpy.data.lights
        ]

        for data_structure in data_structures:
            for block in data_structure:
                # If no one uses this block => remove it
                if block.users == 0:
                    #print("removing")
                    data_structure.remove(block)

    def _remove_custom_properties(self):
        """ Remove all custom properties registered at global entities like the scene. """
        for key in bpy.context.scene.keys():
            del bpy.context.scene[key]

    def run(self):
        """ Runs each module and measuring their execution time. """
        with Utility.BlockStopWatch("Running blender pipeline"):
            for module in self.repeat_modules:
                with Utility.BlockStopWatch("Running module " + module.__class__.__name__):
                    module.run()
