import os
import random

from basic_map import BasicMap
from map_io import *
from stripper import create_blanks, strip_base_files
from terrain import *

TERR_NAMES = {
    BaseTerrain.plains: "plains",
    BaseTerrain.farmlands: "plains",
    BaseTerrain.hills: "hills",
    BaseTerrain.mountains: "mountain",
    BaseTerrain.forest: "forest",
    BaseTerrain.desert: "desert",
    BaseTerrain.marsh: "marsh",
    BaseTerrain.jungle: "jungle",
    BaseTerrain.ocean: "ocean",
    BaseTerrain.urban: "urban",
}

COLOR_FROM_TERR = {
    BaseTerrain.plains: 0,
    BaseTerrain.farmlands: 5,
    BaseTerrain.hills: 2,
    BaseTerrain.mountains: 6,
    BaseTerrain.forest: 1,
    BaseTerrain.desert: 3,
    BaseTerrain.marsh: 9,
    BaseTerrain.jungle: 21,
    BaseTerrain.ocean: 15,
    BaseTerrain.urban: 13,
}

class HOI4Map(BasicMap):
    def __init__(self, file_dir, max_x, max_y, n_x, n_y):
        """Creates a map of size max_x * max_y, which is n_x hexes wide and n_y hexes tall."""
        super().__init__(file_dir, "map", max_x, max_y, n_x, n_y)

    def create_provinces(self, rgb_from_pid, pid_from_cube, coastal, cont_from_pid, terr_from_pid, type_from_pid):
        """Creates provinces.png and definition.csv"""
        # This doesn't use the superclass create_provinces and prov_extra because we need to modify the create_hex_map call, and also flip the image.
        rgb_from_ijk = {k.tuple(): rgb_from_pid[pid] for k, pid in pid_from_cube.items()}
        # TODO: fix four-corner joins by painting with rgb_from_vertex? Need to test it to figure out how to use it correctly on map edge.
        create_hex_map(rgb_from_ijk=rgb_from_ijk, max_x=self.max_x, max_y=self.max_y, mode='RGB', default="black", n_x=self.n_x, n_y=self.n_y).transpose(PIL.Image.FLIP_TOP_BOTTOM).save(os.path.join(self.file_dir, "map", "provinces.bmp"))
        with open(os.path.join(self.file_dir, "map", "definition.csv"), 'w') as outf:
            outf.write("0;0;0;0;land;false;unknown;0\n")
            for pid, rgb in sorted(rgb_from_pid.items()):
                r,g,b = rgb
                coast = "true" if pid in coastal else "false"
                outf.write(";".join([str(x) for x in [pid,r,g,b,type_from_pid[pid], coast, TERR_NAMES[terr_from_pid[pid]], cont_from_pid.get(pid,0)]])+"\n")
    
    def create_terrain(self, terr_from_cube, base_loc, file_ext):
        """Creates terrain.bmp"""
        rgb_from_ijk = {k.tuple(): COLOR_FROM_TERR[terr] for k, terr in terr_from_cube.items()}
        create_hex_map(rgb_from_ijk=rgb_from_ijk, max_x=self.max_x, max_y=self.max_y, mode='P', palette=get_palette(os.path.join(base_loc, self.map_dir, "terrain"+file_ext)), default=254, n_x=self.n_x, n_y=self.n_y).save(os.path.join(self.file_dir, self.map_dir, "terrain"+file_ext))

    def create_buildings(self, file_dir, pids_from_rid, coastal):
        """Creates the buildings.txt file, which has x,y locations for lots of buildings.
        pids_from_rid is a mapping of all pids associated with a rid. TODO: restrict to land or check for land before outputting buildings.
        coastal is a mapping from pids to water ids."""
        with open(os.path.join(file_dir, "map", "buildings.txt"), 'w', encoding="utf-8") as outf:
            for rid, pids in pids_from_rid.items():
                for bname, bnum in [("arms_factory", 6), ("industrial_complex", 6), ("anti_air_building", 3), ("air_base", 1), ("synthetic_refinery", 1), ("nuclear_reactor", 1), ("fuel_silo", 1), ("rocket_site", 1)]:
                    for _ in range(bnum):
                        #TODO: actually determine x,y
                        x,z = 0,0
                        y = 10  # Height
                        rot = 0
                        outf.write(f"{rid};{bname};{x};{y};{z};{rot};0\n")
                dockyard = False
                for pid in pids:
                    if pid in coastal:
                        for bname in ["coastal_bunker", "naval_base", "supply_node"]:
                            x,z = 0,0
                            y = 10  # Height
                            rot = 0
                            dockyard = True
                            dx, dz = 0,0
                            dy = 9.6
                            drot = 0  # TODO: point it towards the water
                            outf.write(f"{rid};{bname};{x};{y};{z};{rot};{coastal.get(pid,0)}\n")
                    for bname in ["bunker"]:
                        x,z = 0,0
                        y = 10  # Height
                        rot = 0
                        outf.write(f"{rid};{bname};{x};{y};{z};{rot};0\n")
                if dockyard:
                    outf.write(f"{rid};dockyard;{dx};{dy};{dz};{drot};0\n")

    
