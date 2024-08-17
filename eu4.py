import os
import random
import shutil

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
    BaseTerrain.farmlands: 10,
    BaseTerrain.hills: 1,
    BaseTerrain.mountains: 6,
    BaseTerrain.forest: 12,
    BaseTerrain.desert: 3,
    BaseTerrain.marsh: 9,
    BaseTerrain.jungle: 254,
    BaseTerrain.ocean: 15,
}


class EU4Map(BasicMap):
    def __init__(self, file_dir, max_x, max_y, n_x, n_y):
        """Creates a map of size max_x * max_y, which is n_x hexes wide and n_y hexes tall."""
        super().__init__(file_dir, "map", max_x, max_y, n_x, n_y)
    
    def create_terrain(self, terr_from_cube, base_loc, file_ext):
        """Creates terrain.bmp"""
        rgb_from_ijk = {k.tuple(): COLOR_FROM_TERR[terr] for k, terr in terr_from_cube.items()}
        create_hex_map(rgb_from_ijk=rgb_from_ijk, max_x=self.max_x, max_y=self.max_y, mode='P', palette=get_palette(os.path.join(base_loc, self.map_dir, "terrain"+file_ext)), default=254, n_x=self.n_x, n_y=self.n_y).save(os.path.join(self.file_dir, self.map_dir, "terrain"+file_ext))

    def prov_extra(self, rgb_from_pid, pid_from_cube, name_from_pid,):
        pass

    
def create_dot_mod(file_dir, mod_name, mod_disp_name):
    """Creates the basic mod structure and metadata file."""
    shared = "version = \"0.0.1\"\n"
    shared += "tags = {\n\t\"Alternative History\"\n\t\"Map\"\n}\n"
    shared += "name = \"{}\"\n".format(mod_disp_name)
    shared += "supported_version = \"1.37.2\"\n"
    outer = "path = \"mod/{}\"\n".format(mod_name)
    
    replace_paths = [
            "common/bookmarks",
            "common/countries",
            "common/disasters",
        ]
    shared += "replace_path = \"" + "\"\nreplace_path = \"".join(replace_paths)+"\""
    os.makedirs(os.path.join(file_dir, mod_name), exist_ok=True)
    with open(os.path.join(file_dir,"{}.mod".format(mod_name)),'w') as f:
        f.write(shared + outer)
    with open(os.path.join(file_dir, mod_name, "descriptor.mod".format(mod_name)),'w') as f:
        f.write(shared)
    return os.path.join(file_dir, mod_name)


def create_adjacencies(file_dir):
    # TODO: Actually write out adjacencies
    with open(os.path.join(file_dir, "map", "adjacencies.csv"), 'w', encoding="utf-8") as outf:
        outf.write("From;To;Type;Through;start_x;start_y;stop_x;stop_y;adjacency_rule_name;Comment\n")
        outf.write("-1;-1;;-1;-1;-1;-1;-1;-1")


def create_bookmarks(file_dir, player_tags, start_date="1444.11.11"):
    """Write out bookmark file."""
    os.makedirs(os.path.join(file_dir, "common", "bookmarks"), exist_ok=True)
    with open(os.path.join(file_dir, "common", "bookmarks", "conversion.txt"), 'w', encoding="utf-8") as outf:
        outf.write("bookmark =\n{\n\tname = \"CONVERSION_BOOKMARK\"\n\tdesc = \"CONVERSION_BOOKMARK_DESC\"\n\tdate = " + start_date + "\n\n\tcenter = 1\n\tdefault = yes\n\n" + "\n".join([f"\tcountry = {tag}" for tag in player_tags]) + "\n}")


def create_colonial_regions(file_dir):
    """Write out common/colonial_regions/00_colonial_regions.txt"""
    os.makedirs(os.path.join(file_dir, "common", "colonial_regions"), exist_ok=True)
    with open(os.path.join(file_dir, "common", "colonial_regions", "00_colonial_regions.txt"), 'w', encoding="utf-8") as outf:
        outf.write("\n")


