# This file is for file IO for V3 maps.
import os
import random
import yaml

from map import *
from stripper import strip_base_files
from terrain import *


USED_MASKS = {
    BaseTerrain.plains: "grasslands_02",
    BaseTerrain.farmlands: "grasslands_01",  # I think farmlands isn't used at all in vanilla, which suggests it's done dynamically?
    BaseTerrain.hills: "cliff_granite_01",
    BaseTerrain.mountains: "cliff_limestone_02",
    BaseTerrain.forest: "woodlands_01",
    BaseTerrain.desert: "desert_04",
    BaseTerrain.marsh: "marchlands_01",
    BaseTerrain.jungle: "woodlands_03",
}

class V3Map:
    def __init__(self, file_dir, max_x, max_y, n_x, n_y):
        """Creates a map of size max_x * max_y, which is n_x hexes wide and n_y hexes tall."""
        self.file_dir = file_dir
        os.makedirs(os.path.join(file_dir, "map_data"), exist_ok=True)
        self.max_x = max_x
        self.max_y = max_y
        self.n_x = n_x
        self.n_y = n_y

    def create_provinces(self, rgb_from_cube):
        """Creates provinces.png and definition.csv"""
        img = create_hex_map(rgb_from_ijk={k.tuple(): v for k,v in rgb_from_cube.items()}, max_x=self.max_x, max_y=self.max_y, mode='RGB', default="black", n_x=self.n_x, n_y=self.n_y)
        img.save(os.path.join(self.file_dir, "map_data", "provinces.png"))

    def create_heightmap(self, height_from_cube):
        """Uses height_from_cube to generate a simple heightmap."""
        rgb_from_ijk = {k.tuple(): v for k,v in height_from_cube.items()}
        img = create_hex_map(rgb_from_ijk=rgb_from_ijk, max_x=self.max_x, max_y=self.max_y, mode='L', default="white", n_x=self.n_x, n_y=self.n_y)
        img.save(os.path.join(self.file_dir, "map_data", "heightmap.png"))
        with open(os.path.join(self.file_dir, "map_data", 'heightmap.heightmap'), 'w') as outf:
            outf.write("heightmap_file=\"map_data/packed_heightmap.png\"\n")
            outf.write("indirection_file=\"map_data/indirection_heightmap.png\"\n")
            outf.write(f"original_heightmap_size={{ {self.max_x} {self.max_y} }}\n")
            outf.write("tile_size=65\n")
            outf.write("should_wrap_x=no\n")
            outf.write("level_offsets={ { 0 0 } { 0 6695 } { 0 7569 } { 0 7662 } { 0 7680 } }\n")
            outf.write("max_compress_level=4\n")
            outf.write("empty_tile_offset={ 201 76 }\n")

    def create_terrain_masks(self, file_dir, base_dir, terr_from_cube):
        """Creates all the terrain masks; just fills each cube.
        terr_from_cube is a map from cube to BaseTerrain."""
        os.makedirs(os.path.join(file_dir, "gfx", "map", "terrain"), exist_ok=True)
        for mask in os.listdir(os.path.join(base_dir, "gfx", "map", "terrain")):
            if not mask.startswith("mask"):
                continue
            mask_name = mask[5:-4]  # begins with mask_ and ends with .png
            if mask_name not in USED_MASKS.values():
                create_hex_map(rgb_from_ijk={}, max_x=self.max_x, max_y=self.max_y, mode='L', default="black").save(os.path.join(file_dir, "gfx", "map", "terrain", mask))
            else:
                terrain = [k for k,v in USED_MASKS.items() if v == mask_name][0]
                rgb_from_cube = {k.tuple(): 128 for k,v in terr_from_cube.items() if v == terrain}
                create_hex_map(rgb_from_ijk=rgb_from_cube, max_x=self.max_x, max_y=self.max_y, mode='L', default="black").save(os.path.join(file_dir, "gfx", "map", "terrain", mask))
    
    def create_rivers(self, river_background, river_edges, river_vertices, base_loc):
        """Create rivers.png"""
        img = create_hex_map(rgb_from_ijk=river_background, rgb_from_edge=river_edges, rgb_from_vertex=river_vertices, max_x=self.max_x, max_y=self.max_y, mode='P', palette=get_palette(base_loc), default="white", n_x=self.n_x, n_y=self.n_y)
        img.save(os.path.join(self.file_dir, "map_data", "rivers.png"))


def create_blanks(file_dir):
    """There are a lot of V3 files that we want to just blank out."""
    for file_path in [
        ["gfx", "map", "city_data", "american_mining_oilrig.txt"],  # These should perhaps be fine if we use the vanilla regions / cultures
        ["gfx", "map", "city_data", "wild_west_farm.txt"],  # These should perhaps be fine if we use the vanilla regions / cultures
    ]:
        with open(os.path.join(file_dir, *file_path), 'w') as outf:
            outf.write("\n")


def create_dot_mod(file_dir, mod_name, mod_disp_name):
    """Creates the basic mod structure and metadata file."""
    file_dir = os.path.join(file_dir, mod_name)
    os.makedirs(os.path.join(file_dir,".metadata"), exist_ok=True)
    with open(os.path.join(file_dir, "metadata", "metadata.json"),'w') as outf:
        outf.write("{\n\t\"name\" : "+mod_disp_name+"\",\n\t\"id\" : \"\"\n\t\"version\" : \"\"\n\t\"supported_game_version\" : \"\",\n\t\"short_description\" : \"\",\n\t\"tags\" : [],\n\t\"relationships\" : [],\n\t\"game_custom_data\" : {\t\t\"multiplayer_synchronized\" : true\n\t},\n\t\"replace_paths\": [\n")
        outf.write("\n".join(x for x in [                
                    "common/country_definitions",
                    "common/history/buildings",
                    "common/history/characters",
                    "common/history/countries",
                    "common/history/diplomatic_plays",
                    "common/history/pops",
                    "content_source/map_objects/masks",
                    "map_data/state_regions",
                ]))
        outf.write("\n\t]\n}\n")
    return file_dir


def create_mod(file_dir, config, pid_from_cube, terr_from_cube, rgb_from_pid, height_from_cube, river_edges, river_vertices):
    """Creates the V3 mod files in file_dir, given the basic data."""
    # Make the basic filestructure that other things go in.
    file_dir = create_dot_mod(file_dir=file_dir, mod_name=config.get("MOD_NAME", "testmod"), mod_disp_name=config.get("MOD_DISPLAY_NAME", "testing_worldgen"))
    rgb_from_cube = {k:rgb_from_pid[pid] for k, pid in pid_from_cube.items()}
    # Maps
    v3map = V3Map(file_dir=file_dir, max_x=config["max_x"], max_y=config["max_y"], n_x=config["n_x"], n_y=config["n_y"])
    v3map.create_provinces(rgb_from_cube=rgb_from_cube)
    v3map.create_heightmap(height_from_cube=height_from_cube)
    river_background = {k.tuple():255 if v > WATER_HEIGHT else 254 for k,v in height_from_cube.items()}
    v3map.create_rivers(river_background, river_edges, river_vertices)

    strip_base_files(file_dir, config["BASE_V3_DIR"], [
        "common/decisions",
        "common/travel",
        "events"
    ])