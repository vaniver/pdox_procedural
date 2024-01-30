# This file is for map-rendering code / file-IO that's game-independent.


import PIL.Image

from cube import Cube

def create_hex_map(rgb_from_ijk, max_x, max_y, mode='RGB', default="black", n_x=235, n_y=72):
    """Draw a hex map with size (max_x,max_y) with colors from rgb_from_ijk.
    There will be n_x hexes horizontally and n_y hexes vertically. 
    n_x will be assumed odd and n_y is assumed even (to have split hexes in all corners)."""
    # We have three different positions to track:
    #  - i,j,k of the hex
    #  - hor, ver of the hex: (0,0) to (n_x,n_y), where hor=x and ver=z-y
    #  - x,y of the pixel: really the rectangle or triangle of the underlying sector.
    
    # Calculate hex size
    # There are 2n_y-2 vertical boxes.
    assert n_x % 2 == 1
    box_height = max_y // (n_y * 2 - 2)  # TODO: make this divide exactly?
    # There are n_x+1 thin boxes (n_x-1 plus 2 on the edges) and n_x-2 double boxes, so 3n_x-3 total.
    box_width = max_x // (n_x * 3 - 3)   # TODO: make this divide exactly?
    # We want the edges between hexes to be always uniform. (Later we'll have an option to save this hex-by-hex.)
    # This is more awkward than trusting the triangle function but what are you gonna do
    river_border = [x*box_height//box_width for x in range(box_width)]
    img = PIL.Image.new(mode, (max_x,max_y), default)
    pix = img.load()
    # try:
    for hor in range(n_x):
        # Calculate starting position
        hor2 = hor//2
        if hor % 2 == 1:
            current = Cube(hor, -hor2-1, -hor2+0)
            max_ver = n_y-1
        else:
            current = Cube(hor, -hor2, -hor2)
            max_ver = n_y
        for ver in range(max_ver):
            rgb = rgb_from_ijk[current.tuple()]
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
                else: # left edge
                    for x in range(box_width):
                        for y in range(river_border[x], box_height * 2 - river_border[x]):
                            pix[start_x+box_width*3+x, start_y+y] = rgb
                    center_vrange = range(box_height*2)
            elif hor == n_x - 1:
                center_wrange = range(box_width)
                if ver == 0: # top right                    
                    for x in range(box_width):
                        for y in range(box_height, box_height + river_border[x]):
                            pix[start_x+x, start_y+y] = rgb
                    center_vrange = range(box_height, box_height*2)
                elif ver == n_y - 1: # bottom right
                    for x in range(box_width):
                        for y in range(box_height - river_border[x], box_height):
                            pix[start_x+x, start_y+y] = rgb
                    center_vrange = range(box_height)
                else: # right edge
                    for x in range(box_width):
                        for y in range(box_height - river_border[x], box_height + river_border[x]):
                            pix[start_x+x, start_y+y] = rgb
                    center_vrange = range(box_height*2)
            elif hor % 2 == 0 and ver == 0:
                for x in range(box_width):
                    for y in range(box_height, box_height + river_border[x]):
                        pix[start_x+x, start_y+y] = rgb
                for x in range(box_width):
                    for y in(range(box_height, box_height * 2 - river_border[x])):
                        pix[start_x+box_width*3+x, start_y+y] = rgb
                center_wrange = range(box_width*2)
                center_vrange = range(box_height, box_height*2)
            elif hor % 2 == 0 and ver == max_ver - 1:
                for x in range(box_width):
                    for y in range(box_height - river_border[x], box_height):
                        pix[start_x+x, start_y+y] = rgb
                for x in range(box_width):
                    for y in(range(river_border[x], box_height)):
                        pix[start_x+box_width*3+x, start_y+y] = rgb
                center_wrange = range(box_width*2)
                center_vrange = range(box_height)
            else:
                for x in range(box_width):
                    for y in range(box_height - river_border[x], box_height + river_border[x]):
                        pix[start_x+x, start_y+y] = rgb
                for x in range(box_width):
                    for y in(range(river_border[x], box_height * 2 - river_border[x])):
                        pix[start_x+box_width*3+x, start_y+y] = rgb
                center_wrange = range(box_width*2)
                center_vrange = range(box_height*2)
            #Paint the center boxes. This could be a drawn rectangle but w/e
            for x in center_wrange:
                for y in center_vrange:
                    pix[start_x + box_width + x,start_y + y] = rgb
            # Move to the next one
            current = current.add(Cube(0,-1,1)) # Move down
    return img

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
            return (start_x + 3*box_width // 2 - shrinkage, start_y - box_height // 2)
        elif to.z == fr.z: # se line
            return (start_x + 3*box_width // 2- shrinkage, start_y + box_height // 2)
        elif to.y < fr.y and to.z < fr.z: # e wedge
            return (start_x + 2*box_width - shrinkage, start_y)
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
            return (start_x - 3*box_width // 2 + shrinkage, start_y + box_height // 2)
        elif to.z == fr.z: # nw line
            return (start_x - 3*box_width // 2 + shrinkage, start_y - box_height // 2)
        elif to.y > fr.y and to.z > fr.z: # w wedge
            return (start_x - 2*box_width + shrinkage, start_y)
        elif to.y < fr.y and to.z > fr.z: # sw wedge
            return (start_x - box_width + shrinkage, start_y + box_height - shrinkage)
        else: # nw wedge
            return (start_x - box_width + shrinkage, start_y - box_height + shrinkage)


def valid_cubes(n_x=235, n_y=72):
    """Construct the list of on-map cube positions."""
    assert n_x % 2 == 1
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


def add_rivers(img, river_from_trio):
    """Given a map,"""
    pass