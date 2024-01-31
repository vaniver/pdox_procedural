from enum import Enum
import os

from alt_map import *

CK3Terrain = Enum('CK3Terrain','plains farmlands hills mountains desert desert_mountains oasis jungle forest taiga wetlands steppe floodplains drylands')

TERRAIN_HEIGHT = {
    CK3Terrain.farmlands: (0,1), CK3Terrain.plains: (0,1), CK3Terrain.floodplains: (0,1), CK3Terrain.taiga: (0,1),
    CK3Terrain.wetlands: (0,1), CK3Terrain.steppe: (0,1), CK3Terrain.drylands: (0,1),
    CK3Terrain.oasis: (0,1), CK3Terrain.desert: (0,1),
    CK3Terrain.jungle: (1,3), CK3Terrain.forest: (1,3),
    CK3Terrain.hills: (1,5), 
    CK3Terrain.mountains: (3,10),  CK3Terrain.desert_mountains: (3,10),
}

TERRAIN_MASK_TYPES = [
    'beach_02', 'beach_02_mediterranean', 'beach_02_pebbles', 'coastline_cliff_brown', 'coastline_cliff_desert',
    'coastline_cliff_grey', 'desert_01', 'desert_02', 'desert_cracked', 'desert_flat_01', 'desert_rocky',
    'desert_wavy_01_larger', 'desert_wavy_01', 'drylands_01_cracked', 'drylands_01_grassy', 'drylands_01',
    'drylands_grass_clean', 'farmland_01', 'floodplains_01', 'forestfloor_02', 'forestfloor', 'forest_jungle_01',
    'forest_leaf_01', 'forest_pine_01', 'hills_01', 'hills_01_rocks', 'hills_01_rocks_medi', 'hills_01_rocks_small',
    'india_farmlands', 'medi_dry_mud', 'medi_farmlands', 'medi_grass_01', 'medi_grass_02', 'medi_hills_01',
    'medi_lumpy_grass', 'medi_noisy_grass', 'mountain_02_b', 'mountain_02_c', 'mountain_02_c_snow',
    'mountain_02_desert_c', 'mountain_02_desert', 'mountain_02_d_desert', 'mountain_02_d', 'mountain_02_d_snow',
    'mountain_02_d_valleys', 'mountain_02', 'mountain_02_snow', 'mud_wet_01', 'northern_hills_01',
    'northern_plains_01', 'oasis', 'plains_01_desat', 'plains_01_dry', 'plains_01_dry_mud', 'plains_01',
    'plains_01_noisy', 'plains_01_rough', 'snow', 'steppe_01', 'steppe_bushes', 'steppe_rocks', 'wetlands_02',
    'wetlands_02_mud'
    ]

USED_MASKS = {
    None: 'beach_02', 
    CK3Terrain.farmlands: 'farmland_01',
    CK3Terrain.plains: 'plains_01', 
    CK3Terrain.floodplains: 'floodplains_01', 
    CK3Terrain.taiga: 'snow',
    CK3Terrain.wetlands: 'wetlands_02',
    CK3Terrain.steppe: 'steppe_01',
    CK3Terrain.drylands: 'drylands_01',
    CK3Terrain.oasis: 'oasis', 
    CK3Terrain.desert: 'desert_01',
    CK3Terrain.jungle: 'forest_jungle_01',
    CK3Terrain.forest: 'forest_leaf_01',
    CK3Terrain.hills: 'hills_01',
    CK3Terrain.mountains: 'mountain_02',
    CK3Terrain.desert_mountains: 'mountain_02_desert_c',
}

MAP_OBJECT_MASK_TYPES = [
    'reeds_01_mask.png', 'steppe_bush_01_mask.png', 'tree_cypress_01_mask.png', 'tree_jungle_01_c_mask.png',
    'tree_jungle_01_d_mask.png', 'tree_leaf_01_mask.png', 'tree_leaf_01_single_mask.png', 'tree_leaf_02_mask.png',
    'tree_palm_01_mask.png', 'tree_pine_01_a_mask.png', 'tree_pine_01_b_mask.png', 'tree_pine_impassable_01_a_mask.png'
    ]

USED_MOBJ_MASKS = {
    CK3Terrain.jungle: 'tree_jungle_01_c_mask.png',
    CK3Terrain.forest: 'tree_leaf_01_mask.png',
}

# HEIGHTMAP constants
WATER_HEIGHT = 18

# PROVINCES constants
IMPASSABLE = (0, 0, 255)

# RIVERS constants
MAJOR_RIVER_THRESHOLD = 9
RIVER_EXTEND = 3
RIVER_BRANCH_CHANCE = 0.5
SOURCE = 0
MERGE = 1
SPLIT = 2
WATER = 254
LAND = 255

