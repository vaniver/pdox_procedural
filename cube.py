# This file is for the 'cube', or coordinates in the hex system, which is game-independent.

from typing import List, Set

class Cube:
    def __init__(self, x=0, y=0, z=0):
        if type(x) == Cube:
            self.x = x.x
            self.y = x.y
            self.z = x.z
        elif type(x) == tuple:
            self.x = x[0]
            self.y = x[1]
            self.z = x[2]
        elif (x+y+z == 0):
            self.x = x
            self.y = y
            self.z = z
        else:
            raise ValueError('x,y,z: '+','.join((str(x),str(y),str(z))))
            
    
    def add(self, other):
        return Cube(self.x+other.x, self.y+other.y, self.z+other.z)
        
    def sub(self, other):
        return Cube(self.x-other.x, self.y-other.y, self.z-other.z)
        
    def mag(self):
        return max(abs(self.x), abs(self.y), abs(self.z))

    def nbr(self, other):
        return self.sub(other).mag() == 1

    def dot(self, other):
        return (self.x * other.x + self.y * other.y + self.z * other.z)
    
    def dist(self, other):
        return max(abs(self.x-other.x), abs(self.y-other.y), abs(self.z-other.z))

    def avg(self, other):
        x = (self.x+other.x)//2
        y = (self.y+other.y)//2
        return Cube(x, y, -x-y)
    
    def add_in_place(self, other):
        self.x = self.x+other.x
        self.y = self.y+other.y
        self.z = self.z+other.z
        
    def rotate_right(self, num):
        if num % 6 == 0:
            return Cube(self.x, self.y, self.z)
        if num % 6 == 1:
            return Cube(-self.z, -self.x, -self.y)
        elif num % 6 == 2:
            return Cube( self.y,  self.z,  self.x)
        elif num % 6 == 3:
            return Cube(-self.x, -self.y, -self.z)
        elif num % 6 == 4:
            return Cube( self.z,  self.x,  self.y)
        else: #elif num % 6 == 5:
            return Cube(-self.y, -self.z, -self.x)
            
    def rotate_right_in_place(self, num):
        if num % 6 == 0:
            pass
        elif num % 6 == 1:
            (self.x,self.y,self.z) = (-self.z, -self.x, -self.y)
        elif num % 6 == 2:
            (self.x,self.y,self.z) = ( self.y,  self.z,  self.x)
        elif num % 6 == 3:
            (self.x,self.y,self.z) = (-self.x, -self.y, -self.z)
        elif num % 6 == 4:
            (self.x,self.y,self.z) = ( self.z,  self.x,  self.y)
        else: #elif num % 6 == 5:
            (self.x,self.y,self.z) = (-self.y, -self.z, -self.x)

    def big(self):
        '''This returns the largest magnitude element of self.'''
        if abs(self.x) >= abs(self.y) and abs(self.x) >= abs(self.z):
            return self.x
        elif abs(self.y) >= abs(self.x) and abs(self.y) >= abs(self.z):
            return self.y
        else:
            return self.z

    def point(self):
        '''Whether or not the triangle defined by the trio which created this direction points left.'''
        return self.big() > 0
            
    def tuple(self):
        return (self.x, self.y, self.z)

    def __str__(self):
        return str(self.x)+", "+str(self.y)+", "+str(self.z)
        
    def __repr__(self):
        return f"Cube({self.x}, {self.y}, {self.z})"

    def __le__(self, other):
        return self.mag() <= other.mag()
    
    def __lt__(self, other):
        return self.mag() < other.mag()

    def __eq__(self, other):
        if isinstance(other, Cube):
            return (self.x == other.x) and (self.y == other.y) and (self.z == other.z)
        else:
            return False
            
    def __ne__(self, other):
        return not self.__eq__(other)
        
    def __hash__(self):
        return hash(tuple((self.x, self.y, self.z)))
        
    def neighbors(self) -> Set['Cube']:
        return {Cube(self.x+1,self.y,self.z-1), Cube(self.x,self.y+1,self.z-1),
                Cube(self.x-1,self.y+1,self.z), Cube(self.x-1,self.y,self.z+1),
                Cube(self.x,self.y-1,self.z+1), Cube(self.x+1,self.y-1,self.z)}
        
    def ordered_neighbors(self) -> List['Cube']:
        """In counterclockwise order, starting with ENE."""
        return [Cube(self.x+1,self.y,self.z-1), Cube(self.x,self.y+1,self.z-1),
                Cube(self.x-1,self.y+1,self.z), Cube(self.x-1,self.y,self.z+1),
                Cube(self.x,self.y-1,self.z+1), Cube(self.x+1,self.y-1,self.z)]
    
    def ordered_strait_neighbors(self) -> List['Cube']:
        """In a weird order, flipping before rotating."""
        return [Cube(self.x+1,self.y-2,self.z+1), Cube(self.x-1,self.y+2,self.z-1),
                Cube(self.x+1,self.y+1,self.z-2), Cube(self.x-1,self.y-1,self.z+2),
                Cube(self.x+2,self.y-1,self.z-1), Cube(self.x-2,self.y+1,self.z+1)]
    
    def strait_neighbors(self) -> Set['Cube']:
        return {Cube(self.x+1,self.y-2,self.z+1), Cube(self.x-1,self.y+2,self.z-1),
                Cube(self.x+1,self.y+1,self.z-2), Cube(self.x-1,self.y-1,self.z+2),
                Cube(self.x+2,self.y-1,self.z-1), Cube(self.x-2,self.y+1,self.z+1)}

    def valid_straits(self, land_cubes, sea_cubes):
        buffer = []
        for rot in range(6):
            a = Cube(1,-1, 0).rotate_right(rot)
            b = Cube(1, 0,-1).rotate_right(rot)
            ka = self.add(a)
            if ka not in sea_cubes:
                continue
            kb = self.add(b)
            if kb not in sea_cubes:
                continue
            kab = ka.add(b)
            if kab not in land_cubes:
                continue
            buffer.append((kab, ka, kb))
        return buffer

    def foursome(self, other):
        '''Given another hex (that a strait neighbor), return the two trios to find the closest vertices.'''
        # Note that the pair included in each trio should be equivalent to:
        #   [c for c in self.neighbors() if c in other.neighbors()]
        #   But this implementation is (I hope) faster.
        try:
            s_index = self.ordered_strait_neighbors().index(other)
            if s_index == 0:
                return ((self, Cube(self.x,self.y-1,self.z+1), Cube(self.x+1,self.y-1,self.z)),
                        (other, Cube(self.x,self.y-1,self.z+1), Cube(self.x+1,self.y-1,self.z)))
            elif s_index == 1:
                return ((self, Cube(self.x,self.y+1,self.z-1), Cube(self.x-1,self.y+1,self.z)),
                        (other, Cube(self.x,self.y+1,self.z-1), Cube(self.x-1,self.y+1,self.z)))
            elif s_index == 2:
                return ((self, Cube(self.x,self.y+1,self.z-1), Cube(self.x+1,self.y,self.z-1)),
                        (other, Cube(self.x,self.y+1,self.z-1), Cube(self.x+1,self.y,self.z-1)))
            elif s_index == 3:
                return ((self, Cube(self.x,self.y-1,self.z+1), Cube(self.x-1,self.y,self.z+1)),
                        (other, Cube(self.x,self.y-1,self.z+1), Cube(self.x-1,self.y,self.z+1)))
            elif s_index == 4:
                return ((self, Cube(self.x+1,self.y,self.z-1), Cube(self.x+1,self.y-1,self.z)),
                        (other, Cube(self.x+1,self.y,self.z-1), Cube(self.x+1,self.y-1,self.z)))
            elif s_index == 5:
                return ((self, Cube(self.x-1,self.y,self.z+1), Cube(self.x-1,self.y+1,self.z)),
                        (other, Cube(self.x-1,self.y,self.z+1), Cube(self.x-1,self.y+1,self.z)))
            else:
                raise NotImplementedError
        except:
            raise ValueError(f"{other} is not a strait neighbor for {self}.")


    def valid(self, other) -> bool:
        '''Checks to make sure this cube is in the sector (third) defined by other.'''
        if (other.x < 0 and self.x >= 0): return False 
        if (other.x > 0 and self.x <= 0): return False 
        if (other.y < 0 and self.y >= 0): return False 
        if (other.y > 0 and self.y <= 0): return False 
        if (other.z < 0 and self.z >= 0): return False 
        if (other.z > 0 and self.z <= 0): return False 
        return True
        
    def flip(self, valid_dir) -> 'Cube':
        if valid_dir.x == 0:
            return Cube(-self.x, -self.z, -self.y)
        elif valid_dir.y == 0:
            return Cube(-self.z, -self.y, -self.x)
        elif valid_dir.z == 0:
            return Cube(-self.y, -self.x, -self.z)
        else:
            raise ValueError('Need a 0 el. x,y,z: '+','.join((str(self.x),str(self.y),str(self.z))))
    
    def flip_in_place(self, valid_dir):
        if valid_dir.x == 0:
            temp = self.y
            self.y = -self.z
            self.z = -temp
            self.x = -self.x
        elif valid_dir.y == 0:
            temp = self.x
            self.x = -self.z
            self.z = -temp
            self.y = -self.y
        elif valid_dir.z == 0:
            temp = self.y
            self.y = -self.x
            self.x = -temp
            self.z = -self.z
        else:
            raise ValueError('Need a 0 el. x,y,z: '+','.join((str(valid_dir.x),str(valid_dir.y),str(valid_dir.z))))
        
