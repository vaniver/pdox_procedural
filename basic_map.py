import os

from map_io import *
from terrain import WATER_HEIGHT

class BasicMap:
    def __init__(self, file_dir, map_dir, max_x, max_y, n_x, n_y):
        """Creates a map of size max_x * max_y, which is n_x hexes wide and n_y hexes tall."""
        self.file_dir = file_dir
        self.map_dir = map_dir
        os.makedirs(os.path.join(file_dir, map_dir), exist_ok=True)
        self.max_x = max_x
        self.max_y = max_y
        self.n_x = n_x
        self.n_y = n_y
        self.box_width, self.box_height = box_from_max(self.max_x, self.max_y, self.n_x, self.n_y)

    def create_provinces(self, rgb_from_pid, pid_from_cube, file_ext, **extras):
        """Creates provinces.file_ext and calls self.prov_extra, where you should put things like definition.csv"""
        rgb_from_ijk = {k.tuple(): rgb_from_pid[pid] for k, pid in pid_from_cube.items()}
        create_hex_map(rgb_from_ijk=rgb_from_ijk, max_x=self.max_x, max_y=self.max_y, mode='RGB', default="black", n_x=self.n_x, n_y=self.n_y).save(os.path.join(self.file_dir, self.map_dir, "provinces" + file_ext))
        self.prov_extra(rgb_from_pid, pid_from_cube, **extras)
    
    def prov_extra(self, rgb_from_pid, pid_from_cube):
        pass

    def create_heightmap(self, height_from_vertex, file_ext, size_factor=1, **extras):
        """Uses height_from_cube to generate a simple heightmap."""
        create_tri_map(height_from_vertex=height_from_vertex, max_x=self.max_x * size_factor, max_y=self.max_y * size_factor, n_x=self.n_x, n_y=self.n_y).save(os.path.join(self.file_dir, self.map_dir, "heightmap"+file_ext))
        self.height_extra(**extras)

    def height_extra(self):
        pass

    def create_rivers(self, height_from_vertex, river_edges, river_vertices, base_loc, file_ext):
        """Create rivers.file_ext"""
        river_background = {k.cube.tuple():255 if v > WATER_HEIGHT else 254 for k,v in height_from_vertex.items() if k.rot==0}
        create_hex_map(rgb_from_ijk=river_background, rgb_from_edge=river_edges, rgb_from_vertex=river_vertices, max_x=self.max_x, max_y=self.max_y, mode='P', palette=get_palette(os.path.join(base_loc, self.map_dir, "rivers"+file_ext)), default=254, n_x=self.n_x, n_y=self.n_y).save(os.path.join(self.file_dir, self.map_dir, "rivers"+file_ext))