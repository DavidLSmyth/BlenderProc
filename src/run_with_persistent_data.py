'''
Run with an initial config, looping over e.g. meshes to load and render
'''
# blender --background --python run.py  -- <config0> [<args>] -- <config1> [<args>]
# <config0> is run once to set the scene (e.g. lighting etc.
#<config2> is repeated

import sys
import os
from sys import platform
import bpy

# Make sure the current script directory is in PATH, so we can load other python modules
dir = "."  # From CLI
if not dir in sys.path:
    sys.path.append(dir)

# Add path to custom packages inside the blender main directory
if platform == "linux" or platform == "linux2":
    packages_path = os.path.abspath(os.path.join(os.path.dirname(sys.executable), "..", "..", "..", "custom-python-packages"))
elif platform == "darwin":
    packages_path = os.path.abspath(os.path.join(os.path.dirname(sys.executable), "..", "..", "..", "..", "Resources", "custom-python-packages"))
elif platform == "win32":
    packages_path = os.path.abspath(os.path.join(os.path.dirname(sys.executable), "..", "..", "..", "custom-python-packages"))
else:
    raise Exception("This system is not supported yet: {}".format(platform))
sys.path.append(packages_path)

# Read args
argv = sys.argv
batch_index_file = None

if "--batch-process" in argv:
    batch_index_file = argv[argv.index("--batch-process") + 1]

argv = argv[argv.index("--") + 1:]
working_dir = os.path.dirname(os.path.abspath(__file__))

from src.main.Pipeline import Pipeline
from src.main.RepeatPipeline import RepeatPipeline
from src.utility.Utility import Utility

init_config_path = argv[0]
repeat_config_path = argv[1]
temp_dir = argv[2]

if batch_index_file == None:
    #pipeline = Pipeline(config_path, argv[2:], working_dir, temp_dir)
    #pipeline.run()
    print("Please provide a batch index file to run modules repeatedly with persistent data")
else:
    with open(Utility.resolve_path(batch_index_file), "r") as f:
        lines = f.readlines()
        #lines[0] gives the initialization arguments
        print(lines[0])
        #Run the initialization pipeline
        init_pipeline = Pipeline(init_config_path, [lines[0].replace("\n","")], working_dir, temp_dir)
        init_pipeline.run()
        #everything imported up to this point should be left in the scene. Using name as a key but should probably use some kind of hash/unique idenfifier for full implementation
        loaded_objects = [obj.name for obj in bpy.data.objects]
        print("Keeping the following in the scene: ")
        print(', '.join([obj_name for obj_name in loaded_objects]))
        #run the repeat pipeline, keeping loaded_objects in the scene. should_perform_clean_up ensures that everything in between each batch is removed, with the exception of loaded_objects
        for line in lines[1:]:
            args = line.split(" ")
            args = [arg.replace("\n","") for arg in args]
            pipeline = RepeatPipeline(loaded_objects, repeat_config_path, args, working_dir, temp_dir, should_perform_clean_up = True)
            pipeline.run()
