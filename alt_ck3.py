import os

from alt_map import *
from terrain import *

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

# PROVINCES constants
IMPASSABLE = (0, 0, 255)


class CK3Map:
    def __init__(self, file_dir, max_x, max_y, n_x, n_y):
        """Creates a map of size max_x * max_y, which is n_x hexes wide and n_y hexes tall."""
        self.file_dir = file_dir
        os.makedirs(os.path.join(file_dir, "map_data"), exist_ok=True)
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

    def create_terrain_masks(self, terr_from_cube):
        """Creates all the terrain masks; just fills each cube."""
        raise NotImplementedError
    
    def create_rivers(self):
        """Determine which rivers are major rivers and create rivers.png"""
        raise NotImplementedError

def create_terrain_file(file_dir, terr_from_pid):
    """Writes out common/province_terrain."""
    # Masks were historically wrapped into create_heightmap, and should maybe be again.
    os.makedirs(os.path.join(file_dir, "common", "province_terrain"), exist_ok=True)
    with open(os.path.join(file_dir, "common", "province_terrain", "00_province_terrain.txt"), 'w') as outf:
        outf.write("default_land=plains\ndefault_sea=sea\ndefault_coastal_sea=coastal_sea\n")
        for pid, terr in terr_from_pid.items():
            outf.write(f"{str(pid)}={CK3Terrain_from_BaseTerrain[terr].name}\n")


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


def create_climate(file_dir):
    """Creates the climate file."""
    # TODO: Actually determine climate from location / terrain / etc.
    os.makedirs(os.path.join(file_dir, "map_data"), exist_ok=True)
    with open(os.path.join(file_dir, "map_data","climate.txt"),'w') as outf:
        outf.write("mild_winter = {\n}\nnormal_winter = {\n}\nsevere_winter = {\n}\n")

def create_coa(file_dir, base_dir, custom_dir, title_list):
    """Populate common/coat_of_arms/coat_of_arms/01 and 90 with all the titles in title_list, drawing first from custom_dir and then from base_dir."""
    os.makedirs(os.path.join(file_dir, "common", "coat_of_arms", "coat_of_arms"), exist_ok=True)
    with open(os.path.join(file_dir, "common", "coat_of_arms", "coat_of_arms","01_landed_titles.txt"),'w') as outf:
        for src_dir in [custom_dir, base_dir]:
            if src_dir is None:
                continue
            with open(os.path.join(src_dir, "01_landed_titles.txt"), 'r') as inf:
                brackets = 0
                title_name = ""
                buffer = ""
                for line in inf.readlines():
                    line = line.split("#")[0]  # Drop all comments
                    brackets += line.count("{")
                    if len(title_name) == 0 and brackets == 1:
                        title_name = line.split("=")[0].strip()
                    if title_name in title_list:
                        buffer += line
                    brackets -= line.count("}")
                    if brackets == 0 and len(title_name) > 0:
                        if title_name in title_list:
                            title_list.remove(title_name)
                            buffer += line
                            outf.write(buffer)
                        title_name = ""
                        buffer = ""
    print(f"After processing coats of arms, there were {len(title_list)} titles without coas.")