# I've got some things:
# - a cube_from_pid for each continent where each barony is assigned a unique pid
# - a landed title tree for each continent which uses the barony pid
# - some ocean stuff idk

# I think what's convenient for the maps is:
# - a mapping between cubes and (r,g,b) tuples
# - a mapping between pids and (r,g,b) tuples  (I would do the V3 thing everywhere but the other games insist on pids)


def create_title_tree():
    """Given the config file, determine name_from_pid and the title tree."""
    # I'm not actually sure what needs to be done here. It looks like most things key off of title name,
    # and so we don't actually really need to link up the pid and the title tree?

    # We do need name_from_pid. 


class CK3Map:
    def __init__(self, file_dir, max_x, max_y, n_x, n_y):
        """Creates a map of size max_x * max_y, which is n_x hexes wide and n_y hexes tall."""
        self.file_dir = file_dir
        self.max_x = max_x
        self.max_y = max_y
        self.n_x = n_x
        self.n_y = n_y

    def create_provinces(self, rgb_from_pid, pid_from_cube, name_from_pid):
        """Creates provinces.png and definition.csv"""
        rgb_from_ijk = {}
        for k, pid in pid_from_cube.items():
            rgb_from_ijk[k.tuple()] = rgb_from_pid[pid]
        img = create_hex_map(rgb_from_ijk=rgb_from_ijk, max_x=self.max_x, max_y=self.max_y, mode='RGB', default="black", n_x=self.n_x, n_y=self.n_y)
        img.save(os.path.join(self.file_dir, "map_data", "provinces.png"))
        with open(os.path.join(self.file_dir, "map_data", "definitions.csv"), 'w') as outf:
            outf.write("0;0;0;0;x;x;\n")
            for pid, name in name_from_pid.items():
                r,g,b = rgb_from_pid[pid]
                outf.write(";".join([str(x) for x in [pid,r,g,b,name,"x"]])+"\n")


    def create_heightmap(self, height_from_cube):
        """Placeholder that just uses land/sea to generate a simple heightmap."""
        rgb_from_ijk = {k.tuple(): v for k,v in height_from_cube.items()}
        img = create_hex_map(rgb_from_ijk=rgb_from_ijk, max_x=self.max_x, max_y=self.max_y, mode='L', default="white", n_x=self.n_x, n_y=self.n_y)
        img.save(os.path.join(self.file_dir, "map_data", "heightmap.png"))
        with open(os.path.join(self.file_dir, "map_data", 'heightmap.heightmap'), 'w') as f:
            f.write("heightmap_file=\"map_data/packed_heightmap.png\"\n")
            f.write("indirection_file=\"map_data/indirection_heightmap.png\"\n")
            f.write(f"original_heightmap_size={{ {self.max_x} {self.max_y} }}\n")
            f.write("tile_size=33\n")
            f.write("should_wrap_x=no\n")
            f.write("level_offsets={ { 0 0 }{ 0 0 }{ 0 0 }{ 0 0 }{ 0 7 }}\n")


def create_terrain(file_dir):
    """Creates all the terrain masks."""
    # Was historically wrapped into create_heightmap.
    raise NotImplementedError


def create_adjacencies(file_dir, straits, cube_from_pid, name_from_pid, closest_xy = None):
    """straits is a list of (id, id, id) pairs.
    This function will create the adjacencies file (including some calculations about type and positioning)."""
    with open(os.path.join(file_dir, "map_data", "adjacencies.csv"), 'w') as outf:
        outf.write("From;To;Type;Through;start_x;start_y;stop_x;stop_y;Comment\n")
        for strait in straits:
            buffer = list(strait)
            fr, to = cube_from_pid[strait[0]], cube_from_pid[strait[1]]
            if fr.sub(to).mag() == 1:
                buffer.insert(2,"river_large")
            else:
                buffer.insert(2,"sea")
            if closest_xy is None:
                buffer.extend([-1] * 4)
            else:
                buffer.extend(closest_xy(fr,to))
                buffer.extend(closest_xy(to, fr))
            buffer.extend(name_from_pid[fr] + "-" + name_from_pid[to])
            outf.write(";".join([str(x) for x in buffer])+"\n")
        outf.write("-1;-1;;-1;-1;-1;-1;-1;\n")


def make_coa(file_dir, base_dir, custom_dir, title_list):
    """Populate common/coat_of_arms/coat_of_arms/01 and 90 with all the titles in title_list, drawing first from custom_dir and then from base_dir."""
    os.makedirs(os.path.join(file_dir, "common", "coat_of_arms", "coat_of_arms"), exist_ok=True)
    with open(os.path.join(file_dir, "common", "coat_of_arms", "coat_of_arms","01_landed_titles.txt"),'w') as outf:
        for src_dir in [custom_dir, base_dir]:
            if src_dir is None:
                continue
            with open(os.path.join(src_dir, "01_landed_titles.txt"), 'r') as inf:
                brackets = 0
                title_name = ""
                for line in inf.readlines():
                    line = line.split("#")[0]  # Drop all comments
                    brackets += line.count("{")
                    if brackets == 1:
                        title_name = line.split("=")[0].strip()
                    if title_name in title_list:
                        outf.write(line)
                    brackets -= line.count("}")
                    if brackets == 0 and len(title_name) > 0:
                        title_list.remove(title_name)
                        title_name = ""
    print(f"After processing coats of arms, there were {len(title_list)} titles without coas.")