def create_dot_mod(file_dir, mod_name, mod_disp_name):
    """Creates the basic mod structure and metadata file."""
    shared = "version = \"0.0.1\"\n"
    shared += "tags = {\n\t\"Alternative History\"\n\t\"Map\"\n}\n"
    shared += "name = \"{}\"\n".format(mod_disp_name)
    shared += "supported_version = \"1.13.7\"\n"
    outer = "path = \"mod/{}\"\n".format(mod_name)
    
    replace_paths = [
            # "common/ai_strategy",
            # "common/ai_strategy_plans",
            # "common/ai_templates",
            # "common/countries",
            # "common/country_tags",
            # "common/country_tag_aliases",
            # "common/ideas",
            # "common/national_focus",
            # "history/countries",
            "history/states",
        ]
    shared += "replace_path = \"" + "\"\nreplace_path = \"".join(replace_paths)+"\""
    os.makedirs(os.path.join(file_dir, mod_name), exist_ok=True)
    with open(os.path.join(file_dir,"{}.mod".format(mod_name)),'w') as f:
        f.write(shared + outer)
    with open(os.path.join(file_dir, mod_name, "descriptor.mod".format(mod_name)),'w') as f:
        f.write(shared)
    return os.path.join(file_dir, mod_name)


def create_countries(file_dir, config, region_trees, tech_from_tag, popularities_from_tag = {}, chars_from_tag = {}, max_dnum=75,):
    """Creates common/countries and history/countries"""
    os.makedirs(os.path.join(file_dir, "common", "countries"), exist_ok=True)
    os.makedirs(os.path.join(file_dir, "common", "country_tags"), exist_ok=True)
    os.makedirs(os.path.join(file_dir, "history", "countries"), exist_ok=True)
    country_tag_buffer = ""
    for region_tree in region_trees:
        for region in region_tree.all_region_trees():
            if region.tag is not None and region.capital_rid != -1:
                with open(os.path.join(file_dir, "common", "countries", f"{region.title}.txt"), 'w', encoding="utf-8") as outf:
                    outf.write(f"graphical_culture = western_european_gfx\n\tgraphical_culture_2d = western_european_2d\n\ncolor = {{ {region.color} }}")
                country_tag_buffer += f"{region.tag} = \"countries/{region.title}.txt\"\n"
                with open(os.path.join(file_dir, "history", "countries", f"{region.tag}-{region.title}.txt"), 'w', encoding="utf-8") as outf:
                    outf.write(f"capital = {region.capital_pid}\nset_oob = \"{region.tag}_1936\"\n\nstarting_train_buffer = 2\nset_technology = {{\n")
                    outf.write("\n".join([f"\t{name} = 1" for name in tech_from_tag[region.tag]]))
                    outf.write("\n}}\nset_research_slots = 3\nset_convoys = 300\n\n")
                    outf.write("set_politics = {\n\truling_party = democractic\n\tlast_election = \"1932.5.1\"\n\telection_frequency = 48\n\telections_allowed = yes\n}\n")
                    outf.write("set_popolarities = {\n" + "\n".join([f"\t{name} = {value}" for name, value in popularities_from_tag.get(region.tag, {"democratic": 64, "fascism": 1, "neutrality": 15, "communism": 20}).items()]) + "\n}\n")
                    if len(chars_from_tag.get(region.tag, [])) > 0:
                        outf.write("\n".join(["recruit_character = {char}" for char in chars_from_tag[region.tag]]))
    with open(os.path.join(file_dir, "common", "country_tags", "02_country_tags.txt"), 'w', encoding="utf-8") as outf:
        outf.write(country_tag_buffer)
    # assert max_dnum < 100  # We _could_ use additional letters to get more than 100, but... why
    # with open(os.path.join(file_dir, "common", "country_tags", "zz_dynamic_tags.txt"), 'w', encoding="utf-8") as outf:
    #     outf.write("dynamic_tags = yes\n" + "\n".join(["D" + str(dnum).rjust(2,"0") + " = \"countries/D" + str(dnum).rjust(2,"0") +".txt\"" for dnum in range(1,max_dnum + 1)]) + "\n")
    # for dnum in range(1, max_dnum + 1):
    #     with open(os.path.join(file_dir, "common", "countries", "D"+str(dnum).rjust(2,"0")+".txt"), 'w', encoding="utf-8") as outf:
    #         outf.write("color = { " + " ".join([str(random.randint(0,255)) for _ in range(3)]) +"}\n")  # Maybe this should copy the vanilla ones instead? They probably have better color choices.
    

