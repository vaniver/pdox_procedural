from math import sqrt
import os
import random
import yaml

from basic_map import BasicMap
from map_io import *
from stripper import copy_base_files, create_blanks, strip_base_files
from terrain import *

USED_MASKS = {  # Not obvious this should go in this direction.
    BaseTerrain.plains: "plains_01",
    BaseTerrain.farmlands: "farmland_01",
    BaseTerrain.hills: "hills_01",
    BaseTerrain.mountains: "mountain_02",
    BaseTerrain.forest: "forest_leaf_01",
    BaseTerrain.desert: "desert_01",
    BaseTerrain.marsh: "wetlands_02",
    BaseTerrain.jungle: "forest_jungle_01",
    BaseTerrain.ocean: "beach_02",
}

CONTENT_SOURCES = {
    BaseTerrain.forest: "tree_leaf_01",
    BaseTerrain.jungle: "tree_jungle_01_d",
}

MAIN_OFFSETS = ["building", "combat", "player_stack", "siege"]

OFFSETS = {
    "building": (0,0),
    "combat": (0.2, 0),
    "player_stack": (0.2, 0.1),
    "siege": (0.1, 0),
    "other_stack": (0.2, -0.1),
    "stack": (0.2, -0.1),
    "special_building": (-0.1, 0.1),
    "activities": (-0.1, -0.1),
}

ZEROS = ["combat", "player_stack", "other_stack", "stack"]

CLAMP = {
    "building": "yes",
    "combat": "yes",
    "player_stack": "yes",
    "siege": "no",
    "other_stack": "yes",
    "stack": "yes",
    "special_building": "yes",
    "activities": "no",
}

LAYERS = {
    "building": "building",
    "combat": "unit",
    "player_stack": "unit",
    "siege": "unit",
    "other_stack": "unit",
    "stack": "unit",
    "special_building": "building",
    "activities": "activities",
}