def make_landed_titles(file_dir, pid_from_title, regions, special_titles=None):
    """Make common/landed_titles."""
    os.makedirs(os.path.join(file_dir, "common", "landed_titles"), exist_ok=True)
    with open(os.path.join(file_dir, "common", "landed_titles","00_landed_titles.txt"), 'w') as outf:
        # Write the special titles out
        if special_titles is not None:
            with open(special_titles) as inf:
                for line in inf.readlines():
                    outf.write(line)
        # Write out the main titles
        for empire in regions:
            outf.write(empire.title + " = {\n")
            outf.write("\tcolor = { " + " ".join(empire.color) + " }\n")
            outf.write("\tcapital = " + empire.capital()+"\n\n")
            for kingdom in empire.children:
                outf.write("\t" + kingdom.title + " = {\n")
                outf.write("\t\tcolor = { " + " ".join(kingdom.color) + " }\n")
                outf.write("\t\tcapital = " + kingdom.capital()+"\n\n")
                for duchy in kingdom.children:
                    outf.write("\t\t" + duchy.title + " = {\n")
                    outf.write("\t\t\tcolor = { " + " ".join(duchy.color) + " }\n")
                    outf.write("\t\t\tcapital = " + duchy.capital()+"\n\n")
                    for county in duchy.children:
                        outf.write("\t\t\t" + county.title + " = {\n")
                        outf.write("\t\t\t\tcolor = { " + " ".join(county.color) + " }\n")
                        for barony in county.children:
                            outf.write("\t\t\t\t" + barony + " = {\n")
                            outf.write("\t\t\t\t\tprovince = " + str(pid_from_title[barony]) + "\n")
                            outf.write("\t\t\t\t\tcolor = { " + " ".join(county.color) + " }\n\t\t\t\t}\n")
                        outf.write("\t\t\t}\n")
                    outf.write("\t\t}\n")
                outf.write("\t}\n")
            outf.write("}\n")


def make_dot_mod(file_dir, mod_name, mod_disp_name):
    """Creates the basic mod structure.
    -common
    --decisions
    --landed_titles
    --province_terrain
    --religion
    --travel
    ---point_of_interest_types
    -events
    --TODO: catch em' all
    -history
    --characters
    --cultures
    --province_mapping
    --provinces
    --titles
    --wars
    -map_data
    --geographical_regions
"""
    shared = "version = \"0.0.1\"\n"
    shared += "tags = {\n\t\"Total Conversion\"\n}\n"
    shared += "name = \"{}\"\n".format(mod_disp_name)
    shared += "supported_version = \"1.11.4\"\n"
    outer = "path = \"mod/{}\"\n".format(mod_name)
    
    replace_paths = [
        "common/bookmark_portraits", "common/culture/innovations", "common/dynasties",
        "history/characters", "history/cultures", "history/province_mappings", "history/provinces", "history/titles", "history/wars"
        ]
    shared += "replace_path = \"" + "\"\nreplace_path = \"".join(replace_paths)+"\""
    os.makedirs(os.path.join(file_dir, mod_name), exist_ok=True)
    with open(os.path.join(file_dir,"{}.mod".format(mod_name)),'w') as f:
        f.write(shared + outer)
    with open(os.path.join(file_dir, mod_name, "descriptor.mod".format(mod_name)),'w') as f:
        f.write(shared)


def create_mod(file_dir, config, pid_from_cube, terr_from_cube, rgb_from_pid, height_from_cube, pid_from_title, name_from_pid, region_tree):
    """Creates the CK3 mod files in file_dir, given the basic data."""
    # Make the basic filestructure that other things go in.
    make_dot_mod(file_dir=file_dir)
    # make common
    make_coa(file_dir, base_dir=os.path.join(config["BASE_DIR"], "common", "coat_of_arms", "coat_of_arms"), custom_dir=config.get("COA_DIR", None), title_list=region_tree.all_ck3_titles("CK3"))
    make_landed_titles(file_dir, pid_from_title, region_tree.children)  # TODO: add special_titles
    # make history
    # Make map
    map = CK3Map(file_dir,config["max_x"], config["max_y"], config["n_x"], config["n_y"])
    map.create_provinces(rgb_from_pid,pid_from_cube, name_from_pid)