def create_geographical_regions(file_dir, regions, all_material_types = None, no_material_types=None, all_animal_types=None, no_animal_types=None):
    """Create the geographical_regions/geographical_region.txt file.
    regions is a list of RegionTrees.
    This includes a bunch of material / animal things which could maybe be customized--but for now I'm going to leave this to the end user."""
    if all_material_types is None:
        all_material_types = ["wood_elm", "wood_walnut", "wood_maple", "woods_pine_and_fir", "woods_yew", "woods_dogwood", "woods_hazel", "cloth_linen", "hsb_deer_antler", "hsb_boar_tusk", "hsb_seashell",]
    if no_material_types is None:
        no_material_types = ["woods_subsaharan", "woods_paduak", "woods_india", "woods_india_burma", "woods_ebony", "woods_bamboo", "woods_cherry", "woods_hickory", "woods_palm", "woods_mulberry", "woods_mediterranean", "woods_sri_lanka", "cloth_no_silk","cloth_cotton", "metal_wootz", "metal_damascus", "metal_bulat", "hsb_camel_bone", "hsb_ivory_imported", "hsb_ivory_native", "hsb_mother_of_pearl", "hsb_tortoiseshell", ]
    if all_animal_types is None:
        all_animal_types = ["deer", "boar", "bear"]
    if no_animal_types is None:
        no_animal_types = ["antelope", "gazelle", "big_cat", "bison", "aurochs", "reindeer", "elk"]
    graphical_types = {
        "western": "255 0 0",
        "mena": "255 255 0",
        "india": "0 255 0",
        "mediterranean": "0 0 255",
        "steppe": "0 255 255"
    }
    os.makedirs(os.path.join(file_dir, "map_data", "geographical_regions"), exist_ok=True)
    with open(os.path.join(file_dir, "map_data", "geographical_regions", "geographical_region.txt"),'w') as outf:
        all_regions = []
        for region in regions:
            region_title = "world_" + region.title.split("_")[1]
            all_regions.append(region_title)
            outf.write(region_title + " = {\n\tduchies= {\n\t\t")
            outf.write(" ".join([x for x in region.all_ck3_titles() if x[0] == 'd']))
            outf.write("\t}\n}\n")
        all_regions = " ".join(all_regions)
        for material in all_material_types:
            outf.write("material_"+material+" = {\n\tregions = {\n\t\t"+all_regions+"\n\t}\n}\n")
        for material in no_material_types:
            outf.write("material_"+material+" = {\n\tregions = {\n\t\t\n\t}\n}\n")
        for graphical, color in graphical_types.items():
            buffer = all_regions if graphical == "western" else ""
            outf.write("graphical_" + graphical + " {\n\tgraphical=yes\n\tcolor={ "+color+" }\n\tregions = {\n\t\t"+buffer+"\n\t}\n}\n")
        for animal in all_animal_types:
            outf.write("hunt_animal_"+animal+"_region = {\n\tregions = {\n\t\t"+all_regions+"\n\t}\n}\n")
        for animal in no_animal_types:
            outf.write("hunt_animal_"+animal+"_region = {\n\tregions = {\n\t\t\n\t}\n}\n")
    with open(os.path.join(file_dir, "map_data", "island_region.txt"),'w') as outf:
        # TODO: figuring out islands will depend on chunking the land elsewhere. For this basic one, we're fine.
        outf.write("\n")


def create_landed_titles(file_dir, pid_from_title, regions, special_titles=None):
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
                        try:
                            outf.write("\t\t\t" + county.title + " = {\n")
                        except:
                            print(county)
                        outf.write("\t\t\t\tcolor = { " + " ".join(county.color) + " }\n")
                        for barony in county.children:
                            outf.write("\t\t\t\t" + barony + " = {\n")
                            outf.write("\t\t\t\t\tprovince = " + str(pid_from_title[barony]) + "\n")
                            outf.write("\t\t\t\t\tcolor = { " + " ".join(county.color) + " }\n\t\t\t\t}\n")
                        outf.write("\t\t\t}\n")
                    outf.write("\t\t}\n")
                outf.write("\t}\n")
            outf.write("}\n")


def create_history(file_dir, regions):
    """Create the history files"""
    os.makedirs(os.path.join(file_dir, "history", "wars"), exist_ok=True)
    with open(os.path.join(file_dir, "history","wars","00_landed_titles.txt"), 'w') as outf:
        outf.write("\n")
    os.makedirs(os.path.join(file_dir, "history", "province_mapping"), exist_ok=True)
    with open(os.path.join(file_dir, "history","province_mapping","00_world.txt"), 'w') as outf:
        outf.write("\n")
    