def create_states(file_dir, config, pids_from_rid, name_from_rid, manpower_from_rid, category_from_rid, tag_from_rid, cores_from_rid, vps_from_rid, buildings_from_rid,):
    """Creates history/states"""
    os.makedirs(os.path.join(file_dir, "history", "states"), exist_ok=True)
    airbase_buffer = ""
    for rid, pids in pids_from_rid.items():
        if name_from_rid[rid][0] == "s":
            continue
        with open(os.path.join(file_dir, "history", "states", f"{rid}-{name_from_rid[rid]}.txt"),'w', encoding="utf-8") as outf:
            outf.write(f"state={{\n\tid={rid}\n\tname=\"{name_from_rid[rid]}\"\n\tmanpower = {manpower_from_rid[rid]}\n\n\tstate_category = {category_from_rid[rid]}\n\n\thistory={{\n\t\towner = {tag_from_rid[rid]}\n")
            outf.write("\n".join([f"\t\tvictory_points = {{ {pid} {vp} }} " for pid, vp in vps_from_rid[rid].items()]))
            outf.write("\n\t\tbuildings = {\n")
            for building, level in buildings_from_rid[rid].items():
                if building[:1] == "nb":
                    outf.write(f"\t\t\t{building[2:]} = {{\n\t\t\t\tnaval_base = {level}\n\t\t\t}}")
                else:
                    outf.write(f"\t\t\t{building} = {level}\n")
            outf.write("\t\t}\n")
            for tag in cores_from_rid[rid]:
                outf.write(f"\t\tadd_core_of = {tag}\n")
            outf.write(f"\n\t}}\n\n\tprovinces={{\n")
            outf.write("\t\t"+" ".join([str(pid) for pid in pids]))
            outf.write(f"\t}}\n\n\tlocal_supplies=0.0\n}}\n")


def create_minimal(file_dir, base_loc, filenames_from_dirs):
    """For each filename in each directory in filenames_from_dirs, copy over just the first section from that file."""
    # TODO: Make there some sort of mapping so that we can assign the historical graphics to particular countries. Maybe this will need to handle different files separately.
    for dir, file_names in filenames_from_dirs:
        os.makedirs(os.path.join(file_dir, *dir), exist_ok=True)
        for file_name in file_names:
            with open(os.path.join(base_loc, *dir, file_name), encoding="utf-8") as inf:
                with open(os.path.join(file_dir, *dir, file_name), 'w', encoding="utf-8") as outf:
                    brackets = 0
                    for line in inf.readlines():
                        brackets += line.count("{")
                        outf.write(line)
                        brackets -= line.count("}")
                        if brackets == 0:
                            break


def create_rail_supplies(file_dir, supply_nodes, railways):
    """Creates map/supply_nodes.txt and map/railways.txt"""
    with open(os.path.join(file_dir, "map", "supply_nodes.txt"), 'w', encoding="utf-8") as outf:
        for pid in supply_nodes:
            outf.write(f"1 {pid}\n")
    with open(os.path.join(file_dir, "map", "railways.txt"), 'w', encoding="utf-8") as outf:
        for level, path in railways:
            outf.write(str(level) + " " + str(len(path)) + " " + " ".join(str(pid) for pid in path) + "\n")


