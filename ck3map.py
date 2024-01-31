# This file is for file IO for CK3 maps.

from cube import Cube
from shared_map import *
from dataclasses import dataclass
from enum import Enum
import heapq
from itertools import combinations, count
from math import sqrt
import PIL.Image
import os
import random
from typing import Tuple

import numpy as np
# from scipy.ndimage import gaussian_filter

def dist2line(x, y, srcx, srcy, destx, desty):
    return abs((desty-srcy)*x-(destx-srcx)*y+destx*srcy-desty*srcx)/sqrt((desty-srcy)**2+(destx-srcx)**2)

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

@dataclass
class RiverTrios:
    width: int = 0
    start_trio: Tuple[int, int, int] = (0, 0, 0)
    start_xy: Tuple[int, int] = (0, 0)
    end_trio: Tuple[int, int, int] = (0, 0, 0)
    end_xy: Tuple[int, int] = (0, 0)
    merge: bool = False
    source: bool = False
    name: str = "River"


@dataclass
class RiverEdge:
    cube: Cube = None
    edge: int = 0
    start_xy: Tuple[int, int] = (0, 0)
    end_xy: Tuple[int, int] = (0, 0)
    split: bool = False
    merge: bool = False
    source: bool = False
        
    def __hash__(self):
        return hash(tuple((self.cube.x, self.cube.y, self.cube.z, self.edge)))

    def set_xy(self, cmap):
        '''Set the start and end xy values for this edge.'''
        assert cmap.crisp
        cx, cy = cmap.c2cx[self.cube], cmap.c2cy[self.cube]
        from_el = self.cube.add(Cube(0, 1, -1).rotate_right(self.edge - 1))
        fcx, fcy = cmap.c2cx[from_el], cmap.c2cy[from_el]
        other_el = self.cube.add(Cube(0, 1, -1).rotate_right(self.edge))
        ocx, ocy = cmap.c2cx[other_el], cmap.c2cy[other_el]
        to_el = self.cube.add(Cube(0, 1, -1).rotate_right(self.edge + 1))
        tcx, tcy = cmap.c2cx[to_el], cmap.c2cy[to_el]
        self.start_xy = ((cx + fcx + ocx) // 3, (cy + fcy + ocy) // 3)
        self.end_xy = ((cx + tcx + ocx) // 3, (cy + tcy + ocy) // 3)

    def check_valid(self, land_height):
        if self.cube not in land_height:
            return False
        if self.cube.add(Cube(0, 1, -1).rotate_right(self.edge)) not in land_height:
            return False  # All river edges need to have land on the other side.
        return True

    def check_downhill(self, cmap):
        if self.start_xy == (0, 0):
            self.set_xy(cmap)
        return cmap.topo[self.start_xy[0], self.start_xy[1]] >= cmap.topo[self.end_xy[0], self.end_xy[1]]
    
    def check_final(self, land_height):
        if self.cube.add(Cube(0, 1, -1).rotate_right(self.edge - 1)) in land_height:
            return False  # This river is pointed towards a land hex.
        return self.check_valid(land_height)

    def upstream(self):
        return (RiverEdge(self.cube, self.edge - 1),
                RiverEdge(self.cube.add(Cube(0, 1, -1).rotate_right(self.edge - 1)), self.edge + 1))

    def downstream(self):
        return (RiverEdge(self.cube, self.edge + 1),
                RiverEdge(self.cube.add(Cube(0, 1, -1).rotate_right(self.edge + 1)), self.edge - 1))

def new_rgb(dictionary):
    '''Returns a randomly chosen RGB value that isn't already in the values of dictionary.'''
    guess = tuple(np.random.randint(0,256,3))
    if guess in dictionary.values() or guess == (255,255,255) or guess == (0,0,0) or guess == IMPASSABLE:
        return new_rgb(dictionary)
    else:
        return guess


class CK3Map:
    
    def __init__(self, max_x=8192, max_y=4096, hex_size=40, map_size=40, crisp=True, default=None):
        '''Creates a map of size max_x x max_y, with hexes that have radius hex_size pixels, and at most map_size hexes on an edge. If crisp=True (default), the hexes will all be regular and the same size; if crisp=False, the sizes will vary to make them visually distinct, and will extend to the edge of the image boundary.'''
        assert max_x % 1024 == 0
        assert max_y % 1024 == 0
        self.max_x = max_x
        self.max_y = max_y
        self.mid_x = max_x/2
        self.mid_y = max_y/2
        self.hex_size = hex_size
        self.default = default
        mr = int(min(map_size, max_x/(hex_size*4), max_y/(hex_size*4)))
        self.map_rad = mr
        self.num_hexes = 3*(self.map_rad*(self.map_rad+1))+1
        self.scale = max(1,64/mr)
        self.img_provinces = PIL.Image.new('RGB', (max_x,max_y),  "black")
        self.img_topology = PIL.Image.new('L', (max_x,max_y),  "white")
        self.img_rivers = PIL.Image.new('P', (max_x,max_y),  255)  # 255=white
        with open(os.path.join("data", "rivers_palette.txt"), "r") as f:
            self.img_rivers.putpalette([int(s) for s in f.read().split(',')])
        self.d_cube2rgb = {}
        self.d_cube2terr = {}
        self.d_cube2pid = {}
        self.d_trio2vertex = {}
        self.d_trio2river = {}
        self.river_weights = {}
        self.s3 = sqrt(3)
        self.l_valid_cubes = None
        self.crisp = crisp
        self.cx = np.zeros(self.num_hexes)
        self.cy = np.zeros(self.num_hexes)
        self.c2cx = {}
        self.c2cy = {}
        for ind, c in enumerate(self.valid_cubes):
            i = c.x
            j = c.y
            k = c.z
            self.cx[ind] = int(i * 1.5 * self.hex_size + self.mid_x)
            self.cy[ind] = self.max_y - int((j * 3 * self.hex_size + self.cx[ind] - self.mid_x) / self.s3 + self.mid_y)
            self.c2cx[c] = self.cx[ind]
            self.c2cy[c] = self.cy[ind]
        if self.crisp:
            self.paint_edge = self.paint_edge_crisp
            self.paint_major_river = self.paint_major_river_crisp
        if not self.crisp:
            self.paint_edge = self.paint_edge_non_crisp
            self.paint_major_river = self.paint_major_river_non_crisp
            self.sigma = np.zeros(self.num_hexes)
            self.c2sigma = {}
            for ind, c in enumerate(self.valid_cubes):
                self.sigma[ind] = np.random.rand() + 0.5
                self.c2sigma[c] = self.sigma[ind]

    def pixel_to_cube(self, x,y):
        if self.crisp:
            q = (x-self.mid_x) * 2.0/3.0/self.hex_size
            r = (-(x-self.mid_x) / 3.0 + self.s3/3.0 * (y-self.mid_y))/self.hex_size
            return cube_round(q,-q-r,r)
        return self.valid_cubes[(((self.cx-x)**2+(self.cy-y)**2)/self.sigma).argmin()]
        

    def cube_to_pid(self, i, j=None, k=None):
        '''Note that province id (pid) is not the same as the ordering in the valid cubes list.'''
        if j is None:
            j = i.y
            k = i.z
            i = i.x
        return (i+self.map_rad)*2*(self.map_rad+1)+k+self.map_rad+1

    def ijk_to_rgb(self, i, j, k):
        c = Cube(i,j,k)
        return self.cube_to_rgb(c)

    def cube_to_rgb(self, c):
        if c in self.d_cube2rgb:
            return self.d_cube2rgb[c]
        else:
            if self.default:
                r, g, b = self.default
            else:
                i, j, k = c.x, c.y, c.z
                r, g, b = (int(i*self.scale+128), int(j*self.scale+128), int(k*self.scale+128))
            self.d_cube2rgb[c] = (r,g,b)
            return (r,g,b)
            
    def cube_to_terr(self, c):
        if c in self.d_cube2terr:
            return self.d_cube2terr[c]
        else:
            self.d_cube2terr[c] = CK3Terrain.plains
            return self.d_cube2terr[c]
            
    def valid_pixel(self, x, y, r = 0):
        '''Determines whether a pixel is within the hexagon whose boundary is the center of all the hexes.
        (If the map doesn't use ocean outlying hexes, increase r accordingly.)'''
        return (round(-self.hex_size * (self.map_rad - 1) * self.s3) - r <= \
                x - self.mid_x <= \
                round(self.hex_size * (self.map_rad - 1) * self.s3) + r) and \
                (round(-self.hex_size*(self.map_rad - 1) * self.s3) - r <= \
                0.5 * ((x - self.mid_x) + self.s3 * (y - self.mid_y)) <= \
                round(self.hex_size * (self.map_rad - 1) * self.s3) + r) and \
                (round(-self.hex_size * (self.map_rad - 1) * self.s3) - r <= \
                0.5 * (self.s3 * (y - self.mid_y) - (x - self.mid_x)) <= \
                round(self.hex_size * (self.map_rad - 1) * self.s3) + r)
        
    @property
    def valid_cubes(self):
        if self.l_valid_cubes is not None:
            return self.l_valid_cubes
        self.l_valid_cubes = []
        for i in range(-self.map_rad,self.map_rad+1):
            for j in range(-self.map_rad,self.map_rad+1):
                k = 0 - i - j
                if -self.map_rad <= k <= self.map_rad:
                    self.l_valid_cubes.append(Cube(i,j,k))
        return self.l_valid_cubes

    def cubes2trio(self, trio):
        """Given a trio of cubes, return a trio of indices in valid_cubes."""
        if isinstance(trio[0], int):
            return trio
        for a, b in combinations(trio, 2):
            assert a.dist(b) == 1, f"Three cubes are not neighbors: {trio}."
        return tuple(sorted([self.valid_cubes.index(el) for el in trio]))
        
    def find_vertex(self, trio):
        """Finds the integer x,y pair that is the vertex between the three hexes.
        Can be provided either a truple of Cubes or a sorted tuple of indices."""
        trio = self.cubes2trio(trio) if isinstance(trio[0], Cube) else trio
        if trio in self.d_trio2vertex:
            return self.d_trio2vertex[trio]
        x = sum([self.cx[el] for el in trio])/3
        y = sum([self.cy[el] for el in trio])/3
        if self.crisp:
            self.d_trio2vertex[trio] = (int(x), int(y))
            return self.d_trio2vertex[trio]
        dists = [((x - self.cx[el])**2 + (y - self.cy[el])**2)/self.c2sigma[el] for el in trio]
        delta = max(dists) - min(dists)
        ldelta = 999999
        while delta < ldelta:
            lx = x
            ly = y
            ldelta = delta
            move_towards = np.argmax(dists)
            if abs(x - self.cx[trio[move_towards]]) > abs (y > self.cy[trio[move_towards]]):
                if x > self.cx[trio[move_towards]]:
                    x -= 1
                elif x < self.cx[trio[move_towards]]:
                    x += 1
            else:
                if y > self.cy[trio[move_towards]]:
                    y -= 1
                elif y < self.cy[trio[move_towards]]:
                    y += 1
            dists = [((x - self.cx[el])**2 + (y - self.cy[el])**2)/self.c2sigma[el] for el in trio]
            delta = max(dists) - min(dists)
        self.d_trio2vertex[trio] = (int(lx), int(ly))
        return (int(lx), int(ly))

    def edge_middle(self, hex_a, hex_b):
        """Find the x,y pair that are on the edge between hex_a and hex_b, equidistant to both centers (probably closest?)."""
        assert hex_a.dist(hex_b) == 1, "Cannot have edge between hexes that are not adjacent."
        vc_ids = tuple(sorted([self.valid_cubes.index(el) for el in [hex_a, hex_b]]))
        x, y = sum([self.cx[vc] for vc in vc_ids])/2, sum([self.cy[vc] for vc in vc_ids])/2
        if self.crisp:
            return (int(x), int(y))
        dists = [((x - self.cx[el])**2 + (y - self.cy[el])**2)/self.c2sigma[el] for el in vc_ids]
        delta = max(dists) - min(dists)
        ldelta = 999999
        while delta < ldelta:
            lx = x
            ly = y
            ldelta = delta
            move_towards = np.argmax(dists)
            if abs(x - self.cx[vc_ids[move_towards]]) > abs (y > self.cy[vc_ids[move_towards]]):
                if x > self.cx[vc_ids[move_towards]]:
                    x -= 1
                elif x < self.cx[vc_ids[move_towards]]:
                    x += 1
            else:
                if y > self.cy[vc_ids[move_towards]]:
                    y -= 1
                elif y < self.cy[vc_ids[move_towards]]:
                    y += 1
            dists = [((x - self.cx[el])**2 + (y - self.cy[el])**2)/self.c2sigma[el] for el in vc_ids]
            delta = max(dists) - min(dists)
    
    def calc_rivers(self, num_rivers, land_height):
        '''Calculate num_rivers rivers, adding them to self.d_trio2river'''
        for i in range(num_rivers):
            print(i)
            # Choose a random hex, weighted by height.
            worked = False
            while not worked:
                source = random.choices(population=list(land_height.keys()), weights=list(land_height.values()), k=1)[0]
                worked = self.source_river(source, land_height)

    def calc_rivers_upwards(self, num_rivers, land_height):
        '''Calculate num_rivers rivers, adding them to self.d_trio2river. Starts with the end of the river,
        and then flows upwards as far as possible.'''
        poss_final_edges = set()
        for el, height in land_height.items():
            if height == 0:
                for rotation in range(6):
                    RiverEdge(el, rotation)
                    if RiverEdge(el, rotation).check_final(land_height):
                        poss_final_edges.add(RiverEdge(el, rotation))
        for i in range(num_rivers):
            final = random.choice(list(poss_final_edges))
            poss_final_edges.remove(final)
            self.river_weights[final] = 1
            self.flow_up(final, land_height)
            
    def flow_up(self, river_edge, land_height, source = True):
        '''Given a river_edge, see if either of the edges leading into it could flow into it'''
        # Calculate the two edges that could flow into this river.
        poss = river_edge.upstream()
        vposs = [p for p in poss if p.check_valid(land_height)]
        if len(vposs) == 0:
            river_edge.source = source
            return river_edge
        if len(vposs) == 2 and random.random < RIVER_BRANCH_CHANCE:
            # Branch.
            self.flow_up(vposs[0], land_height, source=source)
            self.flow_up(vposs[1], land_height, source=False)
        else:
            self.self.flow_up(random.choice(vposs), land_height, source=source)
        split = [p in self.river_weights for p in vposs]

    def source_river(self, source, land_height) -> bool:
        '''Source is a cube. First find its highest vertex, and then extend it towards water. 
        Returns True if successful, False if restarting a previously started (or illegal) river.'''
        width = 0
        height = 0
        for rot in range(6):
            trio = [source, source.add(Cube(-1,0,1).rotate_right(rot)),source.add(Cube(-1,0,1).rotate_right(rot+1))]
            if trio[1] not in land_height or trio[2] not in land_height:
                continue
            tx, ty = self.find_vertex(trio)
            if self.topo[tx,ty] >= height:
                b3cubes = trio
                height = self.topo[tx,ty]
                sx, sy = tx, ty
        if height == 0:  # Couldn't find a vertex that doesn't touch water.
            return False
        start_trio = self.cubes2trio(b3cubes)
        if start_trio in self.d_trio2river:
            return False
        b3cubes = [self.valid_cubes[el] for el in start_trio]  # This reorders them, which is necessary for the next bit.
        b3cube_total = b3cubes[0].add(b3cubes[1]).add(b3cubes[2])
        # Find the lowest of the adjacent vertices.
        height = 256
        for away_cube_ind in range(3):
            # The next cube is the sum of the two cubes you follow minus the one you're moving away from.
            # For reasons, I'm calculating this as a+b+c-a-a instead of b+c-a.
            away_cube = b3cubes[away_cube_ind]
            next_cube = b3cube_total.sub(away_cube).sub(away_cube)
            next_trio = tuple(sorted([el for ind, el in enumerate(start_trio) if ind != away_cube_ind] + [self.valid_cubes.index(next_cube)]))
            tx, ty = self.find_vertex(next_trio)
            if self.topo[tx,ty] <= height:
                end_trio = next_trio
                end_away_cube = away_cube
                height = self.topo[tx,ty]
                end_xy = tx, ty
        assert height < 256
        # Now we have the end of the first river edge.
        self.d_trio2river[start_trio] = RiverTrios(width=width, start_trio=start_trio, start_xy=(sx,sy), end_trio=end_trio, end_xy=end_xy, source=True, merge=False)
        self.extend_river(end_trio, end_xy, end_away_cube, start_trio, width + 1, land_height)
        return True
            

    def extend_river(self, start_trio, start_xy, away_cube, source_trio, width, land_height):
        '''Given a river start_trio (the ending of the previous) and the cube it was moving away from, extend it towards the ocean.
        source_trio is used to delete 'source' from the first edge if this river merges into another.'''
        if start_trio in self.d_trio2river:
            self.d_trio2river[start_trio].source = False
            # TODO: Get this to not loop infinitely
            # self.join_flow(start_trio, width)
            return
        start_cubes = [self.valid_cubes[el] for el in start_trio]
        assert away_cube not in start_cubes
        # This cube is guaranteed to be included in the next trio.
        for t_ind, t_cube in enumerate(start_cubes):
            if t_cube.dist(away_cube) != 1:
                in_el = start_trio[t_ind]
        # Find which of the two directions is lower.
        height = 256
        for t_ind, t_cube in enumerate(start_cubes):
            if t_cube.dist(away_cube) != 1:
                continue
            next_cube = t_cube.add(t_cube).sub(away_cube)
            next_trio = tuple(sorted([start_trio[t_ind], in_el, self.valid_cubes.index(next_cube)]))
            tx, ty = self.find_vertex(next_trio)
            if self.topo[tx,ty] <= height:
                end_trio = next_trio
                height = self.topo[tx,ty]
                end_xy = (tx, ty)
        assert height < 256
        # Now we know which way to keep flowing.
        end3cubes = [self.valid_cubes[el] for el in end_trio]
        assert all([a.dist(b) == 1 for a,b in combinations(end3cubes, 2)])
        away_cube = [c for c in start_cubes if c not in end3cubes][0]
        if end_trio in self.d_trio2river:
            # We've run into a previous river. We need to figure out if it's a source or not.
            if self.d_trio2river[end_trio].source:
                self.d_trio2river[start_trio] = RiverTrios(width=width, start_trio=start_trio, start_xy=start_xy, end_trio=end_trio, end_xy=end_xy, source=False, merge=False)
            else:
                self.d_trio2river[start_trio] = RiverTrios(width=width, start_trio=start_trio, start_xy=start_xy, end_trio=end_trio, end_xy=end_xy, source=False, merge=True)
                self.d_trio2river[source_trio].source = False
        else:
            self.d_trio2river[start_trio] = RiverTrios(width=width, start_trio=start_trio, start_xy=start_xy, end_trio=end_trio, end_xy=end_xy, source=False, merge=False)
        if next_cube in land_height:  # If we haven't reached water, keep going.
            self.extend_river(end_trio, end_xy, away_cube, source_trio, width + 1, land_height)

    def join_flow(self, trio, width):
        '''Adds the width of a joining river to all downstream edges.'''
        cycle_prevention = set()
        while trio in self.d_trio2river and trio not in cycle_prevention:
            self.d_trio2river[trio].width += width
            cycle_prevention.add(trio)
            trio = self.d_trio2river[trio].end_trio
    
    def provinces(self, filedir=None):
        '''Create provinces.bmp. Uses d_cube2rgb, choosing colors based on position if any are empty.Saves if filedir is passed.'''
        pixels = self.img_provinces.load()
        last_i, last_j, last_k = (-999, -999, -999)
        last_r, last_g, last_b = IMPASSABLE
        for x in range(self.max_x):
            for y in range(self.max_y):
                #check if inside big hex
                if self.valid_pixel(x,y):
                    i, j, k = self.pixel_to_cube(x,y).tuple()
                    if not( i==last_i and j==last_j and k==last_k ):
                        last_r, last_g, last_b = self.ijk_to_rgb(i,j,k)
                        last_i, last_j, last_k = i, j, k
                    pixels[x,y] = (last_r, last_g, last_b)
                else:
                    pixels[x,y] = IMPASSABLE
        if filedir:
            self.save_provinces(filedir)

    def save_provinces(self, filedir):
        self.img_provinces.save(os.path.join(filedir, 'map_data', 'provinces.png'))

    def heightmap(self, land_height, water_depth, waste_list, filedir, sigma=0):
        '''Create heightmap.png. Uses a Gaussian filter with sigma; pass sigma=0 to not smooth.
        Also generates terrain files.'''
        assert sigma==0
        self.topo = np.zeros((self.max_x,self.max_y))
        land = np.zeros((self.max_x,self.max_y), dtype=bool)
        all_wastes = set()
        for waste in waste_list:
            for w in waste:
                all_wastes.add(w)
        mask_dir = os.path.join(filedir, "gfx", "map", "terrain")
        os.makedirs(mask_dir, exist_ok=True)
        terr_masks = {}
        terr_pixels = {}
        for terr_name in TERRAIN_MASK_TYPES:
            terr_masks[terr_name] = PIL.Image.new('L', (self.max_x,self.max_y),  "black")
            if terr_name in USED_MASKS.values():
                terr_pixels[terr_name] = terr_masks[terr_name].load()
        flatmap = PIL.Image.new('RGB', (self.max_x, self.max_y),  "black")
        fpixels = flatmap.load()
        last_cube = None
        last_waste = False
        last_range = (0,0)
        ocean_terr = USED_MASKS[None]
        flat_dry = (170, 160, 140)
        flat_wet = (110, 110, 100)
        last_terr = ocean_terr
        last_flat = flat_wet
        for x in range(self.max_x):
            for y in range(self.max_y):
                if self.valid_pixel(x,y):
                    c = self.pixel_to_cube(x,y)
                    if c != last_cube:
                        if c in land_height:
                            last_height = WATER_HEIGHT + 1 + land_height[c] * 3
                            last_land = True
                            last_flat = flat_dry
                        elif c in water_depth:
                            last_height = max(WATER_HEIGHT - 1 - water_depth[c] * 3, 0)
                            last_land = False
                            last_flat = flat_wet
                        else:
                            last_height = 0
                            last_land = False
                            last_flat = flat_wet
                        if c in all_wastes:
                            last_waste = True
                        else:
                            last_waste = False
                        if c in self.d_cube2terr:
                            terr = self.d_cube2terr[c]
                            last_range = TERRAIN_HEIGHT[terr]
                            if last_waste and (terr in [CK3Terrain.mountains, CK3Terrain.desert_mountains]):
                                last_range = (last_range[0] + 2, last_range[1] + 10)
                            last_terr = USED_MASKS[terr]
                        else:
                            last_range = (0,0)
                            last_terr = ocean_terr
                        last_cube = c
                    if c in self.c2cx:
                        r = max(0, self.hex_size - sqrt((self.c2cx[c] - x)**2 + (self.c2cy[c] - y)**2))  # This should be fine, but adding max(0) to be sure.
                    else:
                        r = 0
                    try:
                        self.topo[x,y] = last_height + last_range[0] + random.randint(0, int(r * last_range[1]))
                    except:
                        print(last_range[1], int(r * last_range[1]))
                        raise ValueError
                    land[x,y] = last_land
                    terr_pixels[last_terr][x,y] = 255
                    fpixels[x,y] = last_flat
                else:
                    self.topo[x,y] = 0
                    terr_pixels[ocean_terr][x,y] = 255
                    fpixels[x,y] = flat_wet
        for terr_name in TERRAIN_MASK_TYPES:
            terr_masks[terr_name].save(os.path.join(mask_dir, terr_name + '_mask.png'))
        flatmap.save(os.path.join(mask_dir, 'flatmap.png'))
        PIL.Image.new('RGB', (self.max_x, self.max_y),  (255,255,255)).save(os.path.join(mask_dir, 'colormap.png'))
        # if sigma > 0:
        #     self.topo = np.rint(gaussian_filter(self.topo, sigma=sigma))
        #     for x in range(self.max_x):
        #         for y in range(self.max_y):
        #             if land[x,y]:
        #                 self.topo[x,y] = max(self.topo[x,y], WATER_HEIGHT + 1)
        #             else:
        #                 self.topo[x,y] = min(self.topo[x,y], WATER_HEIGHT - 1)
        self.img_topology.putdata(self.topo.transpose().flatten())  # Maybe need to cast it to int first?
        if filedir:
            with open(os.path.join(filedir, "map_data", 'heightmap.heightmap'), 'w') as f:
                f.write("heightmap_file=\"map_data/packed_heightmap.png\"\n")
                f.write("indirection_file=\"map_data/indirection_heightmap.png\"\n")
                f.write(f"original_heightmap_size={{ {self.max_x} {self.max_y} }}\n")
                f.write("tile_size=33\n")
                f.write("should_wrap_x=no\n")
                f.write("level_offsets={ { 0 0 }{ 0 0 }{ 0 0 }{ 0 0 }{ 0 7 }}\n")
            self.img_topology.save(os.path.join(filedir, "map_data", 'heightmap.png'))
            
    def rivers(self, land_height, bname_from_pid, num_rivers, last_pid, filedir=''):
        '''Create rivers.png.
        This will possibly edit provinces.png, definition.csv, and adjacencies.csv if it creates any major rivers.'''
        self.calc_rivers(num_rivers, land_height)
        r_pixels = self.img_rivers.load()
        lc = Cube(0,0,0)
        def_addenda = []
        adj_addenda = []
        # Determine some palette colors.
        # Figure out all the possible river widths:
        widths = sorted({riv.width for riv in self.d_trio2river.values()})
        if len(widths) > 0 and widths[-1] >= MAJOR_RIVER_THRESHOLD:
            p_pixels = self.img_provinces.load()
            print("At least one major river will be made.\n")
        width_mapping = {width: 3 + i if width < MAJOR_RIVER_THRESHOLD else 254 for i, width in enumerate(widths)}
        # Set the background colors.
        for x in range(self.max_x):
            for y in range(self.max_y):
                #check if inside big hex
                if self.valid_pixel(x, y):
                    c = self.pixel_to_cube(x, y)
                    if c != lc:
                        if c in land_height:
                            lpix = LAND
                        else:
                            lpix = WATER
                        lc = c
                    r_pixels[x,y] = lpix
                else:
                    r_pixels[x,y] = WATER
        # Now we can start making rivers; each edge can be done independently.
        # TODO: major_rivers just has the pids for each river. But it should group them, so that they can be grouped in default.map.
        major_rivers = []
        for start_trio, riv in self.d_trio2river.items():
            if riv.width < MAJOR_RIVER_THRESHOLD:
                self.paint_edge(riv.start_xy, riv.end_xy, width_mapping[riv.width], r_pixels, riv.merge, extend=not(riv.end_trio in self.d_trio2river) or self.d_trio2river[riv.end_trio].width >= MAJOR_RIVER_THRESHOLD)
                if riv.source:
                    r_pixels[riv.start_xy[0], riv.start_xy[1]] = SOURCE
            else:
                da, aa = self.paint_major_river(riv, r_pixels, p_pixels, last_pid, bname_from_pid)
                major_rivers.append(last_pid)
                def_addenda.append(da)
                adj_addenda.append(aa)
                last_pid += 1
        def_addenda.append(";".join([str(s) for s in [last_pid, *IMPASSABLE, "Ocean", "x", "\n"]]))
        with open(os.path.join(filedir, 'map_data', 'definition.csv'), 'a') as f:
            f.write("".join(def_addenda))
        with open(os.path.join(filedir, 'map_data', 'adjacencies.csv'), 'a') as f:
            f.write("".join(adj_addenda))
            f.write('-1;-1;;-1;-1;-1;-1;-1;')
        if len(adj_addenda) > 0:
            self.save_provinces(filedir)
        self.img_rivers.save(os.path.join(filedir, 'map_data', 'rivers.png'))
        return major_rivers, last_pid

    def paint_edge_crisp(self, start_xy, end_xy, paint, pixels, merge: bool = False, extend=False):
        '''Paint a river segment from start_xy to end_xy. Crisp maps only!
        If extend is true, will continue in the same direction for RIVER_EXTEND pixels.'''
        assert not(merge and extend)  # You should never want to do both.
        if start_xy[1] == end_xy[1]:  # Only horizontal edges are possible.
            extend = RIVER_EXTEND if extend else 0
            # We don't do the last pixel because it would maybe overwrite the next one.
            # Does this actually matter? idk, it should only matter for source, and we'll never do that, maybe.
            # It is important for getting merges right tho.
            direction = 1 if end_xy[0] > start_xy[0] else -1
            dest = end_xy[0] - direction + extend * direction
            for x in range(start_xy[0], dest, direction):
                pixels[x, start_xy[1]] = paint
            if merge:
                pixels[dest, start_xy[1]] = MERGE
            else:
                pixels[dest, start_xy[1]] = paint
        else: # We have an angled edge.
            del_x = (1,0) if end_xy[0] > start_xy[0] else (-1,0)
            del_y = (0,1) if end_xy[1] > start_xy[1] else (0,-1)
            x_dist = abs(end_xy[0] - start_xy[0])
            x_path = [del_x] * x_dist
            y_dist = abs(end_xy[1] - start_xy[1])
            y_path = [del_y] * ( y_dist - 1 )
            # Interleaving the two paths; stolen from Stack Overflow.
            path = [x[1] for x in heapq.merge(zip(count(0, y_dist), x_path), zip(count(0, x_dist), y_path))]
            # We have to end with a vertical path piece, tho!
            path.append(del_y)
            if extend:
                p = x_dist / (x_dist + y_dist)
                for _ in range(RIVER_EXTEND):
                    if random.random() < p:  # big x => high p => add more xs. 
                        path.append(del_x)
                        x_dist += 1
                    else:
                        path.append(del_y)
                        y_dist += 1
            cx, cy = start_xy
            for x,y in path[:-1]:
                pixels[cx, cy] = paint
                cx += x
                cy += y
            if merge:
                pixels[cx, cy] = MERGE
            else:
                pixels[cx, cy] = paint

    def paint_edge_non_crisp(self, start_xy, end_xy, paint, pixels):
        '''Paint a river segment from start_xy to end_xy.'''
        raise NotImplementedError

    def paint_major_river_crisp(self, riv, r_pixels, p_pixels, pid, bname_from_pid):
        '''Paint a major river segment defined by riv. Crisp maps only!'''
        rgb = new_rgb(self.d_cube2rgb)
        self.d_cube2rgb[riv.start_trio] = rgb
        midx = (riv.end_xy[0] + riv.start_xy[0]) // 2
        midy = (riv.end_xy[1] + riv.start_xy[1]) // 2
        if riv.start_xy[1] == riv.end_xy[1]:  # Only horizontal edges are possible.
            direction = 1 if riv.end_xy[0] > riv.start_xy[0] else -1
            for x in range(riv.start_xy[0], riv.end_xy[0] + 1, direction):
                if r_pixels[x, riv.start_xy[1] - 1] == LAND:
                    r_pixels[x, riv.start_xy[1] - 1] = WATER
                if r_pixels[x, riv.start_xy[1]] == LAND:
                    r_pixels[x, riv.start_xy[1]] = WATER
                if r_pixels[x, riv.start_xy[1] + 1] == LAND:
                    r_pixels[x, riv.start_xy[1] + 1] = WATER
                p_pixels[x, riv.start_xy[1] - 1] = rgb
                p_pixels[x, riv.start_xy[1]] = rgb
                p_pixels[x, riv.start_xy[1] + 1] = rgb
            # Figure out which cubes border this river.
            shore1 = (midx, midy + 2)
            shore2 = (midx, midy - 2)
        else: # We have an angled edge.
            del_x = (1,0) if riv.end_xy[0] - riv.start_xy[0] > 0 else (-1,0)
            del_y = (0,1) if riv.end_xy[1] - riv.start_xy[1] > 0 else (0,-1)
            x_dist = abs(riv.end_xy[0] - riv.start_xy[0])
            x_path = [del_x] * x_dist
            y_dist = abs(riv.end_xy[1] - riv.start_xy[1])
            y_path = [del_y] * y_dist
            m_dist =  x_path + y_path
            # Interleaving the two paths; stolen from Stack Overflow.
            path = [x[1] for x in heapq.merge(zip(count(0, y_dist), x_path), zip(count(0, x_dist), y_path))]
            cx, cy = riv.start_xy
            for x,y in path:
                if r_pixels[cx, cy] == LAND:
                    r_pixels[cx, cy] = WATER
                if r_pixels[cx, cy + x] == LAND:
                    r_pixels[cx, cy + x] = WATER
                if r_pixels[cx + y, cy] == LAND:
                    r_pixels[cx + y, cy] = WATER
                p_pixels[cx, cy] = rgb
                p_pixels[cx, cy + x] = rgb
                p_pixels[cx + y, cy] = rgb
                cx += x
                cy += y
            # Figure out which cubes border this river.
            shore1 = (midx + del_x[0] * 2, midy - del_y[1] * 2)
            shore2 = (midx - del_x[0] * 2, midy + del_y[1] * 2)
        def_addendum = ";".join([str(s) for s in [pid, *rgb, riv.name, "x", "\n"]])
        pid1 = self.d_cube2pid[self.pixel_to_cube(*shore1)]
        pid2 = self.d_cube2pid[self.pixel_to_cube(*shore2)]
        comment = f"{pid1}-{pid2}\n"
        # From;To;Type;Through;start_x;start_y;stop_x;stop_y;Comment
        adj_addendum = ";".join([str(s) for s in [pid1, pid2, "sea", pid, shore1[0], shore1[1], shore2[0], shore2[1], comment]])
        return def_addendum, adj_addendum

    def paint_major_river_non_crisp(self, riv, r_pixels, p_pixels, pid, bname_from_pid):
        '''Paint a major river segment defined by riv.'''
        raise NotImplementedError

    def positions(self, bname_from_pid, ocean, filedir):
        '''Create the positions file.'''
        o = self.hex_size // 3
        with open(os.path.join(filedir,"map_data", "positions.txt"), "w") as f:
            for cube, pid in self.d_cube2pid.items():
                if pid in bname_from_pid and cube in self.c2cx and cube in self.c2cy:
                    x, y = self.c2cx[cube], self.c2cy[cube]
                    position = " ".join([str(s) for s in [x + o, y, x, y,  x - o, y, x, y + o, x, y - o]])
                    rotation = " ".join([str(s) for s in [0] * 5])
                    height = " ".join([str(s) for s in [0, 0, 0, 20, 0]])
                    f.write(f"#{bname_from_pid[pid]}\n\t{pid}=\n\t{{\n\t\tposition=\n\t\t{{\n{position} }}\n\t\trotation=\n\t\t{{\n{rotation} }}\n\t\theight=\n\t\t{{\n{height} }}\n\t}}\n")
            f.write("\n")
        obj_types = {
            "building_locators.txt": (o, 0),
            "special_building_locators.txt": (0, 0),
            "siege_locators.txt": (0, -o),
            "combat_locators.txt": (-o, 0),
            "player_stack_locators.txt": (0, o),
        }
        for filename, path in obj_types.items():
            # We don't make this directory because it should have already been made, and the base versions copied in.
            # TODO: Make the base versions here instead?
            used_ocean = set()
            with open(os.path.join(filedir, "gfx", "map", "map_object_data", filename), "a", encoding='utf-8') as outf:
                outf.write("\n")
                dx = path[0]
                dy = path[1]
                if filename != "building_locators.txt" and filename != "special_building_locators.txt":
                    outf.write(f"\t\t{{\n\t\t\tid=0\n\t\t\tposition={{ {self.mid_x} 0.000000 {self.mid_y} }}\n\t\t\trotation={{ -0.000000 -0.000025 -0.000000 1.000000 }}\n\t\t\tscale={{ 1.000000 1.000000 1.000000 }}\n\t\t}}\n")
                for cube, pid in self.d_cube2pid.items():
                    valid = pid in bname_from_pid and cube in self.c2cx and cube in self.c2cy
                    if filename == "player_stack_locators.txt" and cube in ocean and cube in self.c2cx and pid not in used_ocean:
                        valid = True
                        used_ocean.add(pid)
                    if valid:
                        x, y = self.c2cx[cube], self.max_y - self.c2cy[cube]
                        outf.write("\t\t{\n")
                        outf.write(f"\t\t\tid={pid}\n")
                        outf.write(f"\t\t\tposition={{ {x + dx} 0.0 {y + dy} }}\n")
                        outf.write("\t\t\trotation={ 0.0 0.0 0.0 -1.0 }\n")
                        outf.write("\t\t\tscale={ 1.0 1.0 1.0 }\n")
                        outf.write("\t\t}\n")
                outf.write("\t}\n}\n")