def strip_base_files(file_dir, src_dir, subpaths):
    """There's a bunch of base game files that are necessary but contain _some_ hardcoded references to provinces.
    Rather than having to manually remove them, let's try to do it automatically.
    
    Currently known to work with the following subpaths:
    - 
    and suspected to work with:
    - common/travel/point_of_interest_types/travel_point_of_interest_types.txt  # TODO: add poi_grand_city for the central cities.
    """
    expanded_subpaths = []
    while len(subpaths) > 0:
        subpath = subpaths.pop()
        if os.path.isdir(os.path.join(src_dir, subpath)):
            subpaths.extend([os.path.join(src_dir, subpath, more) for more in os.listdir(os.path.join(src_dir, subpath))])
        else:
            expanded_subpaths.append(subpath)

    for subpath in expanded_subpaths:
        file_stripped = False
        file_buffer = ""
        with open(os.path.join(src_dir, subpath), encoding='utf-8') as inf:
            valid = True
            brackets = 0
            mod_brackets = 0
            mod = False
            buffer = ""
            mod_buffer = ""
            for line in inf:
                brackets += line.count("{")
                if brackets > 0 and ("province:" in line or "title:" in line or "character:" in line):
                    valid = False
                    file_stripped = True
                if brackets > 0 and valid and "modifier = {" in line:
                    mod = True
                    mod_brackets = brackets - 1  # This is when it closes
                if mod:
                    mod_buffer += line
                elif valid:
                    buffer += line
                brackets -= line.count("}")
                if mod and brackets == mod_brackets:
                    if valid:
                        buffer += mod_buffer
                        mod_buffer = ""
                    else:
                        valid = True
                        mod_buffer = ""
                    mod = False
                if brackets == 0:
                    if valid and mod:
                        print(f"There's an issue with parsing {subpath}")
                    elif valid:
                        file_buffer = file_buffer + buffer
                    buffer = ""
                    valid = True
        if file_stripped:  # We did a replacement, so need to write out buffer.
            relpath = os.path.relpath(subpath,src_dir)
            print(relpath)
            os.makedirs(os.path.join(file_dir, os.path.dirname(relpath)), exist_ok=True)
            with open(os.path.join(file_dir, relpath), 'w', encoding='utf-8') as outf:
                outf.write(file_buffer)


def create_default_map(file_dir, impassable, sea_min, sea_max):
    """Writes out default.map."""
    os.makedirs(os.path.join(file_dir, "map_data"), exist_ok=True)
    with open(os.path.join(file_dir, "map_data", "default.map"), 'w', encoding='utf-8') as outf:
        outf.write("""definitions = "definition.csv"\nprovinces = "provinces.png"\n#positions = "positions.txt"\nrivers = "rivers.png"\n#terrain_definition = "terrain.txt"\ntopology = "heightmap.heightmap"\n#tree_definition = "trees.bmp"\ncontinent = "continent.txt"\nadjacencies = "adjacencies.csv"\n#climate = "climate.txt"\nisland_region = "island_region.txt"\nseasons = "seasons.txt"\n\n""")
        outf.write("sea_zones = RANGE { "+str(sea_min)+" "+str(sea_max)+" }\n\n")
        for impid in impassable:
            outf.write("impassable_mountains = LIST { "+str(impid)+" }\n")
        outf.write("\n")


def create_dot_mod(file_dir, mod_name, mod_disp_name):
    """Creates the basic mod structure.
    -common
    --decisions
    --landed_titles
    --province_terrain
    --religion
    --travel
    ---point_of_interest_types
    -events
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


def create_mod(file_dir, config, pid_from_cube, terr_from_cube, terr_from_pid, rgb_from_pid, height_from_cube, pid_from_title, name_from_pid, region_trees, impassable):
    """Creates the CK3 mod files in file_dir, given the basic data."""
    # Make the basic filestructure that other things go in.
    create_dot_mod(file_dir=file_dir, mod_name=config.get("MOD_NAME", "testmod"), mod_disp_name=config.get("MOD_DISPLAY_NAME", "testing_worldgen"))
    # make common
    all_titles = []
    for region_tree in region_trees:
        all_titles.extend(region_tree.all_ck3_titles())
    print(f"there are {len(all_titles)} titles.")
    create_coa(file_dir, base_dir=os.path.join(config["BASE_CK3_DIR"], "common", "coat_of_arms", "coat_of_arms"), custom_dir=config.get("COA_DIR", None), title_list=all_titles)
    create_landed_titles(file_dir, pid_from_title, region_trees)  # TODO: add special_titles
    create_terrain_file(file_dir=file_dir, terr_from_pid=terr_from_pid)
    # make history
    # Make map
    map = CK3Map(file_dir,config["max_x"], config["max_y"], config["n_x"], config["n_y"])
    map.create_provinces(rgb_from_pid,pid_from_cube, name_from_pid)
    map.create_heightmap(height_from_cube=height_from_cube)
    # map.create_terrain_masks
    create_geographical_regions(file_dir, region_trees)
    if len(impassable) > 0:
        sea_min = max(impassable) + 1
    else:
        sea_min = max(terr_from_pid.values()) + 1  # This is because we never added the sea pids to it.
    sea_max = max(pid_from_cube.values())
    create_default_map(file_dir, impassable, sea_min, sea_max)
