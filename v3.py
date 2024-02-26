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
        self.box_width, self.box_height = box_from_max(self.max_x, self.max_y, self.n_x, self.n_y)

    def create_provinces(self, rgb_from_cube):
        """Creates provinces.png and definition.csv"""
        img = create_hex_map(rgb_from_ijk={k.tuple(): v for k,v in rgb_from_cube.items()}, max_x=self.max_x, max_y=self.max_y, mode='RGB', default="black", n_x=self.n_x, n_y=self.n_y)
        img.save(os.path.join(self.file_dir, "map_data", "provinces.png"))

    def create_heightmap(self, height_from_vertex):
        """Uses height_from_cube to generate a simple heightmap."""
        img = create_tri_map(height_from_vertex=height_from_vertex, max_x=self.max_x * 2, max_y=self.max_y * 2, n_x=self.n_x, n_y=self.n_y)
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

    def create_locators(self, file_dir, locs_from_rid, pid_from_cube):
        os.makedirs(os.path.join(file_dir,"gfx","map", "map_object_data"), exist_ok=True)
        for loc in VALID_LOCS:
            with open(os.path.join(file_dir, "gfx", "map", "map_object_data", f"generated_map_object_locators_{loc}.txt"), 'w', encoding='utf_8_sig') as outf:
                clamp = "yes" if loc == "port" else "no"
                outf.write("game_object_locator={\n\tname=\""+loc+"\"\n\tclamp_to_water_level="+clamp+"\n\trender_under_water=no\n\tgenerated_content=no\n\tlayer=\"locators\"\n\tinstances={\n")
                for rid in sorted(locs_from_rid.keys()):
                    if loc in locs_from_rid[rid]:
                        cubes = [cube for cube, pid in pid_from_cube.items() if pid == locs_from_rid[rid][loc]]
                        if len(cubes) == 0:
                            raise ValueError(f"Missing {loc} for {rid} with pid {locs_from_rid[rid][loc]}")
                        # TODO: choose more intelligently / have them offset?
                        x,y = xy_from_cube(random.sample(cubes, k=1)[0], self.box_width, self.box_height)
                        x += 2*self.box_width
                        y += self.box_height
                        outf.write(f"\t\t{{\n\t\t\tid={rid}\n\t\t\tposition={{ {x} 0.0 {y} }}\n\t\t\trotation={{ 0 0 0 1 }}\n\t\t\tscale={{ 1 1 1 }}\n\t\t}}\n")
                outf.write("\t}\n}\n")

    def create_terrain_masks(self, base_dir, terr_from_cube):
        """Creates all the terrain masks; just fills each cube.
        terr_from_cube is a map from cube to BaseTerrain."""
        os.makedirs(os.path.join(self.file_dir, "gfx", "map", "terrain"), exist_ok=True)
        for mask in os.listdir(os.path.join(base_dir, "gfx", "map", "terrain")):
            if not mask.startswith("mask"):
                continue
            mask_name = mask[5:-4]  # begins with mask_ and ends with .png
            if mask_name not in USED_MASKS.values():
                create_hex_map(rgb_from_ijk={}, max_x=self.max_x, max_y=self.max_y, n_x=self.n_x, n_y=self.n_y, mode='L', default="black").save(os.path.join(self.file_dir, "gfx", "map", "terrain", mask))
            else:
                terrain = [k for k,v in USED_MASKS.items() if v == mask_name][0]
                rgb_from_ijk = {k.tuple(): 128 for k,v in terr_from_cube.items() if v == terrain}
                create_hex_map(rgb_from_ijk=rgb_from_ijk, max_x=self.max_x, max_y=self.max_y, n_x=self.n_x, n_y=self.n_y, mode='L', default="black").save(os.path.join(self.file_dir, "gfx", "map", "terrain", mask))
        os.makedirs(os.path.join(self.file_dir, "gfx", "map", "masks"), exist_ok=True)
        for mask in os.listdir(os.path.join(base_dir, "gfx", "map", "masks")):
            if not mask.startswith("mask"):
                continue
            #TODO: Assign farmland/forestry/mining to provinces
            create_hex_map(rgb_from_ijk={}, max_x=self.max_x, max_y=self.max_y, n_x=self.n_x, n_y=self.n_y, mode='L', default="black").save(os.path.join(self.file_dir, "gfx", "map", "masks", mask))
        os.makedirs(os.path.join(self.file_dir, "gfx", "map", "dynamic_masks"), exist_ok=True)
        # TODO: I think this should be land + one sea depth
        create_hex_map(rgb_from_ijk={}, max_x=self.max_x, max_y=self.max_y, n_x=self.n_x, n_y=self.n_y, mode='L', default="black").save(os.path.join(self.file_dir, "gfx", "map", "dynamic_masks", "exclusion_mask.dds"))
        os.makedirs(os.path.join(self.file_dir, "gfx", "map", "textures"), exist_ok=True)
        # Land mask is white for land and black for ocean
        create_hex_map(rgb_from_ijk={k.tuple(): 0 if v == BaseTerrain.ocean else 255 for k,v in terr_from_cube.items()}, max_x=self.max_x, max_y=self.max_y, n_x=self.n_x, n_y=self.n_y, mode='L', default="black").save(os.path.join(self.file_dir, "gfx", "map", "textures", "land_mask.dds"))
        create_hex_map(rgb_from_ijk={}, max_x=self.max_x//8, max_y=self.max_y//8, n_x=self.n_x, n_y=self.n_y, mode='L', default="black").save(os.path.join(self.file_dir, "gfx", "map", "textures", "windmap_tree.dds"))
        create_hex_map(rgb_from_ijk={}, max_x=self.max_x, max_y=self.max_y, n_x=self.n_x, n_y=self.n_y, mode='RGB', default="white").save(os.path.join(self.file_dir, "gfx", "map", "textures", "colormap.dds"))
        create_hex_map(rgb_from_ijk={}, max_x=self.max_x, max_y=self.max_y, n_x=self.n_x, n_y=self.n_y, mode='RGB', default="white").save(os.path.join(self.file_dir, "gfx", "map", "textures", "flatmap.dds"))
        create_hex_map(rgb_from_ijk={}, max_x=self.max_x//8, max_y=self.max_y//8, n_x=self.n_x, n_y=self.n_y, mode='RGB', default="black").save(os.path.join(self.file_dir, "gfx", "map", "textures", "colormap_tree.dds"))
        os.makedirs(os.path.join(self.file_dir, "content_source", "map_objects", "masks"), exist_ok=True)
        for mask in os.listdir(os.path.join(base_dir, "content_source", "map_objects", "masks")):
            create_hex_map(rgb_from_ijk={}, max_x=self.max_x, max_y=self.max_y, n_x=self.n_x, n_y=self.n_y, mode='L', default="black").save(os.path.join(self.file_dir, "content_source", "map_objects", "masks", mask))
    
    def create_rivers(self, river_background, river_edges, river_vertices, base_loc):
        """Create rivers.png"""
        img = create_hex_map(rgb_from_ijk=river_background, rgb_from_edge=river_edges, rgb_from_vertex=river_vertices, max_x=self.max_x, max_y=self.max_y, mode='P', palette=get_palette(base_loc), default=254, n_x=self.n_x, n_y=self.n_y)
        img.save(os.path.join(self.file_dir, "map_data", "rivers.png"))

    def update_defines(self, base_dir):
        """Copies common/defines/00_defines.txt but replaces WORLD_EXTENTS_X and Z."""
        os.makedirs(os.path.join(self.file_dir, "common", "defines"), exist_ok=True)
        with open(os.path.join(base_dir, "common", "defines", "00_defines.txt"), 'r', encoding='utf_8_sig') as inf:
            with open(os.path.join(self.file_dir, "common", "defines", "00_defines.txt"), 'w', encoding='utf_8_sig') as outf:
                for line in inf.readlines():
                    if line.startswith("\tWORLD_EXTENTS_X"):
                        outf.write(line.split("=")[0] + f"= {self.max_x}\n")
                    elif line.startswith("\tWORLD_EXTENTS_Z"):
                        outf.write(line.split("=")[0] + f"= {self.max_y-1}\n")
                    else:
                        outf.write(line)
        # TODO: Confirm that I don't need to update 00_graphics.txt, mostly CAMERA_START.


def create_blanks(file_dir):
    """There are a lot of V3 files that we want to just blank out."""
    for file_path in [
        ["common", "buildings", "10_canals.txt"],
        ["gfx", "map", "city_data", "american_mining_oilrig.txt"],  # These should perhaps be fine if we use the vanilla regions / cultures
        ["gfx", "map", "city_data", "wild_west_farm.txt"],  # These should perhaps be fine if we use the vanilla regions / cultures
    ]:
        os.makedirs(os.path.join(file_dir,*file_path[:-1]), exist_ok=True)
        with open(os.path.join(file_dir, *file_path), 'w', encoding="utf_8_sig") as outf:
            outf.write("\n")


def create_terrain_file(file_dir, terr_from_pid, rgb_from_pid):
    """Writes out common/province_terrains."""
    # Masks were historically wrapped into create_heightmap, and should maybe be again.
    os.makedirs(os.path.join(file_dir, "map_data"), exist_ok=True)
    with open(os.path.join(file_dir, "map_data", "province_terrains.txt"), 'w') as outf:
        for pid, terr in sorted(terr_from_pid.items()):
            outf.write(f"{hex_rgb(*rgb_from_pid[pid])}=\"{V3Terrain_Name_from_BaseTerrain[terr]}\"\n")
    os.makedirs(os.path.join(file_dir, "common", "terrain_manipulators", "provinces"), exist_ok=True)
    with open(os.path.join(file_dir, "common", "terrain_manipulators", "provinces", "allowed_provinces.txt"), 'w') as outf:
        # TODO: remove cities from this list.
        all_provs = " ".join([str(pid) for pid, terr in terr_from_pid.items() if terr != BaseTerrain.ocean])
        for mask_type in ["farmland", "mining", "forestry"]:
            outf.write(f"mask_dynamic_{mask_type}={{\n\tchecksum=\"\"\n\tallowed_provinces={{ {all_provs} }}\n}}\n")


def create_dot_mod(file_dir, mod_name, mod_disp_name):
    """Creates the basic mod structure and metadata file."""
    file_dir = os.path.join(file_dir, mod_name)
    os.makedirs(os.path.join(file_dir,".metadata"), exist_ok=True)
    with open(os.path.join(file_dir, ".metadata", "metadata.json"),'w') as outf:
        outf.write("{\n\t\"name\" : \""+mod_disp_name+"\",\n\t\"id\" : \"\",\n\t\"version\" : \"0.0\",\n\t\"supported_game_version\" : \"1.5.13\",\n\t\"short_description\" : \"\",\n\t\"tags\" : [\n\t\t\"Total Conversion\"\n\t],\n\t\"relationships\" : [],\n\t\"game_custom_data\" : {\n\t\t\"multiplayer_synchronized\" : true,\n\t\t\"replace_paths\": [\n")
        outf.write(",\n".join("\t\t\t\"" + x + "\"" for x in [                
                    "common/canals",
                    "common/country_creation",
                    "common/country_definitions",
                    "common/country_formation",
                    "common/history/ai",
                    "common/history/buildings",
                    "common/history/characters",
                    "common/history/countries",
                    "common/history/diplomacy",
                    "common/history/diplomatic_plays",
                    "common/history/governments",
                    "common/history/interests",
                    "common/history/military_deployments",
                    "common/history/military_formations",
                    "common/history/pops",
                    "common/history/population",
                    "common/history/production_methods",
                    "common/history/trade_routes",
                    "common/journal_entries",
                    "common/strategic_regions",
                    "content_source/map_objects/masks",
                    "map_data/state_regions",
                ]))
        outf.write("\n\t\t]\n\t}\n}\n")
    return file_dir


HEX_LIST = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "A", "B", "C", "D", "E", "F"]
def hex_rgb(r, g, b):
    """Create a v3-style hex string from a r,g,b tuple. (Use *rgb to split the tuple.)"""
    return "x" + HEX_LIST[r // 16] + HEX_LIST[r % 16] + HEX_LIST[g // 16] + HEX_LIST[g % 16] + HEX_LIST[b // 16] + HEX_LIST[b % 16]


def create_states(file_dir, rid_from_pid, rgb_from_pid, name_from_rid, traits_from_rid, locs_from_rid, arable_from_rid, capped_from_rid, coast_from_rid, tag_from_pid, pop_from_rid, building_from_rid, culture_conv, religion_conv, homelands_from_rid={}, claims_from_rid={}):
    """Creates state_region files, as well as relevant history files."""
    os.makedirs(os.path.join(file_dir,"map_data","state_regions"), exist_ok=True)
    with open(os.path.join(file_dir,"map_data","state_regions", "00_state_regions.txt"), 'w', encoding='utf_8_sig') as outf:
        with open(os.path.join(file_dir,"map_data","state_regions", "99_seas.txt"), 'w', encoding='utf_8_sig') as soutf:
            for rid, rname in name_from_rid.items():
                if rname[0] == "i":  # We don't care about the impassable regions. Might need to fix this later.
                    continue
                buffer = f"{rname} = {{\n\tid = {rid}\n\tprovinces = {{ "
                if rname[0] == "s":  # sea regions
                    buffer += f"\" {hex_rgb(*rgb_from_pid[pid])} \" }}\n}}\n\n"
                    soutf.write(buffer)
                    continue
                buffer += " ".join(["\""+hex_rgb(*rgb_from_pid[pid])+"\"" for pid, rrid in rid_from_pid.items() if rid==rrid]) + "}\n"
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
    pids_from_rid = {}
    for pid, rid in rid_from_pid.items():
        if rid in pids_from_rid:
            pids_from_rid[rid].append(pid)
        else:
            pids_from_rid[rid] = [pid]
    os.makedirs(os.path.join(file_dir,"common","history", "states"), exist_ok=True)
    with open(os.path.join(file_dir, "common", "history", "states", "00_states.txt"), 'w', encoding='utf_8_sig') as outf:
        outf.write("STATES = {\n")
        for rid, rname in name_from_rid.items():
            if rname[0] == "i" or rname[0] == "s":  # We don't care about the impassable regions or seas.
                continue
            outf.write(f"\ts:{rname} = {{\n")
            tags = {}  # This seems awkward--maybe I should store this better elsewhere?
            for pid in pids_from_rid[rid]:
                tag = tag_from_pid[pid]
                if tag in tags:
                    tags[tag].append(pid)
                else:
                    tags[tag] = [pid]
            for tag, pids in tags.items():
                outf.write(f"\t\tcreate_state = {{\n\t\t\tcountry = c:{tag}\n\t\t\towned_provinces = {{ ")
                outf.write(" ".join([hex_rgb(*rgb_from_pid[pid]) for pid in pids]))
                outf.write("\t\t}\n")
            if rid in homelands_from_rid:
                outf.write("\n"+"\n".join(["\t\tadd_homeland = cu:" + culture_conv.get(culture, culture) for culture in homelands_from_rid[rid]]) + "\n")
            if rid in claims_from_rid:
                outf.write("\n"+"\n".join(["\t\tadd_homeland = c:" + tag for tag in claims_from_rid[rid]]) + "\n")
            outf.write("\t}\n")
    os.makedirs(os.path.join(file_dir,"common","history", "pops"), exist_ok=True)
    with open(os.path.join(file_dir, "common", "history", "pops", "00_world.txt"), 'w', encoding='utf_8_sig') as outf:
        outf.write("POPS = {\n")
        for rid, pop_from_tag in pop_from_rid.items():
            outf.write(f"\ts:{name_from_rid[rid]} = {{\n")
            for tag, pops in pop_from_tag.items():
                outf.write(f"\t\tregion_state:{tag} = {{\n")
                for (size, culture, religion) in pops:
                    buffer = ""
                    if culture is not None:
                        buffer += f"\t\t\t\tculture = {culture_conv.get(culture, culture)}\n"
                    if religion is not None:
                        buffer += f"\t\t\t\treligion = {religion_conv.get(religion, religion)}\n"
                    outf.write(f"\t\t\tcreate_pop = {{\n{buffer}\t\t\t\tsize = {size}\n\t\t\t}}\n")
                outf.write("\t\t}\n")
            outf.write("\t}\n")
        outf.write("}\n")
    os.makedirs(os.path.join(file_dir,"common","history", "buildings"), exist_ok=True)
    with open(os.path.join(file_dir, "common", "history", "buildings", "00_world.txt"), 'w', encoding='utf_8_sig') as outf:
        outf.write("BUILDINGS = {\n")
        for rid, building_from_tag in building_from_rid.items():
            outf.write(f"\ts:{name_from_rid[rid]} = {{\n")
            for tag, buildings in building_from_tag.items():
                outf.write(f"\t\tregion_state:{tag} = {{\n")
                for (btype, level, reserves, pms) in buildings:
                    outf.write(f"\t\t\tcreate_building = {{\n\t\t\t\tbuilding = \"{btype}\"\n\t\t\t\tlevel={level}\n\t\t\t\treserves={reserves}\n\t\t\t\tactivate_production_methods={{ " + " ".join(["\"" + pm + "\"" for pm in pms])  + " }\n\t\t\t}\n")
                outf.write("\t\t}\n")
            outf.write("\t}\n")
        outf.write("}\n")


def create_strat_regions(file_dir, srs_from_place, srs_from_farm, region_trees, rgb_from_pid, name_from_rid):
    """Create the strategic region files and a handful of other miscellaneous files."""
    os.makedirs(os.path.join(file_dir, "common", "strategic_regions"), exist_ok=True)
    for region_tree in region_trees:
        grouping_name = region_tree.title[2:]  # Strip off the e_ or w/e
        with open(os.path.join(file_dir, "common", "strategic_regions", grouping_name + "_strategic_regions.txt"), 'w', encoding='utf_8_sig') as outf:
            outf.write(f"# Strategic Regions in {grouping_name}\n\n")
            for rt in region_tree.children:
                if rt.capital_pid == -1:
                    continue
                region_name = "region_" + rt.title[2:]
                capital_prov = hex_rgb(*rgb_from_pid[rt.capital_pid])  # TODO: improve region_tree capitals
                map_color = " ".join([str(x) for x in list(rt.color)])
                states = " ".join(rt.some_ck3_titles("d_"))
                outf.write(f"{region_name} = {{\n\tcapital_province = {capital_prov}\n\tmap_color = {{ {map_color} }}\n\tstates = {{ {states} }}\n}}\n\n")
    with open(os.path.join(file_dir, "common", "strategic_regions", "water_strategic_regions.txt"), 'w', encoding='utf_8_sig') as outf:
        for rid, rname in name_from_rid.items():
            if rname[0] == "s":
                outf.write(f"region_{rid} = {{\n\tstates = {{ s_{rid} }}\n}}\n\n")
    os.makedirs(os.path.join(file_dir, "common", "scripted_triggers"), exist_ok=True)
    with open(os.path.join(file_dir,  "common", "scripted_triggers", "00_geography_triggers.txt"), 'w', encoding='utf_8_sig') as outf:
        americas_list = []
        for place, srs in srs_from_place.items():
            outf.write(f"state_is_in_{place} = {{\n")
            if len(srs) == 0:
                outf.write("\talways = no\n}\n\n")
            else:
                outf.write("\tOR = {\n"+"\n".join(["\t\tregion = sr:" + region for region in srs]) + "\n\t}\n}\n\n")
            if "america" in place:
                americas_list.append(f"state_is_in_{place}")
        if len(americas_list) > 0:
            outf.write("state_is_in_americas = {\n\tOR = {\n" + "".join([f"\t\t{am} = yes\n" for am in americas_list]) + "\t}\n}\n\n")
        for place in srs_from_place.keys():
            outf.write(f"country_is_in_{place} = {{\n\texists = capital\n\tcapital = {{\n\t\tstate_is_in_{place} = yes\n\t}}\n}}\n\n")
        for farm, srs in srs_from_farm.items():
            outf.write(f"is_{farm} = {{\n")
            if len(srs) == 0:
                outf.write("\talways = no\n}\n\n")
            else:
                outf.write("\tOR = {\n"+"\n".join(["\t\tregion = sr:" + region for region in srs]) + "\n\t}\n}\n\n")


TIER_FROM_PREFIX = {
    "e": "empire",
    "k": "kingdom",
    "d": "grand_principality",
    "c": "principality",
}

def create_countries(file_dir, base_dir, region_trees, tech_from_tag, tax_from_tag, laws_from_tag, wealth_from_tag, literacy_from_tag, name_from_rid, culture_conv, religion_conv,):
    """Creates common/country_definitions files, as well as relevant history files."""
    os.makedirs(os.path.join(file_dir,"common","country_definitions"), exist_ok=True)
    with open(os.path.join(os.path.join(file_dir, "common", "country_definitions", "00_countries.txt")), 'w', encoding='utf_8_sig') as outf:
        for region_tree in region_trees:
            for region in region_tree.all_region_trees():
                if region.tag is not None and region.capital_rid != -1:
                    r,g,b = region.color
                    capital = name_from_rid[region.capital_rid]
                    outf.write(region.tag + f" = {{\n\tcolor = {{ {r} {g} {b} }}\n\tcountry_type = recognized\n\ttier = {TIER_FROM_PREFIX[region.title[0]]}\n\tcultures = {{ {culture_conv.get(region.culture, region.culture)} }}\n\tcapital = {capital}\n}}\n\n")
    with open(os.path.join(os.path.join(base_dir, "common", "country_definitions", "99_dynamic.txt")), 'r', encoding='utf_8_sig') as inf:
        with open(os.path.join(os.path.join(file_dir, "common", "country_definitions", "99_dynamic.txt")), 'w', encoding='utf_8_sig') as outf:
            for line in inf.readlines():
                outf.write(line)
    os.makedirs(os.path.join(file_dir,"common","history","countries"), exist_ok=True)
    for tag, tech in tech_from_tag.items():
        with open(os.path.join(file_dir,"common","history","countries", f"{tag} - {tag}.txt"),'w', encoding='utf_8_sig') as outf:  # Not actually obvious these need to be different files instead of one mongo file
            outf.write(f"COUNTRIES = {{\n\tc:{tag} = {{\n\teffect_starting_technology_tier_{str(tech)}_tech = yes\n\t\tset_tax_level = {tax_from_tag[tag]}\n")
            outf.write("\n".join(["\t\tactivate_law = law_type:" + law for law in laws_from_tag[tag]]) + "\n\t}\n}\n")
    os.makedirs(os.path.join(file_dir,"common","history","population"), exist_ok=True)
    for tag, wealth in wealth_from_tag.items():
        with open(os.path.join(file_dir,"common","history","population", f"{tag} - {tag}.txt"),'w', encoding='utf_8_sig') as outf:  # Not actually obvious these need to be different files instead of one mongo file
            outf.write(f"POPULATION = {{\n\tc:{tag} = {{\n\t\teffect_starting_pop_wealth_{wealth} = yes\n\t\teffect_starting_pop_literacy_{literacy_from_tag[tag]} = yes\n\t}}\n}}\n")


def create_adjacencies(file_dir, straits, rgb_from_pid, pid_from_cube, canals=[], closest_xy = None):
    """straits is a list of (cube, cube, pid) tuples (from, to, pid of the water region it passes thru).
    This function will create the adjacencies file (including some calculations about type and positioning)."""
    os.makedirs(os.path.join(file_dir,"map_data"), exist_ok=True)
    with open(os.path.join(file_dir,"map_data","adjacencies.csv"),'w', encoding='utf_8_sig') as outf:
        outf.write("From;To;Type;Through;start_x;start_y;stop_x;stop_y;adjacency_rule_name;Comment")
        for strait in straits:
            fr, to = strait[0], strait[1]
            buffer = [hex_rgb(*rgb_from_pid[pid_from_cube[fr]])]
            buffer.append(hex_rgb(*rgb_from_pid[pid_from_cube[to]]))
            buffer.append("sea")
            buffer.append(hex_rgb(*rgb_from_pid[strait[-1]]) if strait[-1] > 0 else "-1")
            if closest_xy is None:
                buffer.extend([-1] * 4)
            else:
                buffer.extend(closest_xy(fr,to))
                buffer.extend(closest_xy(to, fr))
            buffer.append("")  # adjacency_rule_name, which they never use?
            buffer.append("None")
            outf.write("\n"+";".join([str(x) for x in buffer]))  # No newline at end of file
        # TODO: Canals


def create_default(file_dir, sea_rgbs, lake_rgbs = []):
    """Create default.map"""
    os.makedirs(os.path.join(file_dir,"map_data"), exist_ok=True)
    with open(os.path.join(file_dir,"map_data","default.map"), 'w', encoding='utf_8_sig') as outf:
        outf.write("provinces = \"provinces.png\"\ntopology = \"heightmap.heightmap\"\nrivers = \"rivers.png\"\nadjacencies = \"adjacencies.csv\"\nwrap_x = yes\n\nsea_starts = {\n")
        outf.write("\t\t" + " ".join(sea_rgbs) + "\n}\nlakes= {\n\t" + " ".join(lake_rgbs) + "\n}\n")


def create_objectives(file_dir, base_dir, tags):
    """Modifies 00_objective_tutorial and 01_player_objectives.txt to point to actual tags."""
    os.makedirs(os.path.join(file_dir,"common", "objectives"), exist_ok=True)
    for filename in os.listdir(os.path.join(base_dir, "common", "objectives")):
        with open(os.path.join(file_dir, "common", "objectives", filename), 'w', encoding='utf_8_sig') as outf:
            with open(os.path.join(base_dir, "common", "objectives", filename), 'r', encoding='utf_8_sig') as inf:
                for line in inf.readlines():
                    if "recommended_tags" in line:
                        outf.write(line.split("=")[0] + "= { " + " ".join(random.sample(tags, k=4)) + " }\n")
                    else:
                        outf.write(line)


def create_journals(file_dir, base_dir):
    """Copies over some valid journal files."""
    os.makedirs(os.path.join(file_dir,"common", "journal_entries"), exist_ok=True)
    for filename in [  #TODO: This should be programmatically determined instead of hardcoded :/
        "00_abolish_monarch.txt",  # Has je_warlord_china reference which seems bad
        "00_autocracy.txt",
        "00_corn_laws.txt",
        "00_fascism.txt",
        "00_late_naval_tech.txt",
        "00_liberalism.txt",
        "00_military_tech_je.txt",
        "00_miltech_era_4_5.txt",
        "00_opium.txt",
        "00_plague.txt",
        "00_player_objectives_economic_dominance.txt",
        "00_player_objectives_egalitarian_society.txt",
        "00_player_objectives_hegemon.txt",
        "00_secret_police.txt",
        "00_skyscraper.txt",
        "00_strike_je.txt",
        "00_suffragists.txt",
        "00_technology_production.txt",
        "00_technology_society.txt",
        "00_technology_society_cameras.txt",
        "00_tutorial.txt",
        "00_war_crimes.txt",
        "00_we_live_in_a_society.txt",
        "01_assassination.txt",
        "01_coup.txt",
        "01_flamethrowers.txt",
        "01_grand_exhibition.txt",
        "01_nursing.txt",
        "01_prohibition_laws.txt",
        "01_society_je.txt",
        "01_standard_of_living.txt",
        "01_urbanization.txt",
        "02_nihilism.txt",
        "02_silkworm_diseases.txt",
        "03_positivism.txt",
    ]:
        with open(os.path.join(file_dir, "common", "journal_entries", filename), 'w', encoding='utf_8_sig') as outf:
            with open(os.path.join(base_dir, "common", "journal_entries", filename), 'r', encoding='utf_8_sig') as inf:
                for line in inf.readlines():
                    outf.write(line)
    # TODO: ones that could be customized are 00_belle_epoque and 00_canals


def create_mod(file_dir, config, pid_from_cube, rid_from_pid, terr_from_cube, terr_from_pid, rgb_from_pid, height_from_vertex, river_edges, river_vertices, locs_from_rid, coast_from_rid, name_from_rid, region_trees, tag_from_pid, straits):
    """Creates the V3 mod files in file_dir, given the basic data."""
    # Get some conversion data.
    with open(os.path.join("data", "conversion_v3.yaml"), 'r', encoding="utf_8_sig") as inf:
        conv = yaml.load(inf, yaml.Loader)
        culture_conv = conv.get("culture", {})
        religion_conv = conv.get("religion", {})
    # Make the basic filestructure that other things go in.
    file_dir = create_dot_mod(file_dir=file_dir, mod_name=config.get("MOD_NAME", "testmod"), mod_disp_name=config.get("MOD_DISPLAY_NAME", "testing_worldgen"))
    create_blanks(file_dir=file_dir)  # This is here so if we do make the files later, we won't overwrite them.
    # Combine sea provinces
    new_rgb_from_pid = {}
    rgb_from_rid = {}
    for rid, name in name_from_rid.items():
        if name[0] == "s":
            rgb_from_rid[rid] = rgb_from_pid[min([pid for pid, rr in rid_from_pid.items() if rid==rr])]
    for pid, rgb in rgb_from_pid.items():
        if name_from_rid[rid_from_pid[pid]][0] == "s":
            new_rgb_from_pid[pid] = rgb_from_rid[rid_from_pid[pid]]
        else:
            new_rgb_from_pid[pid] = rgb
    rgb_from_cube = {k:new_rgb_from_pid[pid] for k, pid in pid_from_cube.items()}
    # Maps
    v3map = V3Map(file_dir=file_dir, max_x=config["max_x"], max_y=config["max_y"], n_x=config["n_x"], n_y=config["n_y"])
    v3map.create_provinces(rgb_from_cube=rgb_from_cube)
    v3map.create_heightmap(height_from_vertex=height_from_vertex)
    river_background = {k.cube.tuple():255 if v > WATER_HEIGHT else 254 for k,v in height_from_vertex.items() if k.rot==0}
    v3map.create_rivers(river_background, river_edges, river_vertices, base_loc=os.path.join(config["BASE_V3_DIR"], "map_data", "rivers.png"))
    v3map.create_terrain_masks(base_dir=config["BASE_V3_DIR"], terr_from_cube=terr_from_cube)
    create_terrain_file(file_dir, terr_from_pid=terr_from_pid, rgb_from_pid=new_rgb_from_pid)
    v3map.create_locators(
        file_dir=file_dir,
        locs_from_rid=locs_from_rid,
        pid_from_cube=pid_from_cube,
    )
    v3map.update_defines(base_dir=config["BASE_V3_DIR"])
    sea_rgbs = sorted({hex_rgb(*new_rgb_from_pid[pid]) for pid in sorted(set(coast_from_rid.values()))})
    create_default(file_dir=file_dir, sea_rgbs=sea_rgbs, lake_rgbs=[])
    create_adjacencies(file_dir=file_dir, straits=straits, rgb_from_pid=new_rgb_from_pid, pid_from_cube=pid_from_cube, closest_xy=lambda fr, to: closest_xy(fr, to, v3map.box_height, v3map.box_width))
    srs_from_place = {
        "europe": ["region_east_francia", "region_france", "region_bavaria", "region_christendom_middle",],
        "north_america": [],
        "central_america": [],
        "south_america": [],
        "africa": [],
        "middle_east": ["region_egypt", "region_yemen", "region_syria", "region_arabia_middle"],
        "central_asia": [],
        "india": [],
        "east_asia":[],
        "china":[],
        "southeast_asia":[],
    }
    srs_from_farm = {
        "arabic_farmland": ["region_egypt", "region_yemen", "region_syria", "region_arabia_middle"],
        "asian_farmland": [],
        "subtropic_farmland": [],
        "arid_region": [],
    }
    create_strat_regions(file_dir=file_dir, srs_from_place=srs_from_place, srs_from_farm=srs_from_farm, region_trees=region_trees, rgb_from_pid=rgb_from_pid, name_from_rid=name_from_rid)
    traits_from_rid = {}
    arable_from_rid = {r: (10, ["bg_wheat_farms", "bg_livestock_ranches"]) for r in locs_from_rid.keys()}
    capped_from_rid = {r: {"bg_lead_mining": 10, "bg_iron_mining": 10, "bg_logging": 10, "bg_coal_mining": 10} for r in locs_from_rid.keys()}
    pop_from_rid = {rid_from_pid[pid]: {tag: [(500, "swedish", "catholic")]} for pid, tag in tag_from_pid.items()}
    building_from_rid = {rid_from_pid[pid]: {tag: [("building_government_administration", "1", "1", ["pm_horizontal_drawer_cabinets"])]} for pid, tag in tag_from_pid.items()}
    create_states(
        file_dir=file_dir,
        rid_from_pid=rid_from_pid,
        rgb_from_pid=new_rgb_from_pid,
        name_from_rid=name_from_rid,
        traits_from_rid=traits_from_rid,
        locs_from_rid=locs_from_rid,
        arable_from_rid=arable_from_rid,
        capped_from_rid=capped_from_rid,
        coast_from_rid=coast_from_rid,
        tag_from_pid=tag_from_pid,
        culture_conv=culture_conv,
        religion_conv=religion_conv,
        homelands_from_rid={},  # TODO: Allocate homelands.
        claims_from_rid={},  # TODO: Claims--tho this is probably conversion-only.
        pop_from_rid=pop_from_rid,
        building_from_rid=building_from_rid,
    )
    tags = sorted(set(tag_from_pid.values()))
    tech_from_tag = {tag: "1" for tag in tags}
    tax_from_tag = {tag: "medium" for tag in tags}
    laws_from_tag = {tag: [
        "law_monarchy",
        "law_autocracy",
		"law_freedom_of_conscience",
		"law_serfdom",
		"law_hereditary_bureaucrats",
		"law_national_supremacy",
		"law_isolationism",
		"law_local_police",
		"law_no_schools",
		"law_land_based_taxation",
		"law_censorship",
		"law_closed_borders",
		"law_frontier_colonization",
    ] for tag in tags}
    wealth_from_tag = {tag:"high" for tag in tags}
    literacy_from_tag = {tag:"high" for tag in tags}
    create_countries(
        file_dir=file_dir,
        base_dir=config["BASE_V3_DIR"],
        region_trees=region_trees,
        tech_from_tag=tech_from_tag,
        tax_from_tag=tax_from_tag,
        laws_from_tag=laws_from_tag,
        wealth_from_tag=wealth_from_tag,
        literacy_from_tag=literacy_from_tag,
        name_from_rid=name_from_rid,
        culture_conv=culture_conv,
        religion_conv=religion_conv,
        )
    create_objectives(file_dir=file_dir, base_dir=config["BASE_V3_DIR"], tags=tags)
    strip_base_files(
        file_dir=file_dir,
        src_dir=config["BASE_V3_DIR"],
        subpaths=[
            "common/ai_strategies",
            "common/decisions",
            "common/history/global",
            "events",
        ],
        to_remove=["c:","s:","p:","sr:",],  # cu: ? Also this should maybe be the list of historical tags instead?
        to_keep=[],
        subsection=["triggered_desc = {", "option = {", "if = {"],
        main_file=["common", "on_actions", "00_code_on_actions.txt"],
    )