class CK3Map(BasicMap):
    def __init__(self, file_dir, max_x, max_y, n_x, n_y):
        """Creates a map of size max_x * max_y, which is n_x hexes wide and n_y hexes tall."""
        super().__init__(file_dir, "map_data", max_x, max_y, n_x, n_y)

    def prov_extra(self, rgb_from_pid, pid_from_cube, name_from_pid):
        """Creates definition.csv"""
        with open(os.path.join(self.file_dir, self.map_dir, "definition.csv"), 'w') as outf:
            outf.write("0;0;0;0;x;x;\n")
            for pid in sorted(name_from_pid.keys()):
                name = name_from_pid[pid]
                r,g,b = rgb_from_pid[pid]
                outf.write(";".join([str(x) for x in [pid,r,g,b,name,"x"]])+"\n")

    def height_extra(self):
        """Uses height_from_cube to generate a simple heightmap."""
        with open(os.path.join(self.file_dir, self.map_dir, 'heightmap.heightmap'), 'w') as outf:
            outf.write("heightmap_file=\"map_data/packed_heightmap.png\"\n")
            outf.write("indirection_file=\"map_data/indirection_heightmap.png\"\n")
            outf.write(f"original_heightmap_size={{ {self.max_x} {self.max_y} }}\n")
            outf.write("tile_size=33\n")
            outf.write("should_wrap_x=no\n")
            outf.write("level_offsets={ { 0 0 }{ 0 0 }{ 0 0 }{ 0 0 }{ 0 7 }}\n")

    def create_terrain_masks(self, file_dir, base_dir, terr_from_cube, tree_sparsity=(8,8)):
        """Creates all the terrain masks; just fills each cube.
        terr_from_cube is a map from cube to BaseTerrain.
        Also creates flatmap.dds and colormap.dds."""
        os.makedirs(os.path.join(file_dir, "gfx", "map", "terrain"), exist_ok=True)
        os.makedirs(os.path.join(file_dir, "content_source", "map_objects", "masks"), exist_ok=True)
        for mask in os.listdir(os.path.join(base_dir, "gfx", "map", "terrain")):
            if "mask.png" not in mask:
                continue
            mask_name = mask.split("_mask")[0]
            if mask_name not in USED_MASKS.values():
                create_hex_map(rgb_from_ijk={}, max_x=self.max_x, max_y=self.max_y, n_x=self.n_x, n_y=self.n_y, mode='L', default="black").save(os.path.join(file_dir, "gfx", "map", "terrain", mask))
            else:
                terrain = [k for k,v in USED_MASKS.items() if v == mask_name][0]
                rgb_from_cube = {k.tuple(): 128 for k,v in terr_from_cube.items() if v == terrain}
                create_hex_map(rgb_from_ijk=rgb_from_cube, max_x=self.max_x, max_y=self.max_y, n_x=self.n_x, n_y=self.n_y, mode='L', default="black").save(os.path.join(file_dir, "gfx", "map", "terrain", mask))
        create_hex_map(rgb_from_ijk={}, max_x=self.max_x // 4, max_y=self.max_y // 4, n_x=self.n_x, n_y=self.n_y, mode='RGB', default=(127, 127, 127)).save(os.path.join(file_dir, "gfx", "map", "terrain", "colormap.dds"))
        rgb_from_cube = {k.tuple(): (120, 120, 100) if v == BaseTerrain.ocean else (170,160,140) for k,v in terr_from_cube.items()}
        create_hex_map(rgb_from_ijk=rgb_from_cube, max_x=self.max_x, max_y=self.max_y, n_x=self.n_x, n_y=self.n_y, mode='RGB', default="black").save(os.path.join(file_dir, "gfx", "map", "terrain", "flatmap.dds"))
        for mask in os.listdir(os.path.join(base_dir, "content_source", "map_objects", "masks")):
            mask_name = mask.split("_mask")[0]
            if mask_name not in CONTENT_SOURCES.values():
                create_hex_map(rgb_from_ijk={}, max_x=self.max_x//2, max_y=self.max_y//2, n_x=self.n_x, n_y=self.n_y, mode='L', default="black").save(os.path.join(file_dir, "content_source", "map_objects", "masks", mask))
            else:
                terrain = [k for k,v in CONTENT_SOURCES.items() if v == mask_name][0]
                rgb_from_cube = {k.tuple(): random.randint(64,192) for k,v in terr_from_cube.items() if v == terrain}
                create_hex_map(rgb_from_ijk=rgb_from_cube, max_x=self.max_x//2, max_y=self.max_y//2, n_x=self.n_x, n_y=self.n_y, mode='L', default="black").save(os.path.join(file_dir, "content_source", "map_objects", "masks", mask))

        
    def create_flowmap(self, file_dir, terr_from_cube):
        os.makedirs(os.path.join(file_dir, "gfx", "map", "water"), exist_ok=True)
        rgb_from_ijk = {}
        for cube, terr in terr_from_cube.items():
            if terr == BaseTerrain.ocean:
                flow = 33 * random.randint(0,2)
                rgb_from_ijk[cube.tuple()] = (flow, flow, flow)
            else:
                rgb_from_ijk[cube.tuple()] = (255, 255, 255)
        create_hex_map(rgb_from_ijk=rgb_from_ijk, max_x=self.max_x // 8, max_y=self.max_y // 8, n_x=self.n_x, n_y=self.n_y, mode='RGB', default=(0, 0, 0)).save(os.path.join(file_dir, "gfx", "map", "water", "foam_map.dds"))
        # TODO: Port over flowmap code
        create_hex_map(rgb_from_ijk={}, max_x=self.max_x // 4, max_y=self.max_y // 4, n_x=self.n_x, n_y=self.n_y, mode='RGB', default=(126,130,255)).save(os.path.join(file_dir, "gfx", "map", "water", "flowmap.dds"))

    def surround_mask(self, file_dir, surround_cubes = {}):
        os.makedirs(os.path.join(file_dir, "gfx", "map", "surround_map"), exist_ok=True)
        create_hex_map(rgb_from_ijk={k.tuple(): v for k,v in surround_cubes.items()}, max_x=self.max_x // 8, max_y=self.max_y // 8, n_x=self.n_x, n_y=self.n_y, mode='RGB', default=(255, 255, 0)).save(os.path.join(file_dir, "gfx", "map", "surround_map", "surround_fade.dds"))
        create_hex_map(rgb_from_ijk={k.tuple(): (255,255,255) for k in surround_cubes}, max_x=self.max_x // 2, max_y=self.max_y // 2, n_x=self.n_x, n_y=self.n_y, mode='RGB', default=(0, 0, 0)).save(os.path.join(file_dir, "gfx", "map", "surround_map", "surround_mask.dds"))

    def create_positions(self, name_from_pid, pid_from_cube, file_dir,):
        """Create positions.txt and gfx/map/map_object_data files"""
        os.makedirs(os.path.join(file_dir, "gfx", "map", "map_object_data"), exist_ok=True)
        buffers = {name: f"game_object_locator={{\n\tname=\"{name}\"\n\trender_pass=Map\n\tclamp_to_water_level={CLAMP[name]}\n\tgenerated_content=no\n\tlayer=\"{LAYERS[name]}_layer\"\n\tinstances={{\n" for name in OFFSETS}
        for otype in ZEROS:
            buffers[otype] += "\t\t{\n\t\t\tid=0\n\t\t\tposition={ 0.0 0.0 0.0 }\n\t\t\trotation={ -0.0 -0.0 -0.0 1.0 }\n\t\t\tscale={ 1.0 1.0 1.0 }\n\t\t}\n"
        with open(os.path.join(self.file_dir, self.map_dir, "positions.txt"), 'w', encoding="utf_8_sig") as outf:
            rotation = " ".join([str(s) for s in [0] * 5])
            height = " ".join([str(s) for s in [0, 0, 0, 20, 0]])
            for pid, name in sorted(name_from_pid.items()):
                cube = [k for k,v in pid_from_cube.items() if v == pid]
                if len(cube) == 0:
                    print(pid, name)
                    continue
                elif len(cube) == 1:
                    cube = cube[0]
                else:
                    cube = random.sample(cube, k=1)[0]
                start_x, start_y = xy_from_cube(cube, self.box_width, self.box_height)
                start_x += 2*self.box_width
                start_y += self.box_height
                position = ""
                for otype, (offx, offy) in OFFSETS.items():
                    x = max(min(start_x + offx*self.box_width, self.max_x), 0)
                    y = max(min(start_y + offy*self.box_height, self.max_y), 0)
                    if otype in MAIN_OFFSETS:
                        position += f" {x} {y}"
                    buffers[otype] += f"\t\t{{\n\t\t\tid={pid}\n\t\t\tposition={{ {x} 0.0 {y} }}\n\t\t\trotation={{ -0.0 -0.0 -0.0 1.0}}\n\t\t\tscale={{ 1.0 1.0 1.0 }}\n\t\t}}\n"
                outf.write(f"#{name}\n\t{pid}=\n\t{{\n\t\tposition=\n\t\t{{\n{position} }}\n\t\trotation=\n\t\t{{\n{rotation} }}\n\t\theight=\n\t\t{{\n{height} }}\n\t}}\n")
        buffers = {k: v + "\t}\n}\n" for k,v in buffers.items()}
        for name, contents in buffers.items():
            if name == "activities":  # It is dumb that we have to hardcode this but it doesn't follow the normal naming convention.
                filename = name + ".txt"
            else:
                filename = name + "_locators.txt"
            with open(os.path.join(self.file_dir, "gfx", "map", "map_object_data", filename), 'w', encoding="utf_8_sig") as outf:
                outf.write(contents)

    def update_defines(self, base_dir):
        """Copies common/defines/00_defines.txt but replaces WORLD_EXTENTS_X and Z."""
        os.makedirs(os.path.join(self.file_dir, "common", "defines"), exist_ok=True)
        with open(os.path.join(base_dir, "common", "defines", "00_defines.txt"), 'r', encoding='utf_8_sig') as inf:
            with open(os.path.join(self.file_dir, "common", "defines", "00_defines.txt"), 'w', encoding='utf_8_sig') as outf:
                for line in inf.readlines():
                    if line.startswith("\tWORLD_EXTENTS_X"):
                        outf.write(line.split("=")[0] + f"= {self.max_x}\n")
                    elif line.startswith("\tWORLD_EXTENTS_Z"):
                        outf.write(line.split("=")[0] + f"= {self.max_y}\n")
                    elif line.startswith("\tWATERLEVEL"):
                        outf.write(line.split("=")[0] + f"= 19.0\n")
                    else:
                        outf.write(line)
        # TODO: Confirm that I don't need to update 00_graphics.txt, mostly CAMERA_START.
    
    def create_bookmarks(self, file_dir, terr_from_cube, bookmark_groups, ):
        """terr_from_cube is used to determine where is land and where is sea; bookmark_groups is a list of tuples:
        group_name, char_name_from_grp, bounds, color_from_grp, edge_color_from_grp, grp_from_cube, grp_from_edge"""
        os.makedirs(os.path.join(file_dir, "gfx", "interface", "bookmarks"), exist_ok=True)
        for group_name, char_name_from_grp, bounds, color_from_grp, edge_color_from_grp, grp_from_cube, grp_from_edge in bookmark_groups:
            # Base picture (everyone has background, darker border)
            rgb_from_ijk = {}
            for cube in subset_from_minmax(*bounds):
                if cube in grp_from_cube:
                    rgb_from_ijk[cube.tuple] = color_from_grp[grp_from_cube[cube]]
                elif terr_from_cube[cube] == BaseTerrain.ocean:
                    rgb_from_ijk[cube.tuple()] = (90, 90, 80)
                else:
                    rgb_from_ijk[cube.tuple()] = (160, 150, 125)
            rgb_from_edge = {edge: edge_color_from_grp[grp] for edge, grp in grp_from_edge.items()}
            create_hex_map(rgb_from_ijk=rgb_from_ijk, rgb_from_edge=rgb_from_edge, max_x=1920, max_y=1080, n_x=bounds[1] - bounds[0], n_y=bounds[3] - bounds[2], mode='RGB', default="black").save(os.path.join(file_dir, "gfx", "interface", "bookmarks", group_name + ".dds"))
            for grp, char_name in char_name_from_grp.items():
                rgb_from_ijk = {cube: (*color_from_grp[grp], 127) for cube, gg in grp_from_cube.items() if grp == gg}
                rgb_from_edge = {edge: (255,255,255,255) for edge, gg in grp_from_edge.items() if grp == gg}
                create_hex_map(rgb_from_ijk=rgb_from_ijk, rgb_from_edge=rgb_from_edge, max_x=1920, max_y=1080, n_x=bounds[1] - bounds[0], n_y=bounds[3] - bounds[2], mode='RGBA', default=(255,255,255,0)).save(os.path.join(file_dir, "gfx", "interface", "bookmarks", group_name + "_" + char_name + ".dds"))

def create_terrain_file(file_dir, terr_from_pid):
    """Writes out common/province_terrain."""
    # Masks were historically wrapped into create_heightmap, and should maybe be again.
    os.makedirs(os.path.join(file_dir, "common", "province_terrain"), exist_ok=True)
    with open(os.path.join(file_dir, "common", "province_terrain", "00_province_terrain.txt"), 'w', encoding="utf_8_sig") as outf:
        outf.write("default_land=plains\ndefault_sea=sea\ndefault_coastal_sea=coastal_sea\n")
        for pid, terr in terr_from_pid.items():
            if terr == BaseTerrain.ocean:
                continue
            outf.write(f"{str(pid)}={CK3Terrain_from_BaseTerrain[terr].name}\n")  # Maybe should just replace this with a string dictionary?


def create_adjacencies(file_dir, straits, pid_from_cube, name_from_pid, closest_xy = None):
    """straits is a list of (cube, cube, pid) tuples (from, to, pid of the water region it passes thru).
    This function will create the adjacencies file (including some calculations about type and positioning)."""
    with open(os.path.join(file_dir, "map_data", "adjacencies.csv"), 'w', encoding="utf_8_sig") as outf:
        outf.write("From;To;Type;Through;start_x;start_y;stop_x;stop_y;Comment\n")
        for strait in straits:
            fr, to = strait[0], strait[1]
            buffer = [pid_from_cube[fr], pid_from_cube[to], strait[2]]
            if fr.sub(to).mag() == 1:
                buffer.insert(2,"river_large")
            else:
                buffer.insert(2,"sea")
            if closest_xy is None:
                buffer.extend([-1] * 4)
            else:
                buffer.extend(closest_xy(fr,to))
                buffer.extend(closest_xy(to, fr))
            buffer.append(name_from_pid[pid_from_cube[fr]] + "-" + name_from_pid[pid_from_cube[to]])
            outf.write(";".join([str(x) for x in buffer])+"\n")
        outf.write("-1;-1;;-1;-1;-1;-1;-1;\n")


def create_climate(file_dir):
    """Creates the climate file."""
    # TODO: Actually determine climate from location / terrain / etc.
    os.makedirs(os.path.join(file_dir, "map_data"), exist_ok=True)
    with open(os.path.join(file_dir, "map_data", "climate.txt"),'w', encoding="utf_8_sig") as outf:
        outf.write("mild_winter = {\n}\nnormal_winter = {\n}\nsevere_winter = {\n}\n")

def create_coa(file_dir, base_dir, custom_dir, title_list):
    """Populate common/coat_of_arms/coat_of_arms/01 and 90 with all the titles in title_list, drawing first from custom_dir and then from base_dir."""
    os.makedirs(os.path.join(file_dir, "common", "coat_of_arms", "coat_of_arms"), exist_ok=True)
    with open(os.path.join(file_dir, "common", "coat_of_arms", "coat_of_arms","01_landed_titles.txt"),'w', encoding='utf_8_sig') as outf:
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


def create_geographical_regions(file_dir, regions, sea_region, all_material_types = None, no_material_types=None, all_animal_types=None, no_animal_types=None):
    """Create the geographical_regions/geographical_region.txt file.
    regions is a list of RegionTrees.
    sea_regions is a dictionary, of title: province_list or title: title_list
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
    with open(os.path.join(file_dir, "map_data", "geographical_regions", "geographical_region.txt"),'w', encoding='utf_8_sig') as outf:
        all_regions = []
        for region in regions:
            region_title = "world_" + region.title.split("_")[1]
            all_regions.append(region_title)
            outf.write(region_title + " = {\n\tduchies= {\n\t\t")
            outf.write(" ".join([x for x in region.all_ck3_titles() if x[0] == 'd']))
            outf.write("\n\t}\n}\n")
        all_regions = " ".join(all_regions)
        for sregion, parts in sea_region.items():
            if isinstance(parts[0], int):
                outf.write(sregion + " = {\n\tprovinces = {\n\t\t" + " ".join([str(part) for part in parts]) + "\n\t}\n}\n")
            else:
                outf.write(sregion + " = {\n\tregions = {\n" + "\n".join(["\t\t" + part for part in parts]) + "\n\t}\n}\n")
        outf.write("\n")
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
    with open(os.path.join(file_dir, "map_data", "island_region.txt"),'w', encoding='utf_8_sig') as outf:
        # TODO: figuring out islands will depend on chunking the land elsewhere. For this basic one, we're fine.
        outf.write("\n")


def create_landed_titles(file_dir, pid_from_title, regions, special_titles=None):
    """Make common/landed_titles."""
    os.makedirs(os.path.join(file_dir, "common", "landed_titles"), exist_ok=True)
    with open(os.path.join(file_dir, "common", "landed_titles","00_landed_titles.txt"), 'w', encoding='utf_8_sig') as outf:
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


def date_parser(date):
    if date:
        return date.replace('M',str(random.randint(1,12))).replace('D',str(random.randint(1,28))).replace('Y',str(random.randint(0,9)))
    else:
        return None


def character(cid, name, religion, culture, bd, female=False, dynasty=None, dd=None, father=None, mother=None,
              spouse_date = None, spouse_id = None, trait_list=[], stats_dict={}):
    """Return the history/character entry for this character."""
    bd = date_parser(bd)
    dd = date_parser(dd)
    spouse_date = date_parser(spouse_date)  # This one is a little weird because it should be shared between spouses.
    buf = "{} = {{\n\tname=\"{}\"\n".format(cid, name)
    if female:
        buf += "\tfemale = yes\n"
    if dynasty:
        buf += "\tdynasty={}\n".format(dynasty)
    buf += "\treligion=\"{}\"\n\tculture=\"{}\"\n".format(religion, culture)
    for stat, val in stats_dict.items():
        buf += "\t{}={}\n".format(stat, val)
    for trait in trait_list:
        buf += "\ttrait=\"{}\"\n".format(trait)
    if father:
        buf += "\tfather={}\n".format(father)
    if mother:
        buf += "\tmother={}\n".format(mother)
    buf += "\t{} = {{\n\t\tbirth=\"{}\"\n\t}}\n".format(bd, bd)
    if spouse_date and spouse_id:
        buf += "\t{} = {{\n\t\tadd_spouse = {}\n\t}}\n".format(spouse_date, spouse_id)
    if dd:
        buf += "\t{} = {{\n\t\tdeath=\"{}\"\n\t}}\n".format(dd, dd)
    buf += '}\n'
    return buf


def title_history(name, events, title_data, coffset):
    """Return the history for the title."""
    buf = f"{name} = {{\n"
    vacant = True
    for k, v in events.items():
        if "." in k:
            event_date = date_parser(k)
            if isinstance(v, int):
                cid = v + coffset
                buf += f"\t{event_date} = {{\n\t\tholder = {cid}\n\t}}\n"
                vacant = False
            elif "_" in v:
                other_title = title_data[v]
                buf += f"\t{event_date} = {{\n\t\tliege = {other_title}\n\t}}\n"
        elif k == "development_level":
            buf += f"\t1000.1.1 = {{\tchange_development_level = {str(v)} }}\n"
        else:
            print(f"Unknown event: {k} {v}")
    if vacant:
        buf += "\t900.1.1 = {\n\t}\n"
    buf += "}\n"
    return buf


def culture_history(name, innovations, date="900.1.1"):
    """Return the history for the culture."""
    buf = f"#{name}\n\n{date} = {{\n"
    innos = [x for x in innovations if x.startswith("innovation")]
    eras = [x for x in innovations if not(x.startswith("innovation"))]
    buf += "\n".join(f"\tdiscover_innovation = {i}" for i in innos) + "\n"
    buf += "\n".join(f"\tjoin_era = {i}" for i in eras)
    buf += "\n}\n"
    return buf


def create_history(file_dir, base_dir, config, region_trees, cultures, pid_from_title):
    """Create the history files.
    This covers cultures, characters, provinces, and titles (as well as a few misc files).
    """
    os.makedirs(os.path.join(file_dir, "common", "bookmarks", "bookmarks"), exist_ok=True)
    os.makedirs(os.path.join(file_dir, "common", "bookmarks", "groups"), exist_ok=True)
    os.makedirs(os.path.join(file_dir, "common", "bookmark_portraits"), exist_ok=True)
    os.makedirs(os.path.join(file_dir, "common", "dynasties"), exist_ok=True)
    os.makedirs(os.path.join(file_dir, "common", "dynasty_houses"), exist_ok=True)
    os.makedirs(os.path.join(file_dir, "history", "characters"), exist_ok=True)
    os.makedirs(os.path.join(file_dir, "history", "cultures"), exist_ok=True)
    os.makedirs(os.path.join(file_dir, "history", "provinces"), exist_ok=True)
    os.makedirs(os.path.join(file_dir, "history", "titles"), exist_ok=True)
    os.makedirs(os.path.join(file_dir, "history", "wars"), exist_ok=True)
    with open(os.path.join(file_dir, "history","wars","00_wars.txt"), 'w', encoding="utf_8_sig") as outf:
        outf.write("\n")
    os.makedirs(os.path.join(file_dir, "history", "province_mapping"), exist_ok=True)
    with open(os.path.join(file_dir, "history","province_mapping","00_world.txt"), 'w', encoding="utf_8_sig") as outf:
        outf.write("\n")

    # For each culture and religion, pull up some basic data that we'll use.
    # CULTURES
    # Pull out the basegame namelists.
    # TODO: Add support for custom cultures?
    name_list_from_cul = {}
    dyn_names_from_cul = {}
    male_names_from_cul = {}
    female_names_from_cul = {}
    culture_dir = os.path.join(base_dir, "common", "culture", "cultures")
    for filename in os.listdir(culture_dir):
        if filename.startswith("_"):
            continue
        with open(os.path.join(culture_dir,filename), 'r', encoding='utf_8_sig') as inf:
            keeping = False
            for line in inf.readlines():
                if line[0] != "\t" and "=" in line and "{" in line:
                    cul_name = line.split("=")[0].encode('ascii', 'ignore').strip().decode()  # There's a weird character at the start of some of the files, which this gets rid of. Probably a better way to do it.
                    if cul_name in cultures:
                        keeping = True
                elif keeping and "name_list" in line:
                    name_list_from_cul[cul_name] = line.split("=")[1].strip().split(" ")[0]
                    keeping = False
    name_dir = os.path.join(base_dir, "common", "culture", "name_lists")
    for filename in os.listdir(name_dir):
        if filename.startswith("_"):
            continue
        with open(os.path.join(name_dir,filename), 'r', encoding='utf_8_sig') as inf:
            brackets = 0
            list_name = ""
            keeping = False
            dyn_names = []
            adding_dyn = False
            male_names = []
            adding_male = False
            female_names = []
            adding_female = False
            for line in inf.readlines():
                brackets += line.count("{")
                if brackets == 1 and "=" in line and "{" in line:
                    list_name = line.split("=")[0].encode('ascii', 'ignore').strip().decode()
                    if list_name in name_list_from_cul.values():
                        keeping = True
                    continue
                if keeping:
                    brackets -= line.count("}")
                    if brackets == 0:
                        keeping = False
                        adding_dyn = False
                        adding_male = False
                        adding_female = False
                        for cul in [cul for cul, name_list in name_list_from_cul.items() if name_list == list_name]:
                            dyn_names_from_cul[cul] = dyn_names  # This might allow for reuse of dynasty names between regions with the same culture. Probably fine?
                            male_names_from_cul[cul] = male_names
                            female_names_from_cul[cul] = female_names
                    elif line.startswith("\tdynasty_names"):
                        adding_dyn = True
                    elif line.startswith("\tmale_names"):
                        adding_male = True
                    elif line.startswith("\tfemale_names"):
                        adding_female = True
                    elif brackets == 1:
                        adding_dyn = False
                        adding_male = False
                        adding_female = False
                    elif adding_dyn and "\"" in line:
                        dyn_names.append(line.strip())
                    elif adding_male:
                        male_names.extend(line.strip().split(" "))
                    elif adding_female:
                        female_names.extend(line.strip().split(" "))
                else:
                    brackets -= line.count("}")

    # Pull out the basegame innovations.
    inno_dir = os.path.join(base_dir, "common", "culture", "innovations") 
    inno_list_from_era = {}
    for filename in os.listdir(inno_dir):
        if filename.startswith("_"):
            continue
        era_name = "_".join(filename.split("_")[1:-1])
        if era_name not in config["GUARANTEED_INNOS"] and era_name not in config["RANDOM_INNOS"]:
            continue  # Let's not bother to process files that we're not going to use.
        inno_list_from_era[era_name] = []
        with open(os.path.join(inno_dir,filename), 'r') as inf:
            name = ""
            for line in inf.readlines():
                if "=" in line and "{" in line:
                    name = line.split("=")[0].strip()
                if "=" in line and "group" in line and "regional" not in line and len(name) > 0:
                    inno_list_from_era[era_name].append(name)
                    name = ""
    base_innos = []
    for inno_name in config["GUARANTEED_INNOS"]:
        if inno_name in inno_list_from_era:
            base_innos.extend(inno_list_from_era[inno_name])
        else:
            base_innos.append(inno_name)  # TODO: This is where we should check to make sure the name is still legit
    # RANDOM_INNOS is a dictionary, so that we can get both the era name and the number to roll.
    # But it's not obvious we'll ever want to sample from multiple eras. (Maybe not everyone has all of tribal? idk)
    # Anyway, we're going to try to make opts by era as well, and then sample by era per culture.
    random_opts = {}
    for era_name in config["RANDOM_INNOS"]:
        assert era_name in inno_list_from_era, era_name
        random_opts[era_name] = [inno for inno in inno_list_from_era[era_name] if inno not in config["GUARANTEED_INNOS"] and inno not in config["BANNED_INNOS"]]
    # Write out history/culture (mostly innovations)
    os.makedirs(os.path.join(file_dir, "history", "cultures"), exist_ok=True)
    for culture in cultures:  # This might be too few; I'm a little worried that we will somehow be missing a culture that will show up thru events or w/e. It's probably fine?
        with open(os.path.join(file_dir, "history", "cultures", culture+".txt"), 'w', encoding='utf_8_sig') as outf:
            this_innos = []
            this_innos.extend(base_innos)
            for era_name, num in config["RANDOM_INNOS"].items():
                this_innos.extend(random.sample(random_opts[era_name],k=num))
            outf.write(culture_history(culture, this_innos))
    # CHARACTERS, PROVINCES, TITLES
    # Characters are saved in files that correspond to their original title instead of their culture
    # Because we're building the whole tree at once, we'll just process all three outputs at once.
    cul_from_title = {}
    rel_from_title = {}
    for region_tree in region_trees:
        culrelmap = region_tree.culrelmap()
        for k, (cul, rel) in culrelmap.items():
            cul_from_title[k] = cul
            rel_from_title[k] = rel

    coffset = 1000
    doffset = 100
    dynasty_buffer = ""
    player_buffer = ""
    bookmark_buffer = ""
    bookmark_pictures = []
    # bookmark_group_buffer = ""  # This one is only used if you have multiple start dates; the continents are bookmarks and kingdoms are characters inside a single bookmark.
    for cont_ind, cont_list in enumerate(config["CONTINENT_LISTS"]):
        bookmark_pictures.append(["bm_1000_" + region_trees[cont_ind].title])
        bookmark_buffer += "bm_1000_" + region_trees[cont_ind].title + " {\n\tstart_date=1000.1.1\n\tis_playable = yes\n\tgroup = bm_group_1000\n\n\tweight = {\n\t\tvalue = 0\n\t}\n\n"
        for region in cont_list:
            rtype, region = region.split("-")
            with open(os.path.join("data", rtype + "_template.yml"),'r') as inf:
                template = yaml.load(inf, yaml.Loader)
            # Somehow grab the appropriate region_tree
            region_tree_search = [y for y in [x.find_by_title(region) for x in region_trees] if y is not None]  # This feels super dumb
            if len(region_tree_search) == 0:  # This is a special title.
                with open(os.path.join(file_dir, "history", "titles", region+".txt"),'w', encoding='utf_8_sig') as outf:
                    outf.write(title_history(region, {}, {}, 0))
                continue
            region_tree = region_tree_search[0]
            titles = region_tree.all_ck3_titles()
            culture = region_tree.culture  # This currently doesn't allow for different culture or religions for subregions, but we don't use that yet, so it's fine.
            religion = region_tree.religion
            with open(os.path.join(file_dir, "history", "characters", region+".txt"), 'w', encoding='utf_8_sig') as outf:
                for char in template["chars"].values():  # The key for each character is just for template legibility
                    others = {k: v + coffset if k in ['father', 'mother', 'spouse_id'] else v for k, v in char.items() if k not in ["cid", "dynasty"]}
                    cid = char["cid"] + coffset
                    dynasty = char["dynasty"] + doffset if "dynasty" in char else None
                    try:
                        name = random.choice(female_names_from_cul[culture] if "female" in others else male_names_from_cul[culture])
                    except:
                        name = "ERROR"
                    outf.write(character(cid=cid, name=name, religion=religion, culture=culture, **others, dynasty=dynasty))
                for dyn, did in template["dynasties"].items():  # Leaving dyn b/c we might want to importance-sample somehow, or pick a location name
                    random.shuffle(dyn_names_from_cul[culture])
                    dyn_name = dyn_names_from_cul[culture].pop()
                    prefix = ""
                    if "\"" in dyn_name:
                        dns = dyn_name.split("\"")
                        if len(dns) >= 4:
                            prefix = dns[1]
                            dyn_name = dns[3]
                    if did == 0:
                        player_buffer += f"{did+doffset} = {{\n"
                        if len(prefix) > 0:
                            player_buffer += f"\tprefix={prefix}\n"
                        player_buffer += f"\tname={dyn_name}\n\tculture=\"{culture}\"\n}}\n"
                        bookmark_name = "bookmark_" + titles[0]
                        bookmark_buffer += f"\tcharacter = {{\n\t\tname=\"{bookmark_name}\"\n\t\tdynasty={did+doffset}\n\t\ttype = male\n\t\ttitle = {titles[1]}\n\t\tgovernment = feudal_government\n\t\tculture = {culture}\n\t\treligion = {religion}\n\t\thistory_id = {coffset}\n\t\tposition = {{ {doffset * 5} 400 }}\n\t\tanimation = personality_bold\n\t}}\n\n"
                        src_path = os.path.join("data", "common", "bookmark_portraits", bookmark_name + ".txt")
                        if not os.path.exists(src_path):
                            src_path = os.path.join(base_dir, "common", "bookmark_portraits", "bookmark_adventurers_jarl_haesteinn.txt")
                        with open(src_path, encoding="utf_8_sig") as book_inf:
                            with open(os.path.join(file_dir, "common", "bookmark_portraits", bookmark_name + ".txt"), 'w', encoding="utf_8_sig") as book_outf:
                                for line in book_inf.readlines():
                                    if "bookmark_adventurers" in line:
                                        book_outf.write(bookmark_name + "={\n")
                                    else:
                                        book_outf.write(line)
                    else:
                        dynasty_buffer += f"{did+doffset} = {{\n"
                        if len(prefix) > 0:
                            dynasty_buffer += f"\tprefix={prefix}\n"
                        dynasty_buffer += f"\tname={dyn_name}\n\tculture=\"{culture}\"\n}}\n"
            title_map = {}
            c_capital = False
            num = {"b":0, "c":0, "d":0, "k":0, "e":0}
            prov_buf = ""
            for title in titles:
                title_map[f"{title[0]}_{num[title[0]]}"] = title
                if title[0] == "c":
                    c_capital = True
                if title[0] == "b":
                    pid = pid_from_title[title]
                    prov_buf += f"{pid} = {{\n"
                    if c_capital:
                        prov_buf += f"\tculture = {culture}\n\treligion = {religion}\n"
                        c_capital = False
                    prov_buf +="\tholding = " + template["baronies"].get(num["b"], "none") + "\n}\n"
                num[title[0]] += 1
            if region[0] != "e":  # We don't need to write out province history for empires.
                with open(os.path.join(file_dir, "history", "provinces", region+".txt"),'w', encoding='utf_8_sig') as outf:
                    outf.write(prov_buf)
            title_buf = ""
            for title, events in template["titles"].items():  # We have to do this a second time so that we can make the title map first.
                if title[0] != "b":
                    title_buf += title_history(title_map[title], events, title_map, coffset)
            with open(os.path.join(file_dir, "history", "titles", region+".txt"),'w', encoding='utf_8_sig') as outf:
                outf.write(title_buf)
            doffset += len(template["dynasties"]) + 1
            if len(template["chars"]) > 0:
                coffset += max([char["cid"] for char in template["chars"].values()]) + 1
    with open(os.path.join(file_dir, "common", "bookmarks", "bookmarks", "00_bookmarks.txt"),'w', encoding='utf_8_sig') as outf:
        outf.write(bookmark_buffer)
    with open(os.path.join(file_dir, "common", "bookmarks", "groups", "00_bookmark_groups.txt"),'w', encoding='utf_8_sig') as outf:
        outf.write("bm_group_1000 = {\n\tdefault_start_date = 1000.1.1\n}\n")
    with open(os.path.join(file_dir, "common", "dynasties", "00_dynasties.txt"),'w', encoding='utf_8_sig') as outf:
        outf.write(dynasty_buffer)
    with open(os.path.join(file_dir, "common", "dynasties", "01_players.txt"),'w', encoding='utf_8_sig') as outf:
        outf.write(player_buffer)
    with open(os.path.join(file_dir, "common", "dynasty_houses", "00_dynasty_houses.txt"),'w', encoding='utf_8_sig') as outf:
        outf.write("\n")
    return 


def create_default_map(file_dir, impassable, sea_min, sea_max):
    """Writes out default.map."""
    os.makedirs(os.path.join(file_dir, "map_data"), exist_ok=True)
    with open(os.path.join(file_dir, "map_data", "default.map"), 'w', encoding='utf_8_sig') as outf:
        outf.write("""definitions = "definition.csv"\nprovinces = "provinces.png"\n#positions = "positions.txt"\nrivers = "rivers.png"\n#terrain_definition = "terrain.txt"\ntopology = "heightmap.heightmap"\n#tree_definition = "trees.bmp"\ncontinent = "continent.txt"\nadjacencies = "adjacencies.csv"\n#climate = "climate.txt"\nisland_region = "island_region.txt"\nseasons = "seasons.txt"\n\n""")
        outf.write("sea_zones = RANGE { "+str(sea_min)+" "+str(sea_max)+" }\n\n")
        for impid in impassable:
            outf.write("impassable_mountains = LIST { "+str(impid)+" }\n")
        outf.write("\n")


def create_religion(file_dir, base_dir, religions, holy_sites, custom_dir=None):
    """Create common/religion/holy_sites and common/religion/religions."""
    os.makedirs(os.path.join(file_dir, "common", "religion", "religions"), exist_ok=True)
    os.makedirs(os.path.join(file_dir, "common", "religion", "holy_sites"), exist_ok=True)
    # For each of the religions, we're going to make it so they have all the holy sites.
    religion_locs = [base_dir]
    if custom_dir is not None and os.path.exists(os.path.join(custom_dir, "common","religion","religions")):
        religion_locs.append(custom_dir)  # custom_dir goes second so it will overwrite base files.
    for dir in religion_locs:
        for religion_filename in os.listdir(os.path.join(dir, "common", "religion", "religions")):
            with open(os.path.join(dir, "common", "religion", "religions", religion_filename), 'r', encoding='utf_8_sig') as inf:
                with open(os.path.join(file_dir, "common", "religion", "religions", religion_filename), 'w', encoding='utf_8_sig') as outf:
                    holy_site_section = True
                    for line in inf.readlines():
                        if "holy_site" in line:
                            if holy_site_section:
                                holy_site_section = False
                                for holy_site in holy_sites:
                                    outf.write(f"\t\t\tholy_site = {holy_site}\n")
                        else:
                            if "}" in line: # We have finished that section and will maybe need to dump all the holy sites again.
                                holy_site_section = True
                            outf.write(line)
    with open(os.path.join(file_dir, "common", "religion", "holy_sites", "00_holy_sites.txt"), 'w', encoding='utf_8_sig') as outf:
        holy_site_locs = [os.path.join(base_dir, "common", "religion", "holy_sites", "00_holy_sites.txt")]
        if custom_dir is not None and os.path.exists(os.path.join(custom_dir, "common", "religion", "holy_sites")):
            holy_site_locs.insert(0, os.path.join(custom_dir, "common", "religion", "holy_sites", "00_holy_sites.txt"))
        for inf_loc in holy_site_locs:
            with open(inf_loc, 'r', encoding='utf_8_sig') as inf:
                brackets = 0
                copying = False
                for line in inf.readlines():
                    if brackets == 0 and "{" in line:
                        name = line.split("=")[0].strip()
                        if name in holy_sites:
                            copying = True
                            holy_sites.remove(name)  # This is so if it's taken from the custom one, we don't also take it from the base one.
                    brackets += line.count("{")
                    if copying:
                        outf.write(line)
                    brackets -= line.count("}")
                    if brackets == 0 and "}" in line and copying:
                        outf.write("\n")
                        copying = False
        for holy_site in holy_sites:
            print("holy site " + holy_site + " not found!")  # These are the ones that didn't get found.


def create_dot_mod(file_dir, mod_name, mod_disp_name):
    """Creates the basic mod structure and metadata file."""
    shared = "version = \"0.0.1\"\n"
    shared += "tags = {\n\t\"Total Conversion\"\n}\n"
    shared += "name = \"{}\"\n".format(mod_disp_name)
    shared += "supported_version = \"1.12.2\"\n"
    outer = "path = \"mod/{}\"\n".format(mod_name)
    
    replace_paths = [
        "common/bookmark_portraits", "common/culture/innovations", "common/dynasties", "common/dynasty_houses",
        "history/characters", "history/cultures", "history/province_mappings", "history/provinces", "history/struggles", "history/titles", "history/wars"
        ]
    shared += "replace_path = \"" + "\"\nreplace_path = \"".join(replace_paths)+"\""
    os.makedirs(os.path.join(file_dir, mod_name), exist_ok=True)
    with open(os.path.join(file_dir,"{}.mod".format(mod_name)),'w', encoding="utf_8_sig") as f:
        f.write(shared + outer)
    with open(os.path.join(file_dir, mod_name, "descriptor.mod".format(mod_name)),'w', encoding="utf_8_sig") as f:
        f.write(shared)
    return os.path.join(file_dir, mod_name)


def create_mod(file_dir, config, pid_from_cube, terr_from_cube, terr_from_pid, rgb_from_pid, height_from_vertex, pid_from_title, name_from_pid, region_trees, cultures, religions, impassable, river_flow_from_edge, river_sources, river_merges, river_max_flow, straits, sea_region):
    """Creates the CK3 mod files in file_dir, given the basic data."""
    # Make the basic filestructure that other things go in.
    file_dir = create_dot_mod(file_dir=file_dir, mod_name=config.get("MOD_NAME", "testmod"), mod_disp_name=config.get("MOD_DISPLAY_NAME", "testing_worldgen"))
    create_blanks(file_dir, [["map", "lakes", "00_lakes.txt"]] + [["gfx", "map", "map_object_data", x + ".txt"] for x in ["bridges", "cliffs_coastline", "cliffs_rock", "coast_foam", "env_effects", "lakes", "special"]])
    # make common
    all_titles = []
    holy_sites = []
    for region_tree in region_trees:
        all_titles.extend(region_tree.all_ck3_titles())
        holy_sites.extend(region_tree.all_holy_sites())
    print(f"There are {len(all_titles)} titles.")
    create_coa(file_dir, base_dir=os.path.join(config["BASE_CK3_DIR"], "common", "coat_of_arms", "coat_of_arms"), custom_dir=config.get("COA_DIR", None), title_list=all_titles)
    create_landed_titles(file_dir, pid_from_title, region_trees)  # TODO: add special_titles
    create_terrain_file(file_dir=file_dir, terr_from_pid=terr_from_pid)
    # make history
    create_history(file_dir=file_dir, base_dir=config["BASE_CK3_DIR"], config=config, region_trees=region_trees, cultures=cultures, pid_from_title=pid_from_title)
    # make religions
    create_religion(file_dir, config["BASE_CK3_DIR"], religions, holy_sites, custom_dir=config.get("RELIGION_DIR", None))
    # Determine major rivers and impassable mountain boundaries (done here b/c it affects provinces also)
    # Make map
    ck3map = CK3Map(file_dir, max_x=config["max_x"], max_y=config["max_y"], n_x=config["n_x"], n_y=config["n_y"])
    title_from_pid = {pid: title for title, pid in pid_from_title.items()}
    ck3map.create_provinces(rgb_from_pid, pid_from_cube, ".png", name_from_pid=title_from_pid)
    ck3map.create_heightmap(height_from_vertex=height_from_vertex, file_ext=".png")
    ck3map.create_rivers(height_from_vertex, river_flow_from_edge, river_sources, river_merges, river_max_flow, base_loc=config["BASE_CK3_DIR"], file_ext=".png")
    ck3map.create_flowmap(file_dir=file_dir, terr_from_cube=terr_from_cube)
    ck3map.create_positions(name_from_pid, pid_from_cube, file_dir=file_dir)
    ck3map.create_terrain_masks(file_dir=file_dir, base_dir=config["BASE_CK3_DIR"], terr_from_cube=terr_from_cube)
    ck3map.surround_mask(file_dir=file_dir)  # TODO: Figure out where's far enough away to mask
    ck3map.create_bookmarks(file_dir=file_dir, terr_from_cube=terr_from_cube, bookmark_groups=[])
    ck3map.update_defines(base_dir=config["BASE_CK3_DIR"])
    copy_base_files(file_dir, base_dir=config["BASE_CK3_DIR"], file_paths=[["gfx", "map", "map_object_data", x] for x in ["effect_layers.txt", "game_object_layers.txt", "map_table_ce1.txt", "map_table_western.txt",]])
    create_adjacencies(file_dir=file_dir, straits=straits, pid_from_cube=pid_from_cube, name_from_pid=name_from_pid, closest_xy=lambda fr, to: closest_xy(fr, to, ck3map.box_height, ck3map.box_width))
    create_geographical_regions(file_dir, region_trees, sea_region)
    if len(impassable) > 0:
        sea_min = max(impassable) + 1
    else:
        sea_min = max(terr_from_pid.values()) + 1  # This is because we never added the sea pids to it.
    sea_max = max(pid_from_cube.values())
    create_default_map(file_dir, impassable, sea_min, sea_max)
    create_climate(file_dir=file_dir)
    strip_base_files(file_dir, config["BASE_CK3_DIR"], subpaths=[
        "common\\decisions",
        "common\\travel",
        "events"
    ],
    to_remove=["province:", "title:", "character:"],
    to_keep = [],
    subsection=["modifier = {"],
    )