class Edge:
    def __init__(self, cube, rot, dir=None):
        """Edge is a cube and a rotation: 0, for the flat southern edge; 1, for the southeastern edge; 2, for the northeastern edge.
        The optional dir is +1 for counter-clockwise and -1 for clockwise."""
        self.cube = cube
        assert rot in [0,1,2]
        self.rot = rot
        self.dir = dir

    def adj_edges(self):
        """Returns the list of four adjacent edges.
        If the edge is directional, the from edge pair will be first and the to edge pair will be second."""
        if self.dir is None:
            if self.rot == 0:
                return [
                    Edge(self.cube.add(Cube(-1, 0, 1)), 2),
                    Edge(self.cube.add(Cube(-1, 0, 1)), 1),
                    Edge(self.cube.add(Cube(0, -1, 1)), 2),
                    Edge(self.cube, 1),
                    ]
            elif self.rot == 1:
                return [
                    Edge(self.cube, 0),
                    Edge(self.cube.add(Cube(0, -1, 1)), 2),
                    Edge(self.cube, 2),
                    Edge(self.cube.add(Cube(1, 0, -1)), 0),
                    ]
            else:  # self.rot == 2
                return [
                    Edge(self.cube, 1),
                    Edge(self.cube.add(Cube(1, 0, -1)), 0),
                    Edge(self.cube.add(Cube(0, 1, -1)), 0),
                    Edge(self.cube.add(Cube(0, 1, -1)), 1),
                    ]
        elif self.dir == 1:
            if self.rot == 0:
                return [
                    Edge(self.cube.add(Cube(-1, 0, 1)), 2,-1),
                    Edge(self.cube.add(Cube(-1, 0, 1)), 1, 1),
                    Edge(self.cube.add(Cube(0, -1, 1)), 2, -1),
                    Edge(self.cube, 1, 1),
                    ]
            elif self.rot == 1:
                return [
                    Edge(self.cube, 0, 1),
                    Edge(self.cube.add(Cube(0, -1, 1)), 2, -1),
                    Edge(self.cube, 2, 1),
                    Edge(self.cube.add(Cube(1, 0, -1)), 0, -1),
                    ]
            else:  # self.rot == 2
                return [
                    Edge(self.cube, 1, 1),
                    Edge(self.cube.add(Cube(1, 0, -1)), 0, -1),
                    Edge(self.cube.add(Cube(0, 1, -1)), 0, -1),
                    Edge(self.cube.add(Cube(0, 1, -1)), 1, 1),
                    ]
        else:  # self.dir == -1
            if self.rot == 0:
                return [
                    Edge(self.cube.add(Cube(0, -1, 1)), 2, 1),
                    Edge(self.cube, 1, -1),
                    Edge(self.cube.add(Cube(-1, 0, 1)), 2, 1),
                    Edge(self.cube.add(Cube(-1, 0, 1)), 1, -1),
                    ]
            elif self.rot == 1:
                return [
                    Edge(self.cube, 2, -1),
                    Edge(self.cube.add(Cube(1, 0, -1)), 0, 1),
                    Edge(self.cube, 0, -1),
                    Edge(self.cube.add(Cube(0, -1, 1)), 2, 1),
                    ]
            else:  # self.rot == 2
                return [
                    Edge(self.cube.add(Cube(0, 1, -1)), 0, 1),
                    Edge(self.cube.add(Cube(0, 1, -1)), 1, -1),
                    Edge(self.cube, 1, -1),
                    Edge(self.cube.add(Cube(1, 0, -1)), 0, 1),
                    ]

    def vertices(self):
        """Returns the two vertices this edge travels between, in from-to order."""
        if self.dir == 1:
            if self.rot == 0:
                return (Vertex(self.cube.add(Cube(-1,0,1)), 1), Vertex(self.cube.add(Cube(1,-1,0)), -1))
            elif self.rot == 1:
                return (Vertex(self.cube.add(Cube(1,-1,0)), -1), Vertex(self.cube, 1),)
            else:  # self.rot == 2
                return (Vertex(self.cube, 1), Vertex(self.cube.add(Cube(1,0,-1)), -1))
        else:  # self.dir == -1 or None
            if self.rot == 0:
                return (Vertex(self.cube.add(Cube(1,-1,0)), -1), Vertex(self.cube.add(Cube(-1,0,1)), 1))
            elif self.rot == 1:
                return (Vertex(self.cube, 1), Vertex(self.cube.add(Cube(1,-1,0)), -1))
            else:  # self.rot == 2
                return (Vertex(self.cube.add(Cube(1,0,-1)), -1), Vertex(self.cube, 1))


    def __str__(self):
        return str(self.cube.x)+", "+str(self.cube.y)+", "+str(self.cube.z)+"; "+str(self.rot)+str(self.dir)

    def __eq__(self, other):
        if isinstance(other, Edge):
            return self.cube == other.cube and self.rot == other.rot and ((self.dir is None and other.dir is None) or self.dir == other.dir)
        else:
            return False
        
    def __hash__(self):
        return hash(tuple((self.cube.x, self.cube.y, self.cube.z, self.rot, self.dir)))
    
    @classmethod
    def from_pair(cls, k1, k2, dir=None):
        """Given an adjacent pair of cubes, return the (normalized) edge between them.
        The optional dir is +1 for counter-clockwise and -1 for clockwise."""
        diff = k1.sub(k2)
        assert diff.mag() == 1, (k1, k2)
        if diff.x == 1:
            if diff.y == 0:
                return cls(k2, 2, dir=dir)
            else:
                return cls(k2, 1, dir=dir)
        elif diff.x == 0:
            if diff.y == -1:
                return cls(k2, 0, dir=dir)
            else:
                return cls(k1, 0, dir=dir)
        else:
            if diff.y == 0:
                return cls(k1, 2, dir=dir)
            else:
                return cls(k1, 1, dir=dir)
            
    @classmethod
    def from_vertices(cls, v1, v2):
        """Given an adjacent pair of vertices, return the edge from v1 to v2."""
        assert v1.rot == -v2.rot
        delta = v1.cube.sub(v2.cube)
        if v1.rot == 1:
            if delta == Cube(-2, 1, 1):
                return cls(v1.cube.add(Cube(1,0,-1)), 0, 1)
            elif delta == Cube(-1, 1, 0):
                return cls(v1.cube, 1, -1)
            elif delta == Cube(-1, 0, 1):
                return cls(v1.cube, 2, 1)
            raise ValueError
        else:
            if delta == Cube(2, -1, -1):
                return cls(v1.cube.add(Cube(-1,1,0)), 0, -1)
            elif delta == Cube(1, 0, -1):
                return cls(v1.cube.add(Cube(-1,0,1)), 2, -1)
            elif delta == Cube(1, -1, 0):
                return cls(v1.cube.add(Cube(-1,1,0)), 1, 1)
            raise ValueError    


