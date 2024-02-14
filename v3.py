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

V3Terrain_Name_from_BaseTerrain = {
    BaseTerrain.plains: "plains",
    BaseTerrain.farmlands: "plains",
    BaseTerrain.hills: "hills",
    BaseTerrain.mountains: "mountain",
    BaseTerrain.forest: "forest",
    BaseTerrain.desert: "desert",
    BaseTerrain.marsh: "wetland",
    BaseTerrain.jungle: "jungle",
    BaseTerrain.ocean: "ocean",
}

VALID_LOCS = ["city", "port", "farm", "mine", "wood"]  # These are the locations that are in a specific province in each state.

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
                create_hex_map(rgb_from_ijk={}, max_x=self.max_x, max_y=self.max_y, n_x=self.n_x, n_y=self.n_y, mode='L', default="black").save(os.path.join(file_dir, "gfx", "map", "terrain", mask))
            else:
                terrain = [k for k,v in USED_MASKS.items() if v == mask_name][0]
                rgb_from_ijk = {k.tuple(): 128 for k,v in terr_from_cube.items() if v == terrain}
                img = create_hex_map(rgb_from_ijk=rgb_from_ijk, max_x=self.max_x, max_y=self.max_y, n_x=self.n_x, n_y=self.n_y, mode='L', default="black")
                img.save(os.path.join(file_dir, "gfx", "map", "terrain", mask))
    
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
        os.makedirs(os.path.join(file_dir,*file_path[:-1]), exist_ok=True)
        with open(os.path.join(file_dir, *file_path), 'w') as outf:
            outf.write("\n")


def create_terrain_file(file_dir, terr_from_pid, rgb_from_pid):
    """Writes out common/province_terrain."""
    # Masks were historically wrapped into create_heightmap, and should maybe be again.
    os.makedirs(os.path.join(file_dir, "map_data"), exist_ok=True)
    with open(os.path.join(file_dir, "map_data", "province_terrain.txt"), 'w') as outf:
        for pid, terr in terr_from_pid.items():
            outf.write(f"{hex_rgb(*rgb_from_pid[pid])}=\"{V3Terrain_Name_from_BaseTerrain[terr]}\"\n")

def create_dot_mod(file_dir, mod_name, mod_disp_name):
    """Creates the basic mod structure and metadata file."""
    file_dir = os.path.join(file_dir, mod_name)
    os.makedirs(os.path.join(file_dir,".metadata"), exist_ok=True)
    with open(os.path.join(file_dir, ".metadata", "metadata.json"),'w') as outf:
        outf.write("{\n\t\"name\" : \""+mod_disp_name+"\",\n\t\"id\" : \"\",\n\t\"version\" : \"0.0\",\n\t\"supported_game_version\" : \"1.5.13\",\n\t\"short_description\" : \"\",\n\t\"tags\" : [\n\t\t\"Total Conversion\"\n\t],\n\t\"relationships\" : [],\n\t\"game_custom_data\" : {\n\t\t\"multiplayer_synchronized\" : true,\n\t\t\"replace_paths\": [\n")
        outf.write(",\n".join("\t\t\t\"" + x + "\"" for x in [                
                    "common/country_definitions",
                    "common/history/buildings",
                    "common/history/characters",
                    "common/history/countries",
                    "common/history/diplomatic_plays",
                    "common/history/pops",
                    "content_source/map_objects/masks",
                    "map_data/state_regions",
                ]))
        outf.write("\n\t\t]\n\t}\n}\n")
    return file_dir


