# This file is for map-rendering code / file-IO that's game-independent.
from math import sqrt

import perlin_numpy
import PIL.Image

from cube import Cube, Edge, Vertex

# rivers values
LAND_COLOR = 255
SEA_COLOR = 254

def box_from_max(max_x, max_y, n_x, n_y):
    """Compute the box height and box_width."""
    if n_x == 1 or n_y == 1:
        return max_x // 4, max_y // 2
    box_height = max_y // (n_y * 2 - 2)  # TODO: make this divide exactly?
    # There are n_x+1 thin boxes (n_x-1 plus 2 on the edges) and n_x-2 double boxes, so 3n_x-3 total.
    box_width = max_x // (n_x * 3 - 3)   # TODO: make this divide exactly?
    return box_width, box_height


def hor_ver_from_cube(cube):
    hor = cube.x
    ver = - cube.y - hor // 2 - hor % 2
    return hor,ver

def xy_from_cube(cube, box_width, box_height):
    hor, ver = hor_ver_from_cube(cube)
    start_x = (3 * hor - 2) * box_width
    start_y = (2 * ver - 1 + (hor % 2)) * box_height
    return start_x, start_y

def xy_lattice_from_cube(cube, box_width, box_height, lattice_width=2, lattice_height=2):
    """Return a list of evenly hexagonally spaced points lattice_width apart horizontally and lattice_height apart vertically.
    Note this is trying to make a hexagonal lattice, so the distances are more like 2*width and 2*height."""
    min_x, min_y = xy_from_cube(cube, box_width, box_height)
    lattice_points = []
    for ind, dx in enumerate(range(0, box_width*2, lattice_width)):
        offy = lattice_height if ind % 2 == 1 else 0
        for dy in range(offy, min(box_height, (box_width*2-round(dx))*box_height//box_width), lattice_height*2):
            lattice_points.append((min_x+box_width*2+dx, min_y+box_height+dy))
            if dx > 0:
                lattice_points.append((min_x+box_width*2-dx, min_y+box_height+dy))
            if dy > 0:
                lattice_points.append((min_x+box_width*2+dx, min_y+box_height-dy))
            if dx > 0 and dy > 0:
                lattice_points.append((min_x+box_width*2-dx, min_y+box_height-dy))
    return lattice_points


def subset_from_minmax(min_x, max_x, min_y, max_y):
    """Returns the valid cubes between min_x and max_x / min_y and max_y, inclusive."""
    pass

def create_hex_map(rgb_from_ijk, max_x, max_y, n_x, n_y, rgb_from_edge={}, rgb_from_vertex={}, mode='RGB', default="black", palette=None, four_corners=False):
    """Draw a hex map with size (max_x,max_y) with colors from rgb_from_ijk, rgb_from_vertex, and rgb_from_edge. mode determines the image type, and also the correct format for rgb (which should be shared by everything).
    There will be n_x hexes horizontally and n_y hexes vertically.
    rgb_from_edge should be a dictionary from edge to (rgb, thickness) tuples; also, please don't use edges near the map edge.
    rgb_from_vertex should be a dictionary from vertex to rgb."""
    # We have three different positions to track:
    #  - i,j,k of the hex
    #  - hor, ver of the hex: (0,0) to (n_x,n_y), where hor=x and ver=z-y
    #  - x,y of the pixel: really the rectangle or triangle of the underlying section.
    
    # Calculate hex size
    # There are 2n_y-2 vertical boxes.
    box_width, box_height = box_from_max(max_x, max_y, n_x, n_y)
    # We want the edges between hexes to be always uniform. (Later we'll have an option to save this hex-by-hex.)
    # This is more awkward than trusting the triangle function but what are you gonna do
    river_border = [x*box_height//box_width for x in range(box_width)] + [box_height]
    img = PIL.Image.new(mode, (max_x, max_y), default)
    if palette is not None:
        img.putpalette(palette)
    pix = img.load()
    for ijk, rgb in rgb_from_ijk.items():
        hor = ijk[0]
        if hor >= n_x or hor < 0:
            print(ijk, rgb, "out of bounds!")
            continue
        ver = - ijk[1] - hor // 2 - hor % 2
        if ver >= n_y - hor % 2 or ver < 0:
            print(ijk, rgb, "out of bounds!")
            continue
        start_x = (3 * hor - 2) * box_width
        start_y = (2 * ver - 1 + (hor % 2)) * box_height
        # Compute what we actually need to paint for this:            
        if hor == 0:
            center_wrange = range(box_width, box_width*2)
            if ver == 0: # top left
                for x in range(box_width):
                    for y in range(box_height, box_height * 2 - river_border[x]):
                        pix[start_x+box_width*3+x, start_y+y] = rgb
                center_vrange = range(box_height, box_height*2)
            elif ver == n_y - 1: # bottom left
                for x in range(box_width):
                    for y in range(river_border[x], box_height):
                        pix[start_x+box_width*3+x, start_y+y] = rgb
                center_vrange = range(box_height)
                for x in range(2*box_width):  # Go all the way to the bottom edge
                    for y in range(start_y + box_height, max_y):
                        pix[x, y] = rgb
            else: # left edge
                for x in range(box_width):
                    for y in range(river_border[x], box_height * 2 - river_border[x]):
                        pix[start_x+box_width*3+x, start_y+y] = rgb
                center_vrange = range(box_height*2)
        elif hor == n_x - 1:
            center_wrange = range(box_width)
            if ver == 0 and hor % 2 == 0: # top right; if it's even it's the full right side.
                for x in range(box_width):
                    for y in range(box_height, box_height + river_border[x]):
                        pix[start_x+x, start_y+y] = rgb
                center_vrange = range(box_height, box_height*2)
                for x in range(start_x+2*box_width, max_x):  # Go all the way to the edge
                    for y in range(box_height):
                        pix[x, y] = rgb
            elif ver == n_y - 1 and hor % 2 == 0: # bottom right
                for x in range(box_width):
                    for y in range(box_height - river_border[x], box_height):
                        pix[start_x+x, start_y+y] = rgb
                center_vrange = range(box_height)
                for x in range(start_x+2*box_width, max_x):  # Go all the way to the edge
                    for y in range(box_height):
                        pix[x, start_y+y] = rgb
                for x in range(start_x, max_x):
                    for y in range(start_y+box_height, max_y):
                        pix[x, y] = rgb
            else: # right edge
                for x in range(box_width):
                    for y in range(box_height - river_border[x], box_height + river_border[x]):
                        pix[start_x+x, start_y+y] = rgb
                center_vrange = range(box_height*2)
                for x in range(start_x+2*box_width, max_x):  # Go all the way to the edge
                    for y in range(box_height*2):
                        pix[x, start_y+y] = rgb
        elif hor % 2 == 0 and ver == 0:
            for x in range(box_width):
                for y in range(box_height, box_height + river_border[x]):
                    pix[start_x+x, start_y+y] = rgb
            for x in range(box_width):
                for y in(range(box_height, box_height * 2 - river_border[x])):
                    pix[start_x+box_width*3+x, start_y+y] = rgb
            center_wrange = range(box_width*2)
            center_vrange = range(box_height, box_height*2)
        elif hor % 2 == 0 and ver == n_y - 1:
            for x in range(box_width):
                for y in range(box_height - river_border[x], box_height):
                    pix[start_x+x, start_y+y] = rgb
            for x in range(box_width):
                for y in(range(river_border[x], box_height)):
                    pix[start_x+box_width*3+x, start_y+y] = rgb
            center_wrange = range(box_width*2)
            center_vrange = range(box_height)
            for x in range(4*box_width):  # Go all the way to the bottom edge
                for y in range(start_y + box_height, max_y):
                    pix[start_x+x, y] = rgb
        else:
            for x in range(box_width):
                for y in range(box_height - river_border[x], box_height + river_border[x]):
                    pix[start_x+x, start_y+y] = rgb
            for x in range(box_width):
                for y in(range(river_border[x], box_height * 2 - river_border[x])):
                    pix[start_x+box_width*3+x, start_y+y] = rgb
            center_wrange = range(box_width*2)
            center_vrange = range(box_height*2)
            if ver == n_y - 2 and hor % 2 == 1:  # Go all the way to the bottom edge    
                for x in range(box_width, 3*box_width):
                    for y in range(start_y + 2*box_height, max_y):
                        pix[start_x+x, y] = rgb
        #Paint the center boxes. This could be a drawn rectangle but w/e
        for x in center_wrange:
            for y in center_vrange:
                pix[start_x + box_width + x,start_y + y] = rgb
    if four_corners:
        for ver in range(1,max_y):
            if (0,-ver,ver) in rgb_from_ijk:
                pix[0, (2 * ver - 1) * box_height-1] = rgb_from_ijk[(0,-ver,ver)]
    for edge, (rgb, thickness) in rgb_from_edge.items():
        # The edges that get painted are the south (0), southeast (1), and northeast edges (2).
        # This currently doesn't check that the edges are actually on-map, which it probably should? These are not supposed to be populated near the edge.
        start_x, start_y = xy_from_cube(edge.cube, box_width=box_width, box_height=box_height)
        y_down = thickness // 2
        y_up = thickness - y_down
        # TODO: Make it so edges never try to paint the same pixels?
        if edge.rot == 0:
            # If thickness == 1 this should just be the southernmost pixels of the hex.
            for x in range(start_x + box_width, start_x + box_width * 3 + 1):  # The +1 is because the right-most pixel is generally actually painted by the triangles; but with an impassable mountain / major river, we want to block the connection.
                for y in range(start_y + box_height * 2 - y_down - 1, start_y + box_height * 2 + y_up - 1):
                    pix[x, y] = rgb
        elif edge.rot == 1:
            for x in range(box_width):
                for y in range(start_y + max(box_height - 1, box_height * 2 - river_border[x + 1] - y_up), start_y + box_height * 2 - river_border[x] + y_down):  # up and down are flipped to better match the borders. Note also there can be a four-corners situation here, so box_height-1.
                    pix[start_x + box_width * 3 + x, y] = rgb
        elif edge.rot == 2:
            for x in range(box_width):
                for y in range(start_y + river_border[x] - y_down, start_y + min(box_height,river_border[x + 1] + y_up)):
                    pix[start_x + box_width * 3 + x, y] = rgb
    for vertex, rgb in rgb_from_vertex.items():
        if isinstance(vertex, Vertex):
            # The vertices that get painted are the west (-1), center (0), and eastern vertices (1).
            start_x, start_y = xy_from_cube(vertex.cube, box_width=box_width, box_height=box_height)
            start_y -= 1  # This is to line it up with the southernmost edge instead of the northernmost edge.
            start_x -= vertex.rot == 1
            pix[start_x + (1 + vertex.rot) * 2 * box_width, start_y + box_height] = rgb
        elif isinstance(vertex, tuple):
            fr,to = vertex
            assert isinstance(fr, Vertex) and isinstance(to, Vertex)
            start_x, start_y = xy_from_cube(to.cube, box_width=box_width, box_height=box_height)
            o_x, o_y = xy_from_cube(fr.cube, box_width=box_width, box_height=box_height)
            if start_y == o_y:
                start_x += 1 if start_x < o_x else -1
            else:
                start_y += 1 if start_y < o_y else -1
            start_y -= 1  # This is to line it up with the southernmost edge instead of the northernmost edge.
            start_x -= to.rot == 1
            pix[start_x + (1 + to.rot) * 2 * box_width, start_y + box_height] = rgb
    return img


def calc_bary(box_width, box_height):
    """Calculates the barycentric triangles for a triangle with base 2*box_width and height box_height; returns a tuple of the up-triangle and the down-triangle."""
    river_border = [x*box_height//box_width for x in range(box_width)] + [box_height]
    # It is the same triangle everywhere, so we can compute once the barycentric ratios for all the pixels in the triangle.
    bary_up = {}
    bary_down = {}
    denom = (2. * box_width * box_height)
    for x in range(2*box_width):
        for y in range(river_border[-min(x,2*box_width-x)-1], box_height):
            dy = (y - box_height + 1)
            beta = (x*box_height + box_width*dy) / denom
            gamma = 2*box_width*dy / -denom
            alpha = 1-beta-gamma
            bary_up[(x,y)] = (gamma,alpha,beta)
    for x in range(2*box_width):
        for y in range(river_border[min(x,2*box_width-x)]):
            beta = (x*box_height - box_width*y) / denom
            gamma = 2*box_width*y / denom
            alpha = 1-beta-gamma
            bary_down[(x,y)] = (gamma,alpha,beta)
    return bary_up, bary_down


def create_tri_map(height_from_vertex, max_x, max_y, n_x, n_y, mode='L', default="black", palette=None):
    """Creates a map out of triangular patches, each defined by three adjacent vertices in height_from_vertex."""
    box_width, box_height = box_from_max(max_x, max_y, n_x, n_y)
    # It is the same triangle everywhere, so we can compute once the barycentric ratios for all the pixels in the triangle.
    bary_up, bary_down = calc_bary(box_width, box_height)
    img = PIL.Image.new(mode, (max_x, max_y), default)
    if palette is not None:
        img.putpalette(palette)
    pix = img.load()
    for vertex, z in height_from_vertex.items():
        # There are two types of triangles: pointing-up and pointing-down.
        # For each vertex, we check whether its two mates (up or down) exist, and if so, draw that triangle.
        start_x, start_y = xy_from_cube(vertex.cube, box_width=box_width, box_height=box_height)
        start_x += (2*vertex.rot + 1)*box_width  # Offset based on which is the center.
        for ind, (bary, pair) in enumerate([(bary_down, vertex.down_pair()), (bary_up, vertex.up_pair())]):
            ok = True
            l, r = pair
            if l in height_from_vertex:
                zl = height_from_vertex[l]
            else:
                ok = False
            if r in height_from_vertex:
                zr = height_from_vertex[r]
            else:
                ok = False
            if ok:
                start_y += ind * box_height
                for (x,y), (a,b,c) in bary.items():
                    pix[start_x + x, start_y + y] = int(z * a + zl * b + zr * c)
    return img


def create_noise_map(base_from_vertex, mask_from_vertex, max_x, max_y, n_x, n_y, mask_max, mode='L', default="black", palette=None):
    """Similar to create_tri_map but using mask_from_vertex to determine how much of a shared noise source to use.
    Ensure that mask_from_vertex has elements wherever base_from_vertex does."""
    noise = mask_max * (1 - abs(perlin_numpy.generate_fractal_noise_2d((max_x, max_y), (max_x//32, max_y//32), octaves=5)))
    box_width, box_height = box_from_max(max_x, max_y, n_x, n_y)
    # It is the same triangle everywhere, so we can compute once the barycentric ratios for all the pixels in the triangle.
    bary_up, bary_down = calc_bary(box_width, box_height)
    img = PIL.Image.new(mode, (max_x, max_y), default)
    if palette is not None:
        img.putpalette(palette)
    pix = img.load()
    for vertex, z in base_from_vertex.items():
        # There are two types of triangles: pointing-up and pointing-down.
        # For each vertex, we check whether its two mates (up or down) exist, and if so, draw that triangle.
        start_x, start_y = xy_from_cube(vertex.cube, box_width=box_width, box_height=box_height)
        start_x += (2*vertex.rot + 1)*box_width  # Offset based on which is the center.
        for ind, (bary, pair) in enumerate([(bary_down, vertex.down_pair()), (bary_up, vertex.up_pair())]):
            ok = True
            m = mask_from_vertex[vertex]
            l, r = pair
            if l in base_from_vertex:
                zl = base_from_vertex[l]
                ml = mask_from_vertex[l]
            else:
                ok = False
            if r in base_from_vertex:
                zr = base_from_vertex[r]
                mr = mask_from_vertex[r]
            else:
                ok = False
            if ok:
                start_y += ind * box_height
                for (x,y), (a,b,c) in bary.items():
                    pix[start_x + x, start_y + y] = min(255, int(z * a + zl * b + zr * c + max(0, m * a + ml * b + mr * c) * noise[start_x+x,start_y+y]))
    return img


def create_normal(heightmap):
    """Given heightmap (a PIL.Image), return an image that's the normal vector for heightmap."""
    max_x, max_y = heightmap.size
    wono = PIL.Image.new(mode="RGB", size=heightmap.size, color="black")
    bpix = heightmap.load()
    wpix = wono.load()
    for x in range(max_x):
        for y in range(max_y):
            xComp = min(11,max(-11, bpix[max(0,x-1),y]-bpix[min(max_x-1, x+1),y]))
            yComp = min(11,max(-11, bpix[x,max(0,y-1)]-bpix[x,min(max_y-1, y+1)]))
            xComp *= abs(xComp)
            yComp *= abs(yComp)
            zComp = sqrt(max(0,127*127 - xComp*xComp - yComp*yComp))
            wpix[x,y] = (int(xComp + 128), int(yComp + 128), int(zComp + 128))
    return wono

def closest_xy(fr, to, box_height, box_width, shrinkage=2):
    """Rather than the strict closest x,y position, this function returns either
    - the midpoint of the edge for all hexes that are in a straight line (shrunk a few pixels towards the center)
    - the closest corner for all hexes in the wedge between straight lines (shrunk a few pixels towards the center)"""
    hor = fr.x
    ver = -fr.y - hor % 2 - hor // 2
    # Compute the center of the from hex
    start_x = (3 * hor) * box_width
    start_y = (2 * ver + (hor % 2)) * box_height
    # Compute the direction
    # I'm just going to do the 12-way splitting.
    if to.x > fr.x:  # ne wedge, ne line, e wedge, se line, se wedge
        if to.y == fr.y:  # ne line
            return (start_x + 3 * box_width // 2 - shrinkage, start_y - box_height // 2)
        elif to.z == fr.z: # se line
            return (start_x + 3 * box_width // 2- shrinkage, start_y + box_height // 2)
        elif to.y < fr.y and to.z < fr.z: # e wedge
            return (start_x + 2 * box_width - shrinkage, start_y)
        elif to.y < fr.y and to.z > fr.z: # se wedge
            return (start_x + box_width - shrinkage, start_y + box_height - shrinkage)
        else: # ne wedge
            return (start_x + box_width - shrinkage, start_y - box_height + shrinkage)
    elif to.x == fr.x:  # n line, s line
        if to.y > fr.y:
            return (start_x, start_y - box_height + shrinkage)
        else:
            return (start_x, start_y + box_height - shrinkage)
    else:  # nw wedge, nw line, w wedge, sw line, sw wedge
        if to.y == fr.y:  # sw line
            return (start_x - 3 * box_width // 2 + shrinkage, start_y + box_height // 2)
        elif to.z == fr.z: # nw line
            return (start_x - 3 * box_width // 2 + shrinkage, start_y - box_height // 2)
        elif to.y > fr.y and to.z > fr.z: # w wedge
            return (start_x - 2 * box_width + shrinkage, start_y)
        elif to.y < fr.y and to.z > fr.z: # sw wedge
            return (start_x - box_width + shrinkage, start_y + box_height - shrinkage)
        else: # nw wedge
            return (start_x - box_width + shrinkage, start_y - box_height + shrinkage)


def get_palette(base_loc):
    """Pulls out the palette from an image"""
    return PIL.Image.open(base_loc).palette


def valid_cubes(n_x=235, n_y=72):
    """Construct the list of on-map cube positions."""
    cube_list = []
    for hor in range(n_x):
        hor2 = hor//2
        if hor % 2 == 1:
            current = Cube(hor, -hor2-1, -hor2+0)
            max_ver = n_y-1
        else:
            current = Cube(hor, -hor2, -hor2)
            max_ver = n_y
        for ver in range(max_ver):
            cube_list.append(current)
            current = current.add(Cube(0,-1,1)) # Move down
    return cube_list