class Vertex:
    def __init__(self, cube, rot=0):
        """Vertex is a cube and a rotation: +1 or -1 to correspond to +x or -x, and 0 corresponds to the center of the cube."""
        self.cube = cube
        assert rot in [-1,0,1]
        self.rot = rot

    def adj_vertices(self):
        """Returns the six vertices adjacent to this vertex."""
        if self.rot == 0:
            return [
                Vertex(self.cube,-1),
                Vertex(self.cube.add(Cube(-1,1,0)),1),
                Vertex(self.cube.add(Cube(1,0,-1)),-1),
                Vertex(self.cube,1),
                Vertex(self.cube.add(Cube(1,-1,0)),-1),
                Vertex(self.cube.add(Cube(-1,0,1)),1),
                ]
        elif self.rot == -1:
            return [
                Vertex(self.cube.add(Cube(-2,1,1)),1),
                Vertex(self.cube.add(Cube(-1,1,0)),0),
                Vertex(self.cube.add(Cube(-1,1,0)),1),
                Vertex(self.cube,0),
                Vertex(self.cube.add(Cube(-1,0,1)),1),
                Vertex(self.cube.add(Cube(-1,0,1)),0),
                ]
        else:  # self.rot == 1
            return [
                Vertex(self.cube,0),
                Vertex(self.cube.add(Cube(1,0,-1)),-1),
                Vertex(self.cube.add(Cube(1,0,-1)),0),
                Vertex(self.cube.add(Cube(2,-1,-1)),-1),
                Vertex(self.cube.add(Cube(1,-1,0)),0),
                Vertex(self.cube.add(Cube(1,-1,0)),-1),
                ]
        
    def edge_vertices(self):
        """Returns an empty list if it's the central vertex, or the three adjacency vertices paired with the edge between them (from this one to that one)."""
        if self.rot == 0:
            return []
        elif self.rot == -1:
            return [
                (Vertex(self.cube.add(Cube(-2,1,1)),1), Edge(self.cube.add(Cube(-1,1,0)), 0, -1)),
                (Vertex(self.cube.add(Cube(-1,1,0)),1), Edge(self.cube.add(Cube(-1,1,0)), 1, 1)),
                (Vertex(self.cube.add(Cube(-1,0,1)),1), Edge(self.cube.add(Cube(-1,0,1)), 2, -1)),
                ]
        else:  # self.rot == 1
            return [
                (Vertex(self.cube.add(Cube(1,0,-1)),-1), Edge(self.cube, 2, 1)),
                (Vertex(self.cube.add(Cube(2,-1,-1)),-1), Edge(self.cube.add(Cube(1,0,-1)), 0, 1)),
                (Vertex(self.cube.add(Cube(1,-1,0)),-1), Edge(self.cube, 1, -1)),
                ]

    def down_pair(self):
        """Returns the two vertices above this vertex in a triangle pointing down as a tuple."""
        if self.rot == 0:
            return (Vertex(self.cube.add(Cube(-1,1,0)),1), Vertex(self.cube.add(Cube(1,0,-1)),-1))
        elif self.rot == -1:
            return (Vertex(self.cube.add(Cube(-1,1,0)),0), Vertex(self.cube.add(Cube(-1,1,0)),1))
        else:  # self.rot == 1
            return (Vertex(self.cube.add(Cube(1,0,-1)),-1), Vertex(self.cube.add(Cube(1,0,-1)),0))
    
    def up_pair(self):
        """Returns the two vertices below this vertex in a triangle pointing up as a tuple."""
        if self.rot == 0:
            return (Vertex(self.cube.add(Cube(-1,0,1)),1), Vertex(self.cube.add(Cube(1,-1,0)),-1))
        elif self.rot == -1:
            return (Vertex(self.cube.add(Cube(-1,0,1)),0), Vertex(self.cube.add(Cube(-1,0,1)),1))
        else:  # self.rot == 1
            return (Vertex(self.cube.add(Cube(1,-1,0)),-1), Vertex(self.cube.add(Cube(1,-1,0)),0))

    def trio(self):
        """Returns the three cubes adjacent to this vertex as a list; returns an empty list for central vertices."""
        if self.rot == 1:
            return [self.cube, self.cube.add(Cube(1,0,-1)), self.cube.add(Cube(1,-1,0))]
        elif self.rot == -1:
            return [self.cube, self.cube.add(Cube(-1,0,1)), self.cube.add(Cube(-1,1,0))]
        else:
            return []

    def __str__(self):
        return str(self.cube.x)+", "+str(self.cube.y)+", "+str(self.cube.z)+"; "+str(self.rot)

    def __eq__(self, other):
        if isinstance(other, Vertex):
            return self.cube == other.cube and self.rot == other.rot
        else:
            return False
        
    def __hash__(self):
        return hash(tuple((self.cube.x, self.cube.y, self.cube.z, self.rot)))

    @classmethod
    def from_trio(cls, k1, k2, k3):
        """Given three adjacent cubes, return the (normalized) vertex they share."""
        #This is either a left-pointing triangle or a right-pointing triangle.
        if k1.x == k2.x:
            return cls(k3, 1 if k3.x < k1.x else -1)
        if k1.x == k3.x:
            return cls(k2, 1 if k2.x < k1.x else -1)
        elif k2.x == k3.x:
            return cls(k1, 1 if k1.x < k2.x else -1)
        else:
            raise ValueError((k1,k2,k3,))



