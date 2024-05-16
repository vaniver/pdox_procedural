from collections import defaultdict

from cube import Cube

class Area:
    def __init__(self, cid, members):
        """Each area has a area id (cid) and a set of cubes that are members.
        I will often assume that areas are contiguous but that isn't enforced."""
        self.cid = cid
        self.members = list(members)
        self.outside = False  # This was going to be to measure whether or not the chunk is on the outside of the map but idk if we care about this ever.
        self._boundary = None
        self.self_edges = {}
        self.other_edges = {}
        self._cols = None
        self.min_x, self.min_y, self.min_z = (999,999,999)
        self.max_x, self.max_y, self.max_z = (-999,-999,-999)

    def __contains__(self, other):
        """Checks whether a cube is in self.members, or if a list of cubes is supplied, whether all of them are."""
        if isinstance(other, Cube):
            return other in self.members
        elif isinstance(other, list):
            return all([el in self for el in other])
        else:
            return False
    
    @property
    def boundary(self):
        if self._boundary is None:
            self.calc_boundary()
        return self._boundary

    def calc_boundary(self):
        """Calculates boundary, the set of cubes that border another area, _including_ the map edge.
        Doesn't compute self_edges or other_edges."""
        self._boundary = set()
        for member in self.members:
            if len([other for other in member.neighbors() if other not in self.members]) > 0:
                self._boundary.add(member)

    def calc_edges(self, cid_from_cube):
        """Calculates boundary, the set of cubes that border another area (not including the map edge!),
        self_edges, a dictionary that maps from other cids to all cubes that border that cid,
        other_edges, a dictionary that maps from other cids to all cubes in the other area that border this one."""
        self._boundary = set()
        self.self_edges = {}
        self.other_edges = {}
        for member in self.members:
            others = [other for other in member.neighbors() if other not in self.members and other in cid_from_cube]
            if not all([other in cid_from_cube for other in member.neighbors()]):
                self.outside = True
            for other in others:  # Note this will skip if it's an empty list
                self._boundary.add(member)
                ocid = cid_from_cube[other]
                if cid_from_cube[other] in self.self_edges:
                    self.self_edges[ocid].add(member)
                    self.other_edges[ocid].add(other)
                else:
                    self.self_edges[ocid] = set([member])
                    self.other_edges[ocid] = set([other])

    def calc_bounding_hex(self):
        """Calculates the x,y,z lines that bound (inclusively) the area."""
        self.min_x, self.min_y, self.min_z = (999,999,999)
        self.max_x, self.max_y, self.max_z = (-999,-999,-999)
        for member in self.members:
            self.max_x = max(self.max_x, member.x)
            self.max_y = max(self.max_y, member.y)
            self.max_z = max(self.max_z, member.z)
            self.min_x = min(self.min_x, member.x)
            self.min_y = min(self.min_y, member.y)
            self.min_z = min(self.min_z, member.z)

    def bounding_hex_interior(self, extra=0, ignore={}):
        self.calc_bounding_hex()
        result = []
        for x in range(self.min_x-extra, self.max_x+1+extra):
            for y in range(self.min_y-extra, self.max_y+1+extra):
                if self.min_z-extra <= -x-y <= self.max_z+extra:
                    k = Cube(x,y,-x-y)
                    if k not in ignore:
                        result.append(k)
        return result

    @property
    def cols(self):
        if self._cols is None:
            xs = defaultdict(set)
            ys = defaultdict(set)
            zs = defaultdict(set)
            for cub in self.members:
                xs[cub.x].add(cub.y)
                ys[cub.y].add(cub.z)
                zs[cub.z].add(cub.x)
            xs = {x: (min(y), max(y)) for x, y in xs.items()}
            ys = {y: (min(z), max(z)) for y, z in ys.items()}
            zs = {z: (min(x), max(x)) for z, x in zs.items()}
            self._cols = xs, ys, zs
        return self._cols

    def corners(self, extra = 0):
        '''Returns the 6 corners of the BoundingHex, in adjacent clockwise order starting at the top. Use extra to increase the size of the bounding box.'''
        return [Cube(0-self.max_y-self.min_z, self.max_y + extra, self.min_z - extra), Cube(self.max_x + extra, 0-self.max_x-self.min_z, self.min_z - extra),
                Cube(self.max_x + extra, self.min_y - extra, 0-self.max_x-self.min_y), Cube(0-self.min_y-self.max_z, self.min_y - extra, self.max_z + extra),
                Cube(self.min_x - extra, 0-self.min_x-self.max_z, self.max_z + extra), Cube(self.min_x - extra, self.max_y + extra, 0-self.min_x-self.max_y)]

    def in_bounding_hex(self, other):
        """Checks whether or not a cube is inside the bounding hex of this area.
        Will return True for any sensible input if calc_bounding_hex has not been called yet."""
        if other.x < self.min_x:
            return False
        if other.x > self.max_x:
            return False
        if other.y < self.min_y:
            return False
        if other.y > self.max_y:
            return False
        if other.z < self.min_z:
            return False
        if other.z > self.max_z:
            return False
        return True
    
    def min_dist(self, other):
        """Computes the minimum distance between an element of self.boundary and other.
        other can be a Cube, list of Cubes, or Area (make sure boundary is computed!)."""
        if isinstance(other, Cube):
            return min([m.sub(other).mag() for m in self.boundary])
        elif isinstance(other, list):
            return min([min([m.sub(o).mag() for m in self.boundary]) for o in other])
        elif isinstance(other, Area):
            dist = 100000000
            for sc, oc in zip(self.cols, other.cols):
                for v in sc.keys():
                    if v not in oc:
                        continue
                    d = min([abs(s - o) for s in sc[v] for o in oc[v]])
                    dist = min(dist, d)
                    # Cant get less than zero
                    if dist == 0:
                        return 0
            if dist == 100000000:
                return min([min([m.sub(o).mag() for m in self.boundary]) for o in other.boundary])
            return dist
        else:
            return NotImplementedError
        
    def best_corner(self, angle):
        if len(self.boundary) == 0:
            self.calc_boundary()
        cdist = [self.min_dist(el) for el in self.corners()]
        corner_idx = cdist.index(max(cdist))
        rotation = (angle - corner_idx) % 6
        origin = self.corners(extra=1)[corner_idx].rotate_right(3+rotation)
        return (origin, rotation)
        
    
    def count_straits(self, other):
        """Computes the number of possible straits between self and other.
        Note that single provinces which have multiple possible straits will count each separately.
        other can be a Cube, list of Cubes, or Area (make sure boundary is computed!)."""
        return len(self.find_straits(other))
        
    def find_straits(self, other):
        """Returns all possible straits between self and other. The return is a list of tuples of cube pairs that are straits.
        Note that single provinces which have multiple possible straits will count each separately.
        other can be a Cube, list of Cubes, or Area (make sure boundary is computed!)."""
        if isinstance(other, Cube):
            return [(m, other) for m in self.boundary if m in other.strait_neighbors()]
        elif isinstance(other, list):
            return [(m, o) for m in self.boundary for o in other if m in o.strait_neighbors()]
        elif isinstance(other, Area):
            return [(m, o) for m in self.boundary for o in other.boundary if m in o.strait_neighbors()]
        else:
            return NotImplementedError


    def calc_average(self):
        """returns the (integer-valued) average cube of the area."""
        total_x, total_y = (0,0)  # z is determined by x/y
        for member in self.members:
            total_x += member.x
            total_y += member.y
        avg_x = total_x // len(self.members)
        avg_y = total_y // len(self.members)
        return Cube(avg_x, avg_y, -avg_x-avg_y)

    def rectify(self, other=None):
        """Replaces self.members with one that is shifted by other. (If none is supplied, use the area's average.)
        Make sure to recalculate any derived properties you would like to use (like boundary or bounding_hex)."""
        if other is None:
            other = self.calc_average()
        self.members = [k.sub(other) for k in self.members]
        self._boundary = None

    def rotate(self, rot=0):
        """Rotates all cubes in self.members right by rot; consider rectifying first."""
        self.members = [k.rotate_right(rot) for k in self.members]
        self._boundary = None

    def add(self, other):
        assert isinstance(other, Cube)
        return Area(self.cid, [k.add(other) for k in self.members])

    def __add__(self, other):
        return self.add(other)

    def translate(self, other=Cube(0,0,0)):
        """Moves all cubes in self.members by adding other."""
        self.members = [k.add(other) for k in self.members]
        self._boundary = None

    def __hash__(self):
        return hash(tuple(self.members))