def create_mod(file_dir, config, pid_from_cube, rgb_from_pid, terr_from_cube, terr_from_pid, rid_from_pid, tag_from_pid, type_from_pid, cont_from_pid, coast_from_cube, pids_from_rid, name_from_rid, river_edges, river_vertices, locs_from_rid, height_from_vertex, region_trees, supply_nodes, railways,):
    """Creates the HOI4 mod files in file_dir, given the basic data."""
    # Make the basic filestructure that other things go in.
    file_dir = create_dot_mod(file_dir=file_dir, mod_name=config.get("MOD_NAME", "testmod"), mod_disp_name=config.get("MOD_DISPLAY_NAME", "testing_worldgen"))
    # create_blanks(file_dir=file_dir, file_paths=[
    #     ["common", "country_tag_aliases", "tag_aliases.txt"],
    # ], encoding="utf-8")  # This is here so if we do make the files later, we won't overwrite them.
    hoi4map = HOI4Map(file_dir=file_dir, max_x=config["max_x"], max_y=config["max_y"], n_x=config["n_x"], n_y=config["n_y"])
    # Figure out which pids are coastal, given which cubes are coastal.
    coastal = {pid_from_cube[cube]: coast_from_cube[cube] for cube in coast_from_cube}
    coastal.update({pid: pid for pid in sorted(set(coast_from_cube.values()))})  # We want the coastal water to also be flagged; this is maybe the wrong way to identify it.
    hoi4map.create_provinces(rgb_from_pid, pid_from_cube, coastal, cont_from_pid, terr_from_pid, type_from_pid)
    hoi4map.create_terrain(terr_from_cube=terr_from_cube, base_loc=config["BASE_HOI4_DIR"], file_ext=".bmp")
    hoi4map.create_heightmap(height_from_vertex=height_from_vertex, file_ext=".bmp")
    hoi4map.create_world_normal()
    hoi4map.create_buildings(file_dir=file_dir, pids_from_rid=pids_from_rid, coastal=coastal)
    hoi4map.create_rivers(height_from_vertex, river_edges, river_vertices, base_loc=config["BASE_HOI4_DIR"], file_ext=".bmp")
    create_rail_supplies(file_dir, supply_nodes, railways)
    tags = sorted(set(tag_from_pid.values()))
    tag_from_rid = {rid_from_pid[pid]: tag for pid, tag in tag_from_pid.items()}
    tech_from_tag = {tag: ["infantry_weapons", "infantry_weapons1", "tech_support", "tech_engineers", "tech_recon", "tech_mountaineers", "tech_trucks", "motorised_infantry", "gw_artillery", "interwar_antiair", "trench_warfare", "fleet_in_being", "fuel_silos", "fuel_refining", "basic_train",] for tag in tags}
    vps_from_rid = {}
    buildings_from_rid = {}
    for rid, pids in pids_from_rid.items():
        if name_from_rid[rid][0] == "s":
            continue
        vps_from_rid[rid] = {min(pids): 1}
        buildings_from_rid[rid] = {
			"infrastructure": 1,
			"arms_factory": 1,
			"industrial_complex": 1,
			"anti_air_building": 1,
			"air_base": 1,
            }
    create_countries(file_dir, config, region_trees, tech_from_tag)
    manpower_from_rid = {rid: 10000 for rid, name in name_from_rid.items() if name[0] != "s"}
    category_from_rid = {rid: "large_city" for rid, name in name_from_rid.items() if name[0] != "s"}
    cores_from_rid = {rid: [tag] for rid, tag in tag_from_rid.items()}
    create_states(file_dir, config, pids_from_rid, name_from_rid, manpower_from_rid, category_from_rid, tag_from_rid, cores_from_rid, vps_from_rid, buildings_from_rid,)
    
    # create_minimal(file_dir, config["BASE_HOI4_DIR"], [
    #     (["gfx","interface","equipmentdesigner", "graphic_db"], ["00_plane_icons.txt", "00_tank_icons.txt"]),
    #     (["common", "ideas"], ["_economic.txt", "_manpower.txt", "zzz_generic.txt"]),  # TODO: The first two need to be stripped instead.
    # ])
    # strip_base_files(file_dir=file_dir, src_dir=config["BASE_HOI4_DIR"],subpaths=[
    #     "common\\national_focus\\generic.txt",
    # ], to_remove=["\ttag ="], to_keep=[], subsection=["modifier = {"], encoding="utf-8")