HEX_LIST = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "A", "B", "C", "D", "E", "F"]
def hex_rgb(r, g, b):
    """Create a v3-style hex string from a r,g,b tuple. (Use *rgb to split the tuple.)"""
    return "x" + HEX_LIST[r // 16] + HEX_LIST[r % 16] + HEX_LIST[g // 16] + HEX_LIST[g % 16] + HEX_LIST[b // 16] + HEX_LIST[b % 16]


def create_states(file_dir, rid_from_pid, rgb_from_pid, name_from_rid, traits_from_rid, locs_from_rid, arable_from_rid, capped_from_rid, coast_from_rid):
    """Creates state_region files, as well as relevant history files."""
    os.makedirs(os.path.join(file_dir,"map_data","state_regions"), exist_ok=True)
    with open(os.path.join(file_dir,"map_data","state_regions", "00_state_regions.txt"), 'w', encoding='utf-8') as outf:
        with open(os.path.join(file_dir,"map_data","state_regions", "99_seas.txt"), 'w', encoding='utf-8') as soutf:
            for rid, rname in name_from_rid.items():
                if rname[0] == "i":  # We don't care about the impassable regions. Might need to fix this later.
                    continue
                buffer = f"{rname} = {{\n\tid = {rid}\n\tprovinces = {{ "
                buffer += " ".join(["\""+hex_rgb(*rgb_from_pid[pid])+"\"" for pid, rrid in rid_from_pid.items() if rid==rrid]) + "}\n"
                if rname[0] == "s":  # sea regions
                    soutf.write(buffer + "}\n\n")
                    continue
                outf.write(buffer + "\tsubsistence_building = \"building_subsistence_farms\"\n")
                if rid in traits_from_rid:
                    outf.write("\ttraits = { " + " ".join(["\""+trait+"\"" for trait in traits_from_rid[rid]]) + " }\n")
                if rid in locs_from_rid:
                    for loc, pid in locs_from_rid[rid].items():
                        if loc in VALID_LOCS:
                            outf.write(f"\t{loc} = \"{hex_rgb(*rgb_from_pid[pid])}\"\n")
                    arable_land, arable_types = arable_from_rid[rid]
                    outf.write("\n\tarable_land = "+str(arable_land) +"\n\tarable_resources = { "+" ".join(["\""+atype+"\"" for atype in arable_types]) + " }\n\tcapped_resources = {\n")
                    outf.write("\n".join(["\t\t" + ctype + " = " + str(camount) for ctype, camount in capped_from_rid[rid].items()]) + "\t}\n")
                    if "port" in locs_from_rid[rid]:
                        outf.write("\tnaval_exit_id = " + str(coast_from_rid[rid]) + "\n")
                outf.write("}\n\n")


def create_mod(file_dir, config, pid_from_cube, rid_from_pid, terr_from_cube, terr_from_pid, rgb_from_pid, height_from_cube, river_edges, river_vertices, locs_from_rid, coast_from_rid, name_from_rid):
    """Creates the V3 mod files in file_dir, given the basic data."""
    # Make the basic filestructure that other things go in.
    file_dir = create_dot_mod(file_dir=file_dir, mod_name=config.get("MOD_NAME", "testmod"), mod_disp_name=config.get("MOD_DISPLAY_NAME", "testing_worldgen"))
    rgb_from_cube = {k:rgb_from_pid[pid] for k, pid in pid_from_cube.items()}
    # Maps
    v3map = V3Map(file_dir=file_dir, max_x=config["max_x"], max_y=config["max_y"], n_x=config["n_x"], n_y=config["n_y"])
    v3map.create_provinces(rgb_from_cube=rgb_from_cube)
    v3map.create_heightmap(height_from_cube=height_from_cube)
    river_background = {k.tuple():255 if v > WATER_HEIGHT else 254 for k,v in height_from_cube.items()}
    v3map.create_rivers(river_background, river_edges, river_vertices, base_loc=os.path.join(config["BASE_V3_DIR"], "map_data", "rivers.png"))
    v3map.create_terrain_masks(file_dir=file_dir, base_dir=config["BASE_V3_DIR"], terr_from_cube=terr_from_cube)
    create_terrain_file(file_dir, terr_from_pid=terr_from_pid, rgb_from_pid=rgb_from_pid)
    traits_from_rid = {}
    arable_from_rid = {r: (10, ["bg_wheat_farms", "bg_livestock_ranches"]) for r in locs_from_rid.keys()}
    capped_from_rid = {r: {"bg_lead_mining": 10, "bg_iron_mining": 10, "bg_logging": 10, "bg_coal_mining": 10} for r in locs_from_rid.keys()}
    create_states(
        file_dir=file_dir,
        rid_from_pid=rid_from_pid,
        rgb_from_pid=rgb_from_pid,
        name_from_rid=name_from_rid,
        traits_from_rid=traits_from_rid,
        locs_from_rid=locs_from_rid,
        arable_from_rid=arable_from_rid,
        capped_from_rid=capped_from_rid,
        coast_from_rid=coast_from_rid,
    )

    strip_base_files(
        file_dir=file_dir,
        src_dir=config["BASE_V3_DIR"],
        subpaths=[
            "common/decisions",
            "events"
        ],
        to_remove=["c:"],  # Possibly this should be the list of historical tags instead?
        to_keep=[],
        subsection=["triggered_desc = {", "option = {"],
    )
    create_blanks(file_dir=file_dir)