def create_countries(file_dir, region_trees, gov_from_tag={}):
    """Write out common/countries, common/country_colors/00_country_colors.txt, and common/country_tags/00_countries.txt"""
    os.makedirs(os.path.join(file_dir, "common", "countries"), exist_ok=True)
    os.makedirs(os.path.join(file_dir, "common", "country_colors"), exist_ok=True)
    os.makedirs(os.path.join(file_dir, "common", "country_tags"), exist_ok=True)
    os.makedirs(os.path.join(file_dir, "history", "countries"), exist_ok=True)
    country_color_buffer = ""
    country_tag_buffer = ""
    for region_tree in region_trees:
        for region in region_tree.all_region_trees():
            if region.tag is not None and region.capital_rid != -1:
                with open(os.path.join(file_dir, "common", "countries", f"{region.title}.txt"), 'w', encoding="utf-8") as outf:
                    outf.write(f"graphical_culture = westerngfx\n\ncolor = {{ {' '.join(region.color)} }}\n")
                country_tag_buffer += f"{region.tag} = \"countries/{region.title}.txt\"\n"
                country_color_buffer += f"{region.tag} = {{\n" + " ".join(["\tcolor1 = { " + " ".join(region.color) + " }\n"]) + "}\n\n"
                with open(os.path.join(file_dir, "history", "countries", f"{region.tag}-{region.title}.txt"), 'w', encoding="utf-8") as outf:
                    outf.write("government = " + gov_from_tag.get(region.tag, "monarchy") + "\ngovernment_rank = 1\nmercantilism = 25\ntechnology_group = western\nreligion = " + region.religion + "\nprimary_culture = " + region.culture)
                    outf.write(f"\ncapital = {region.capital_pid}\n")
    with open(os.path.join(file_dir, "common", "country_colors", "00_country_colors.txt"), 'w', encoding="utf-8") as outf:
        outf.write(country_color_buffer)
    with open(os.path.join(file_dir, "common", "country_tags", "00_countries.txt"), 'w', encoding="utf-8") as outf:
        outf.write(country_tag_buffer)


def create_geography(file_dir, pids_from_rid, srid_from_pid, name_from_rid, name_from_srid, cont_names, cont_from_pid):
    region_names = {}
    with open(os.path.join(file_dir, "map", "area.txt"), 'w', encoding="utf-8") as outf:
        for rid, pids in pids_from_rid.items():
            outf.write(f"{name_from_rid[rid]} = {{\n\t{' '.join([str(pid) for pid in pids])}\n}}\n\n")
            srid = srid_from_pid[pids[0]]
            if srid in region_names:
                region_names[srid].add(name_from_rid[rid])
            else:
                region_names[srid] = {name_from_rid[rid]}
    with open(os.path.join(file_dir, "map", "region.txt"), 'w', encoding="utf-8") as routf:
        with open(os.path.join(file_dir, "map", "superregion.txt"), 'w', encoding="utf-8") as sroutf:
            sroutf.write("world_superregion = {\n")
            for srid, srname in name_from_srid.items():
                buffer = ''.join([f"\t\t{area}\n" for area in region_names[srid]])
                routf.write(f"{srname} = {{\n\tareas = {{\n{buffer}\t}}\n}}\n\n")
                sroutf.write(f"\t{srname}\n")
            sroutf.write("}\n")
    with open(os.path.join(file_dir, "map", "continent.txt"), 'w', encoding="utf-8") as outf:
        for cind, cont_name in enumerate(cont_names):
            outf.write(cont_name + " = {\n\t")
            outf.write(" ".join([str(pid) for pid, cont in cont_from_pid.items() if cont == cind]))
            outf.write("}\n\n")
        outf.write("island_check_provinces = {\n}\n\nnew_world = {\n}")


def create_mod(file_dir, config, region_trees, rgb_from_pid, name_from_pid, pids_from_rid, name_from_rid, pid_from_cube, terr_from_cube, gov_from_tag, base_from_vertex, mask_from_vertex, river_flow_from_edge, river_sources, river_merges, river_max_flow, srid_from_pid, name_from_srid, cont_names, cont_from_pid):
    """Creates the EU4 mod files in file_dir, given the basic data."""
    # Make the basic filestructure that other things go in.
    file_dir = create_dot_mod(file_dir=file_dir, mod_name=config.get("MOD_NAME", "testmod"), mod_disp_name=config.get("MOD_DISPLAY_NAME", "testing_worldgen"))
    create_blanks(file_dir, file_paths=[
        ["map", "lakes", "00_lakes.txt"],
        ["map", "ambient_object.txt"],
        ["map", "trade_winds.txt"],
    ], encoding="utf-8")
    player_tags = ["NOR"]
    create_bookmarks(file_dir, player_tags)
    create_colonial_regions(file_dir)
    create_countries(file_dir, region_trees, gov_from_tag)
    eu4map = EU4Map(file_dir, max_x=config["eu4max_x"], max_y=config["eu4max_y"], n_x=config["eu4n_x"], n_y=config["eu4n_y"])
    eu4map.create_provinces(rgb_from_pid, pid_from_cube, ".bmp", name_from_pid=name_from_pid)
    eu4map.create_terrain(terr_from_cube=terr_from_cube, base_loc=config["BASE_EU4_DIR"], file_ext=".bmp")
    eu4map.create_heightmap(base_from_vertex=base_from_vertex, mask_from_vertex=mask_from_vertex, file_ext=".bmp")
    eu4map.create_world_normal()
    eu4map.create_rivers(base_from_vertex, river_flow_from_edge, river_sources, river_merges, river_max_flow, base_loc=config["BASE_EU4_DIR"], file_ext=".bmp")
    create_adjacencies(file_dir)
    create_geography(file_dir, pids_from_rid, srid_from_pid, name_from_rid, name_from_srid, cont_names, cont_from_pid)