
class Area:
    def __init__(self, cid, members):
        """Each area has a area id (cid) and a set of cubes that are members.
        I will often assume that areas are contiguous but that isn't enforced."""
        self.cid = cid
        self.members = set(members)
        self.outside = False
    
    def calc_edges(self, cid_from_cube):
        """Calculates boundary, the set of cubes that border another area (not including the map edge!),
        self_edges, a dictionary that maps from other cids to all cubes that border that cid,
        other_edges, a dictionary that maps from other cids to all cubes in the other area that border this one."""
        self.boundary = set()
        self.self_edges = {}
        self.other_edges = {}
        for member in self.members:
            others = [other for other in member.neighbors() if other not in self.members and other in cid_from_cube]
            if not all([other in cid_from_cube for other in member.neighbors()]):
                self.outside = True
            for other in others:  # Note this will skip if it's an empty list
                self.boundary.add(member)
                ocid = cid_from_cube[other]
                if cid_from_cube[other] in self.self_edges:
                    self.self_edges[ocid].add(member)
                    self.other_edges[ocid].add(other)
                else:
                    self.self_edges[ocid] = set([member])
                    self.other_edges[ocid] = set([other])