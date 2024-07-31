import os

def setup_dir(path_to_dir):
    if not os.path.exists(path_to_dir):
        os.makedirs(path_to_dir)