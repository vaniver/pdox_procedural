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