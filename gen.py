import os
import random
import yaml

from map_io import valid_cubes
from area import Area
from chunk_split import check_contiguous, find_contiguous, split_chunk, SplitChunkMaxIterationExceeded
from cube import *
from terrain import BaseTerrain, RAIL_DIST, TERRAIN_HEIGHT, WATER_HEIGHT
from voronoi import area_voronoi, iterative_voronoi, growing_voronoi, voronoi

import ck3
import eu4
import v3
import hoi4

class CreationError(Exception):
    pass

DEPTH_MAP = {"e": 0, "k": 1, "d": 2, "c": 3, "b": 4}

class RegionTree:
    """A class to hold the region tree.
    This is game-agnostic, which means it needs to have the basic details for all games.
    The ordering goes something like:
    - era
      - continent
        - region
          - area
            - county
              - barony
    The overall divisions of the world are not a tree, but landed_titles and related things are.
    At the county level, children (the baronies) is just a list of strings instead of a list of RegionTrees.
    """
    def __init__(self, title=None, tag=None, culture=None, religion=None, rough="forest", holy_site=None, color=("0","0","0"), capital_title=None, capital_pid=-1, capital_rid=-1, children = []):
        self.capital_title = capital_title
        self.capital_pid = capital_pid
        self.capital_rid = capital_rid
        self.culture = culture
        self.religion = religion
        self.rough = rough
        self.holy_site = holy_site
        self.title = title
        self.tag = tag
        self.color = color
        if len(children) > 0:
            self.children = children
        else:
            self.children = []

    def all_ck3_titles(self):
        """Returns all ck3 titles defined in this region tree.
        There are four types:
        e_ (continents)
        k_ (regions)
        d_ (areas)
        c_ (counties)
        b_ (baronies)"""
        if self.title is None:
            return []
        title_list = [self.title]
        for child in self.children:
            if isinstance(child,RegionTree):
                title_list.extend(child.all_ck3_titles())
            else:
                title_list.append(child)
        return title_list

    def some_ck3_titles(self, filter):
        """Returns all ck3 titles that start with filter."""
        return [x for x in self.all_ck3_titles() if x.startswith(filter)]
    
    def all_region_trees(self):
        rt_list = [self]
        for child in self.children:
            if isinstance(child,RegionTree):
                rt_list.extend(child.all_region_trees())
        return rt_list
    
    def all_tag_pids(self, last_tag=""):
        """Returns a list of tag mappings defined by this region_tree.
        Will have a blank string for any untagged provinces."""
        if self.tag is not None:
            last_tag = self.tag
        tag_list = []
        for child in self.children:
            if isinstance(child,RegionTree):
                tag_list.extend(child.all_tag_pids(last_tag=last_tag))
            else:
                tag_list.append(last_tag)
        return tag_list

    def all_holy_sites(self):
        """Returns all holy sites."""
        if self.holy_site is None:
            holy_site_list = []
        else:
            holy_site_list = [self.holy_site]
        for child in self.children:
            if isinstance(child,RegionTree):
                holy_site_list.extend(child.all_holy_sites())
        return holy_site_list
    
    def capital(self):
        if self.capital_title is not None:
            return self.capital_title
        if self.title[0] == "c":
            return self.title
        if len(self.children) > 0 and isinstance(self.children[0], RegionTree):
            self.capital_title = self.children[0].capital()
            return self.capital_title
        return ""
    
    def culrels(self):
        if self.title[0] == "c":
            return [(self.culture, self.religion)]
        else:
            culrel = [(self.culture, self.religion)]
            for child in self.children:
                culrel.extend(child.culrels())
            return culrel
        
    def culrelmap(self):
        if self.title[0] == "c":
            if self.culture is not None:
                return {self.title: (self.culture, self.religion)}
            else:
                return {}
        else:
            culrelmap = {}
            if self.culture is not None:
                culrelmap[self.title] = (self.culture, self.religion)
            for child in self.children:
                culrelmap.update(child.culrelmap())
            return culrelmap
        
    def find_by_title(self, title):
        """Given a title, return the region_tree corresponding to that title (either self or a child, or a more remote descendant.)"""
        if self.title == title:
            return self
        if self.title[0] == "c":
            return None
        for child in self.children:
            f =  child.find_by_title(title)
            if f is not None:
                return f
        return None

    @classmethod
    def from_csv(cls, filename, last_pid=1, last_rid=1, last_srid=1):
        """last_pid and last_rid will be used to assign pids and rids as we go.
        Returns the region_tree, the new last_pid, and the new last_rid."""
        with open(filename) as inf:
            current = {}
            for line in inf.readlines():
                lsplit = line.split(",")
                depth = DEPTH_MAP[lsplit[0][0]]
                if depth == 1:
                    last_srid += 1
                elif depth == 2:  # This is a duchy/state, and so the region_id needs to increase.
                    last_rid += 1
                elif depth == 4:  # This is a barony, and so just needs to be appended to children of the current county.
                    for cind in current:
                        if current[cind].capital_pid < 0:
                            current[cind].capital_pid = last_pid
                    current[3].children.append(lsplit[0].strip())
                    last_pid += 1
                    continue
                if depth in current:  # We finished a unit and are on to the next one.
                    dd = max(current.keys())
                    while dd >= depth:  # We've got to make sure we finish any smaller units first.
                        current[dd-1].children.append(current.pop(dd))
                        dd -= 1
                title = lsplit[0]
                color = tuple([x.strip() for x in lsplit[1:4]]) if len(lsplit) > 3 else ("0","0","0")
                tag, culture, religion, rough = lsplit[4:8] if len(lsplit) > 7 else [None, None, None, "forest"]
                holy_site = lsplit[8].strip() if len(lsplit) > 8 else None
                current[depth] = cls(title=title, color=color, tag=tag, culture=culture, religion=religion, rough=rough, holy_site=holy_site, capital_rid=last_rid)
            while len(current) > 0:
                depth = max(current.keys())
                if depth-1 in current:
                    current[depth-1].children.append(current.pop(depth))
                else:
                    result = current[depth]
                    break
        return result, last_pid, last_rid, last_srid

    @classmethod
    def from_dict(cls, contents, last_pid=1, last_rid=1, last_srid=1):
        """Given a dictionary of region details, recursively create a RegionTree. Also returns pid/rid/srid and localization dictionary."""
        localization = {}
        children = contents.get("children", [])
        result_children = []
        if len(children) > 0 and isinstance(children[0], str):
            for child in children:
                title, local = child.split("|")
                localization[title] = local
                result_children.append(title)
                last_pid += 1
        else:
            for child in children:
                result, last_pid, last_rid, last_srid, child_localization = cls.from_dict(child, last_pid, last_rid, last_srid)
                result_children.append(result)
                localization.update(child_localization)
        title = contents["title"]  # This should break if it's not there
        color = tuple([x.strip() for x in contents["color"].split(" ")])  # TODO: Maybe just use color as a string instead of a tuple?
        depth = DEPTH_MAP[title[0]]
        if depth == 2:
            last_rid += 1
        elif depth == 1:
            last_srid += 1
        if "l" in contents:
            localization[title] = contents["l"]
        culture = contents.get("cul", None)
        religion = contents.get("rel", None)
        holy_site = contents.get("holy", None)
        tag = contents.get("tag", None)
        rough = contents.get("rough", "forest")
        result = cls(title=title, color=color, tag=tag, culture=culture, religion=religion, rough=rough, holy_site=holy_site, capital_rid=last_rid, children=result_children)
        return result, last_pid, last_rid, last_srid, localization
            

    @classmethod
    def from_yml(cls, filename, last_pid=1, last_rid=1, last_srid=1):
        """Processes a .yml file to create a dictionary, which then is run thru from_dict. Also returns localization dictionary."""
        with open(filename, encoding='utf_8_sig') as inf:
            contents = yaml.load(inf, yaml.Loader)
        return cls.from_dict(contents, last_pid, last_rid, last_srid)
        


def assemble_culrels(region_trees):
    """Create lists of cultures and religions that are present in region_trees, which is a list of RegionTrees."""
    cultures = set()
    religions = set()
    for region_tree in region_trees:
        culrel = region_tree.culrels()
        cultures.update([x[0] for x in culrel])
        religions.update([x[1] for x in culrel])
    if None in cultures:
        cultures.remove(None)
    if None in religions:
        religions.remove(None)
    return cultures, religions


def create_chunks(weight_from_cube, num_centers):
    """Create num_centers different voronoi chunks using weight_from_cube."""
    centers = random.sample(sorted(weight_from_cube.keys()),num_centers)
    centers, result, distmap = voronoi(centers, weight_from_cube=weight_from_cube)
    cids = sorted(set(result.values()))  # This should just be the range from 0 to num_centers
    chunks = []
    for cid in cids:
        chunks.append(Area(cid, [k for k, v in result.items() if v == cid]))
    for chunk in chunks:
        chunk.calc_edges(result)
    return centers, chunks, cids

def compute_func(chunks, cids, size):
    """Given a bunch of chunks, figure out which ones are connected to each other as a clique, with the minimum boundary size.
    cids are the ids of the chunks (the index to call into the chunks list); probably I don't need this?
    The returned list is sorted by minimum boundary size in descending order."""
    assert 3 <= size <= 5
    triangles = set()
    for cid in cids:
        if chunks[cid].outside:
            continue
        for oid1 in chunks[cid].self_edges.keys():
            if chunks[oid1].outside:
                continue
            for oid2 in chunks[oid1].self_edges.keys():
                if chunks[oid2].outside:
                    continue
                if cid in chunks[oid2].self_edges.keys():
                    # Found a triangle!
                    short_edge = min(
                        len(chunks[cid].self_edges[oid1]),  len(chunks[cid].other_edges[oid1]),
                        len(chunks[cid].self_edges[oid2]),  len(chunks[cid].other_edges[oid2]),
                        len(chunks[oid1].self_edges[oid2]), len(chunks[oid1].other_edges[oid2]),
                    )
                    triangles.add((tuple(sorted([cid,oid1,oid2])), short_edge, sum([len(chunks[x].members) for x in [cid,oid1,oid2]])))
    if size == 3:
        return sorted(triangles, key=lambda x: x[1], reverse=True)
    tets = set()
    for tri in triangles:
        for other in triangles:
            ids = set(tri[0]).union(other[0])
            if len(ids) == 4:
                tets.add((tuple(sorted(ids)), min(tri[1], other[1]), sum([len(chunks[x].members) for x in ids])))
    if size == 4:
        return sorted(tets, key=lambda x: x[1], reverse=True)
    pents = set()
    for tet in tets:
        for other in triangles:
            ids = set(tet[0]).union(other[0])
            if len(ids) == 5:
                pents.add((tuple(sorted(ids)), min(tet[1], other[1]), sum([len(chunks[x].members) for x in ids])))
    if size == 5:
        return sorted(pents, key=lambda x: x[1], reverse=True)


def create_triangular_continent(weight_from_cube, chunks, candidate, config):
    """Chunks is a list of chunks; candidates is a tuple of chunk ids (of length 3, 4, or 5).
    This generates a continent out of a series of triangular chunk cliques and will return CreationFailure if the adjacencies aren't right.
    Returns a list cube_from_pid"""
    terr_templates = []
    num_k = len(candidate[0])
    num_c = num_k - 2
    num_b = num_k * 2 - 3
    if num_k == 3:
        a,b,c = candidate[0]
        centers = [((a,b,c), list(chunks[a].self_edges[b].intersection(chunks[a].self_edges[c]))[0])]
        fixed_borders = []
        dyna_borders = [(a,b),(b,c),(a,c)]
    elif num_k == 4:
        # a and d only connect to b and c, both b and c connect to everyone.
        nums = {2: [], 3: []}
        for ind in range(4):
            others = list(candidate[0][:ind]) + list(candidate[0][ind+1:])
            nums[sum([o in chunks[candidate[0][ind]].self_edges for o in others])].append(candidate[0][ind])
        if len(nums[3]) < 2:
            print("No b-c edge for 4-continent")
            raise CreationError
        elif len(nums[3]) > 2:  # We need to pick the longest edge to be the b-c edge
            nums[3] = sorted([y for y in nums[3]], key=lambda x: max([chunks[x].self_edges[o] for o in nums[3] if o != x]), reverse=True)
        b,c,a,d = nums[3] + nums[2]
        centers = [
            ((a,b,c), list(chunks[a].self_edges[b].intersection(chunks[a].self_edges[c]))[0]),
            ((b,c,d), list(chunks[d].self_edges[b].intersection(chunks[d].self_edges[c]))[0])
        ]
        fixed_borders = [(b,c)]
        dyna_borders = [(a,b),(a,c),(b,d),(c,d)]
    elif num_k == 5:
        nums = {2: [], 3: [], 4: []}
        for ind in range(5):
            others = list(candidate[0][:ind]) + list(candidate[0][ind+1:])
            nums[sum([o in candidate[ind].self_edges for o in others])].append(candidate[0][ind])
        # b connects to at least 4; abc, bcd, bde are the triangles. 
        if len(nums[4]) < 1:
            print("No b for 5-continent")
            raise CreationError
        b = nums[4][0]
        c, d, alpha, beta = nums[4][1:] + nums[3] + nums[2]
        a = alpha if alpha in chunks[c].self_edges else beta
        e = alpha if alpha in chunks[d].self_edges else beta
        if d not in chunks[c].self_edges:
            print("c-d didn't line up correctly for 5-continent")
            raise CreationError
        centers = [
            ((a,b,c), list(chunks[a].self_edges[b].intersection(chunks[a].self_edges[c]))[0]),
            ((b,c,d), list(chunks[d].self_edges[b].intersection(chunks[d].self_edges[c]))[0]),
            ((c,d,e), list(chunks[d].self_edges[c].intersection(chunks[d].self_edges[e]))[0]),
        ]
        fixed_borders = [(b,c), (b,d)]
        dyna_borders = [(a,b),(a,c),(b,c),(b,e),(d,e)]
    # We're going to mostly hardcode how the central duchy works.
    cube_from_pid = []
    for (aa,bb,cc), center in centers:
        _, _, cdistmap = voronoi([center], weight_from_cube)
        if not all([x not in cube_from_pid for x in center.neighbors()]):  # The center is too close to an existing center.
            print("Centers too close together")
            raise CreationError
        cube_from_pid.extend([center] + list(center.neighbors()))
        if not all([x in weight_from_cube for x in cube_from_pid]):  # Check to make sure the center is actually contained.
            print("Center too close to edge")
            raise CreationError
        # Add the three counties to the central duchy, each one carved out of a different original region.
        for cid, other in enumerate([aa,bb,cc]):
            options = {k:weight_from_cube[k] for k in cdistmap.keys() if k in chunks[other].members and k not in cube_from_pid}
            _, _, selection = voronoi([min(options, key=cdistmap.get)],options)
            ss = sorted(selection, key=selection.get)
            for k in ss[:config["CENTER_SIZE_LIST"][cid+1]]:
                cube_from_pid.append(k)
        terr_templates.append(config["CENTER_TERRAIN_TEMPLATE"])
    allocated = set([x for x in cube_from_pid])
    # Create the border duchies inside the annular region
    group_from_cube = {}
    for ind, (aa,bb) in enumerate(fixed_borders):
        initiala = [x for x in chunks[aa].self_edges[bb] if x not in allocated]
        initialb = [x for x in chunks[bb].self_edges[aa] if x not in allocated]
        if len(initiala) == 0 or len(initialb) == 0:  # One of the sections is cut off from the other by the center.
            print("Fixed edge cut off by center expansion.")
            raise CreationError
        # This should maybe be a call to growing_voronoi or something? I'm doing it manually here b/c
        # I want to ensure that the whole connection between the centers is included, but this is maybe something that would be done by the right choice of distance.
        if len(initiala) + len(initialb) > config["BORDER_SIZE"]:  # TODO: Handle this case correctly
            print("Fixed edge too large for border duchy.")
            raise CreationError
        this_border = initiala + initialb
        options = {}
        for cube in this_border:
            for nbr in cube.neighbors():
                if nbr in allocated or nbr in this_border or nbr not in weight_from_cube:
                    continue
                w = weight_from_cube[nbr] + 8  # We don't want to have any gaps, so we need the base distance to matter more than the random weight, while still counting the random weight.
                if w in options:
                    options[w].append(nbr)
                else:
                    options[w] = [nbr]
        while len(this_border) < config["BORDER_SIZE"] and len(options) > 0:
            minw = min(options.keys())
            random.shuffle(options[minw])
            next_bit = options[minw].pop()
            if len(options[minw]) == 0:
                del options[minw]
            if next_bit in this_border:
                continue
            this_border.append(next_bit)
            for nbr in next_bit.neighbors():
                if nbr in allocated or nbr in this_border or nbr not in weight_from_cube:
                    continue
                w = weight_from_cube[nbr] + minw + 8
                if w in options:
                    options[w].append(nbr)
                else:
                    options[w] = [nbr]
        if len(this_border) != config["BORDER_SIZE"]:
            print("Fixed edge too small for border size.")
            raise CreationError
        for cube in this_border:
            group_from_cube[cube] = ind
            allocated.add(cube)
    # Set up the centers for the annular regions
    new_centers = []
    # Add the borders
    for o1, o2 in dyna_borders:
        options = {k for k in chunks[o1].self_edges[o2].union(chunks[o1].other_edges[o2]) if k not in allocated}
        if len(options) == 0:
            print("No connection between regions left for dynamic border region.")
            raise CreationError
        new_centers.append(min(options, key=cdistmap.get))
    # Add the kingdoms
    for o in candidate[0]:
        options = {k: min([k.sub(nc).mag() for nc in new_centers[:len(dyna_borders)]]) for k in chunks[o].members if k not in allocated and any([kn in allocated for kn in k.neighbors()])}
        new_centers.append(max(options, key=options.get))
    subweights = {k:v for k,v in weight_from_cube.items() if k not in allocated}
    try:
        new_centers, dyna_group_from_cube = growing_voronoi(new_centers, [config["BORDER_SIZE"]]*len(dyna_borders) + [config["KINGDOM_SIZE"]]*num_k, subweights)
    except ValueError:
        print("growing_voronoi failed for some reason.")
        raise CreationError
    # Split the border duchies into counties
    group_from_cube.update({k: v + len(fixed_borders) for k, v in dyna_group_from_cube.items() if v != -1})
    for ind in range(num_b):
        duchy = [k for k, v in group_from_cube.items() if v==ind]
        try:
            counties = split_chunk(duchy, config["BORDER_SIZE_LIST"])
        except:  # Covers both difficult-to-split and incorrectly-sized regions.
            print("Duchy splitting failed for some reason.")
            raise CreationError
        for county in counties:
            cube_from_pid.extend(county)
        terr_templates.append(config["BORDER_TERRAIN_TEMPLATE"])
    # Split the kingdoms into duchies
    adj_size_list = [x for x in config["KINGDOM_DUCHY_LIST"]]
    adj_size_list[0] -= 6
    sea_centers = []
    for kind in range(num_b,num_b+num_k):  # 3 border duchies - 3 kingdoms
        kingdom = [k for k,v in group_from_cube.items() if v==kind]
        # In order to be a capital, it needs to have 5 neighbors in the region and 1 neighbor not allocated.
        poss_capitals = sorted([k for k,v in group_from_cube.items() if (v == kind and sum([group_from_cube.get(kn,-1) == -1 and kn not in allocated for kn in k.neighbors()]) == 1 and sum([group_from_cube.get(kn,-1) == kind for kn in k.neighbors()]) == 5)], key=cdistmap.get, reverse=True)
        # This will sometimes count lakes, which is bad, but I think using cdist to sort it will mostly resolve that.
        to_be_continued = True
        attempt = 0
        while to_be_continued:
            for pc in poss_capitals:
                if not to_be_continued:
                    break
                attempt = 0
                this_capital = [pc] + [pcn for pcn in pc.neighbors() if pcn in kingdom]
                if len(this_capital) != 6:  # This shouldn't be necessary b/c of how poss_capitals is defined, but checking anyway
                    print("WTF: capital size")
                    continue
                others = [k for k in kingdom if k not in this_capital]
                if not check_contiguous(others):  # This doesn't actually seem necessary--it _might_ work otherwise--but probably speeds things up.
                    continue
                while to_be_continued and attempt < 5:
                    attempt += 1
                    try:
                        ksplit = split_chunk(others, adj_size_list)
                        if any([any([kn in ksplit[0] for kn in k.neighbors()]) for k in this_capital]):  #The 17 is adjacent to 
                            to_be_continued = False
                    except SplitChunkMaxIterationExceeded:
                        continue
                    except AssertionError:  # The kingdom was incorrectly sized.
                        print("Kingdom was incorrectly sized.")
                        raise CreationError
        if not to_be_continued:
            cube_from_pid.extend(this_capital)
            sea_centers.append([x for x in this_capital[0].neighbors() if x not in this_capital][0])
            terr_templates.append(config["KINGDOM_TERRAIN_TEMPLATE"])
            for dind, duchy in enumerate(ksplit):
                start_ind = 1 if dind == 0 else 0  # We don't need to split out the capital county for the capital duchy; it's already done for us.
                try:
                    dsplit = split_chunk(duchy, config["KINGDOM_SIZE_LIST"][dind][start_ind:])
                except:
                    print("Kingdom failed to split.")
                    raise CreationError
                for county in dsplit:
                    cube_from_pid.extend(county)
    return cube_from_pid, terr_templates, sea_centers
    

def create_triangle_continents(config, weight_from_cube = None, n_x=129, n_y=65, num_centers=None, last_pid=1, last_rid=0, last_srid=0):
    """Create len(config["CONTINENT_LISTS"]) continents with the appropriate number of kingdoms.
    Uses the standard triangle-border system, which requires 3 to 5 kingdoms per continent.
    Will start province and region ids at last_pid and last_rid+1 respectively."""
    continents = []
    terr_templates = []
    region_trees = []
    if weight_from_cube is None:
        weight_from_cube = {cub: random.randint(1,8) for cub in valid_cubes(n_x,n_y)}
    if num_centers is None:
        num_centers = len(weight_from_cube) // (3 * config["KINGDOM_SIZE"])
    centers, chunks, cids = create_chunks(weight_from_cube, num_centers)
    ind = -1
    for cind, cont_list in enumerate(config["CONTINENT_LISTS"]):
        empires = [x for x in cont_list if x[0] == "e"]
        kingdoms =[x for x in cont_list if x[:2] == "61"]  # TODO: configure these instead of hardcode them
        centers = [x for x in cont_list if x[:2] == "22"]
        borders = [x for x in cont_list if x[:2] == "24"]
        num_k = len(kingdoms)
        num_c = num_k - 2
        num_b = num_k * 2 - 3
        assert len(empires) == 1
        assert len(centers) == num_c
        assert len(borders) == num_b  # Changed this from >= to == so that we can use CONTINENT_LISTS elsewhere to determine which characters to spawn. If we want to randomize them, we'll have to do it in making the config.
        region_tree, last_pid, last_rid, last_srid, l_from_title = RegionTree.from_yml(os.path.join("data", empires[0])+".yml", last_pid=last_pid, last_rid=last_rid, last_srid=last_srid)
        region_tree.children[0].capital_pid = last_pid  # The interstitial kingdom has its capital in another file, and so this needs to be assigned here.
        random.shuffle(kingdoms)
        random.shuffle(centers)
        random.shuffle(borders)
        for title in centers[:num_c] + borders[:num_b]:
            rt, last_pid, last_rid, last_srid, local = RegionTree.from_yml(os.path.join("data", title)+".yml", last_pid=last_pid, last_rid=last_rid, last_srid=last_srid)
            l_from_title.update(local)
            region_tree.children[0].children.append(rt) # The empires come with an interstitial kingdom to add all of these duchies to.
        for title in kingdoms:
            rt, last_pid, last_rid, last_srid, local = RegionTree.from_yml(os.path.join("data", title)+".yml", last_pid=last_pid, last_rid=last_rid, last_srid=last_srid)
            l_from_title.update(local)
            region_tree.children.append(rt)
        region_trees.append(region_tree)
        candidates = compute_func(chunks, cids, num_k)
        all_sea_centers = []
        while len(continents) <= cind:
            ind += 1
            print("Continent attempt: " + str(ind))
            subweights = {k:v for k,v in weight_from_cube.items() if any([k in chunks[cid].members for cid in candidates[ind][0]])}
            try:
                continent, terr_template, sea_centers = create_triangular_continent(subweights, chunks, candidates[ind], config)
                continents.append(continent)
                terr_templates.append(terr_template)
                all_sea_centers.extend(sea_centers)
            except CreationError:
                print("Creation error")
                if ind == len(candidates) - 1:
                    print(f"Failed to make enough of size {num_k}, had to rechunk.")
                    centers, chunks, cids = create_chunks(weight_from_cube, num_centers)
                    candidates = compute_func(chunks, cids, num_k)
                    ind = -1
    return continents, terr_templates, region_trees, all_sea_centers, last_pid, last_rid, last_srid, l_from_title,


def assign_sea_zones(sea_cubes, config, province_centers=[], region_centers=[], min_province_distance=2, style="random"):
    """Given the set of cubes sea_cubes, the overall config and optional centers (for regions or provinces), determine the sea regions and sea provinces."""
    # Determine if any of the proposed centers are close to each other, and drop the spare(s) if so. 
    sea_province_centers = []
    rid_from_pid = {}
    for ind, k in enumerate(province_centers):
        if not any([ok.sub(k).mag() <= min_province_distance for ok in province_centers[ind:]]):
            sea_province_centers.append(k)
    if "SEA_PROVINCES" not in config:
        config["SEA_PROVINCES"] = len(sea_cubes) // config.get("SEA_PROVINCE_SIZE", 40)
    if style == "random":
        v_centers = random.sample(list(sea_cubes),max(0, config["SEA_PROVINCES"] - len(sea_province_centers))) + sea_province_centers
    elif style == "even":
        y_num = 20 #sqrt(config["SEA_PROVINCES"] * config["n_y"] / config["n_x"]).__round__()
        x_num = y_num * config["n_x"] // config["n_y"]
        v_centers = [s for s in sea_province_centers]
        for x in range(x_num):
            for y in range(y_num):
                xx = (2*x + 1) * config["n_x"] // (2*x_num)
                yy = (2*y + 1) * config["n_y"] // (2*y_num) + xx//2
                center =  Cube(xx,-yy,-xx+yy)
                if center in sea_cubes:
                    v_centers.append(center)
    v_centers, pid_from_cube, _ = voronoi(v_centers, {k:1 for k in sea_cubes})  # TODO: This really ought to be better.
    # Group the provinces together into regions.
    pids = sorted(set(pid_from_cube.values()))
    pid_centers = sorted(set([pid_from_cube[rc] for rc in region_centers]))
    extra_regions = config.get("SEA_REGIONS", 20) - len(pid_centers)
    if extra_regions > 0:
        pid_centers.extend(random.sample([x for x in pids if x not in pid_centers], k=extra_regions))
    # Now that we have a bunch of centers, we need to allocate all of the regions.
    rid_from_pid = area_voronoi(pid_from_cube, pid_centers)
    # TODO: Assign strategic regions instead of just doing the region clumping?
    return pid_from_cube, rid_from_pid, rid_from_pid


def assign_terrain_subregion(region, template, rough="forest"):
    """Assign terrain to the region according to the template."""
    # TODO: treat farmland right
    terr_from_cube = {}
    template_list = []
    for k,v in template.items():
        template_list.extend([k] * v)
    random.shuffle(template_list)
    for ind, cube in enumerate(region.values()):
        terr_from_cube[cube] = BaseTerrain[rough] if template_list[ind] == "rough" else BaseTerrain[template_list[ind]]
    return terr_from_cube

def assign_terrain_continent(cube_from_pid, templates):
    """Assign terrain to the continent according to the template list.
    TODO: also generate the heightmap and creates rivers."""
    min_pid = min(cube_from_pid.keys())
    terr_from_cube = {}
    for template in templates:
        max_pid = min_pid + sum(template.values())
        region = {k:v for k,v in cube_from_pid.items() if min_pid <= k < max_pid}
        terr_from_cube.update(assign_terrain_subregion(region, template))  # TODO: Correctly use rough
        min_pid = max_pid
    return terr_from_cube


def arrange_inner_sea(continents, inner_sea_center, angles=[2,4,0]):
    """Given three continents, arrange them to have straits around a central inner sea.
    Also computes wastelands."""
    assert len(continents) == 3
    moved_continents = []
    sea_region_centers = [inner_sea_center]
    longest_dim = 0
    offs = [Cube(-2,4,-2), Cube(0,0,0), Cube(-5,4,1)]  # These are hardcoded for the 1945 seed.
    for ind,continent in enumerate(continents):
        ac = Area(ind, continent)  # Area has unordered membership, which is why we have to construct the dict again later. Continent should probably be a Tile (old code w/ ordered membership).
        off1 = ac.calc_average()
        ac.rectify()
        ac.calc_boundary()
        ac.calc_bounding_hex()
        longest_dim = max(longest_dim, ac.max_x-ac.min_x, ac.max_y-ac.min_y, ac.max_z-ac.min_z)
        off2, rot = ac.best_corner(angles[ind])
        moved_continents.append([k.sub(off1).rotate_right(rot+3).sub(off2).add(inner_sea_center).add(offs[ind]) for k in continent])
    # TODO: Iteratively move them closer to each other until the strait situation is good.
    # TODO: Add the strait mouths to sea_region_centers.
    return moved_continents, sea_region_centers

def arrange_mediterranean(continents):
    """Given two continents, arrange them to have straits around a central inner sea. Because of how bounding boxes work, might have to be north/south? :/"""
    assert len(continents) == 2
    raise NotImplementedError


def assign_color(rgb_from_pid):
    rgb = (random.randint(0,255),random.randint(0,255),random.randint(0,255))
    if rgb not in rgb_from_pid.values():
        return rgb
    else:
        return assign_color(rgb_from_pid)

def create_colors(pid_from_cube):
    """Assign a unique color to each of the pids in pid_from_cube."""
    rgb_from_pid = {}
    for pid in pid_from_cube.values():
        rgb_from_pid[pid] = assign_color(rgb_from_pid)
    return rgb_from_pid


def create_supply_rails(terr_from_cube, pids_from_rid, rid_from_cube, cube_from_pid, pid_from_cube, name_from_rid):
    """Create supply nodes and railways"""
    supply_nodes = []
    railways = []
    areas = {}
    rail_dist_from_cube = {k:RAIL_DIST[v] for k,v in terr_from_cube.items()}
    rail_connex = {}
    for rid, pids in pids_from_rid.items():
        if name_from_rid[rid][0] == "s":
            continue
        cap_pid = min(pids)
        supply_nodes.append(cap_pid)
        areas[rid] = Area(cid=rid, members=[cube_from_pid[pid] for pid in pids if pid in cube_from_pid])
        areas[rid].calc_edges(rid_from_cube)
        for orid in areas[rid].self_edges:
            if name_from_rid[orid][0] == "s":
                continue
            ocap_pid = min(pids_from_rid[orid])
            cap_cube = land_cube_from_pid[cap_pid]
            ocap_cube = land_cube_from_pid[ocap_pid]
            partial_paths = [(0, [cap_cube], False), (0,[ocap_cube], True)]
            need_path = True
            final_path = None
            reached_cubes = {False: {cap_cube}, True: {ocap_cube}}
            while need_path:  # This could be smarter by doing A* instead of just expanding 
                if len(partial_paths) == 0:  # Somehow we failed to find a path.
                    need_path=False
                    continue
                partial_paths = sorted(partial_paths)
                this_path = partial_paths.pop(0)
                for nbr in this_path[1][-1].neighbors():
                    if rid_from_cube.get(nbr,-1) in [rid, orid] and nbr not in reached_cubes[this_path[2]]:
                        if nbr in reached_cubes[not this_path[2]]:
                            other_part = sorted([pp for pp in partial_paths if nbr in pp[1] and this_path[2] != pp[2]])[0][1]
                            other_part.reverse()
                            final_path = this_path[1] + other_part
                            need_path = False
                            break
                        partial_paths.append((this_path[0] + rail_dist_from_cube[nbr], this_path[1] + [nbr], this_path[2]))
                        reached_cubes[this_path[2]].add(nbr)
            if final_path is not None:
                for ind in range(len(final_path)-1):
                    a = pid_from_cube[final_path[ind]]
                    b = pid_from_cube[final_path[ind+1]]
                    if a in rail_connex:
                        rail_connex[a].add(b)
                    else:
                        rail_connex[a] = {b}
                    if b in rail_connex:
                        rail_connex[b].add(a)
                    else:
                        rail_connex[b] = {a}
    supply_nodes = sorted(supply_nodes)
    starting_points = {x for x in supply_nodes}
    while len(starting_points) > 0:
        start = starting_points.pop()
        while len(rail_connex.get(start, [])) > 0:
            next_node = rail_connex[start].pop()
            rail_connex[next_node].discard(start)
            pathway = [start, next_node]
            next_nodes = rail_connex[next_node]
            start = next_node
            while len(next_nodes) == 1:  # Only one place to go; add it to this railroad.
                next_node = next_nodes.pop()
                rail_connex[next_node].discard(start)
                pathway.append(next_node)
                next_nodes = rail_connex[next_node]
                start = next_node
            if len(next_nodes) == 0:  # end of the line
                if pathway[-1] in starting_points:
                    starting_points.remove(pathway[-1])  # We don't need to do it from that side because we did it from this side.
                railways.append((1, pathway))
            else:  # Multiple ways to go from here
                starting_points.add(pathway[-1])
                railways.append((1, pathway))
    return supply_nodes, railways


def create_data(config):
    """The main function that calls all the other functions in order. 
    The resulting data structure should be enough to make the mod for any particular game."""
    random.seed(config.get("seed", 1945))
    last_pid = 1  # province_id. They 1-index instead of 0-indexing.
    last_cid = 1  # county_id. They 1-index instead of 0-indexing.
    last_rid = 1  # region_id. They 1-index instead of 0-indexing.
    last_srid = 1  # strategic_region_id. They 1-index instead of 0-indexing.
    continents, terr_templates, region_trees, sea_centers, last_pid, last_rid, last_srid, name_from_title = create_triangle_continents(config, n_x=config["n_x"], n_y=config["n_y"], num_centers=config.get("num_centers", None), last_pid=last_pid, last_rid=last_rid, last_srid=last_srid)
    m_x = config["n_x"]//2
    m_y = -(config["n_y"]+config["n_x"]//2)//2
    continents, sea_region_centers = arrange_inner_sea(continents, Cube(m_x, m_y, -m_x-m_y))

    pid_from_cube = {}
    rid_from_pid = {}
    srid_from_pid = {}
    cid_from_pid = {}  # This is mostly useful for EU4, whose lowest level is the cid, not the pid.
    cont_from_pid = {}
    pid_from_title = {}
    tag_from_pid = {}
    land_cubes = set()
    sea_cubes = set()
    terr_from_cube = {}
    name_from_pid = {}
    name_from_cid = {}
    name_from_rid = {}
    name_from_srid = {}
    
    last_pid = 1  # province_id. They 1-index instead of 0-indexing.
    last_cid = 0  # county_id. 
    last_rid = 0  # region_id. This is incremented before use.
    last_srid = 0  # strategic_region_id. This is incremented before use.
    for cind, continent in enumerate(continents):
        # This is currently recalculating the pid and rid. This is presumably correct, but probably we should be reading it off the region_tree instead?
        ck3_titles = region_trees[cind].all_ck3_titles()
        sregion_caps = {ck3_titles[ind+3]: t for ind, t in enumerate(ck3_titles) if t[0] == "k"}
        region_caps = {ck3_titles[ind+2]: t for ind, t in enumerate(ck3_titles) if t[0] == "d"}
        county_caps = {ck3_titles[ind+1]: t for ind, t in enumerate(ck3_titles) if t[0] == "c"}
        names = [x for x in ck3_titles if x[0] == "b"]
        for pid, cube in enumerate(continent):
            title = names[pid]
            if title in sregion_caps:
                last_srid += 1
                name_from_srid[last_srid] = name_from_title.get(sregion_caps[title],sregion_caps[title])
            if title in region_caps:
                last_rid += 1
                name_from_rid[last_rid] = name_from_title.get(region_caps[title],region_caps[title])
            if title in county_caps:
                last_cid += 1
                name_from_cid[last_cid] = name_from_title.get(county_caps[title],county_caps[title])
            pid_from_cube[cube] = pid + last_pid
            rid_from_pid[pid + last_pid] = last_rid
            srid_from_pid[pid + last_pid] = last_srid
            name_from_pid[pid + last_pid] = name_from_title.get(title,title)
            pid_from_title[title] = pid + last_pid
            cont_from_pid[pid + last_pid] = cind + 1
        tag_from_pid.update({pid + last_pid: tag for pid, tag in enumerate(region_trees[cind].all_tag_pids())})
        land_cubes = land_cubes.union(continent)
        last_pid += len(continent)
        terr_from_cube.update(assign_terrain_continent({v:k for k,v in pid_from_cube.items() if k in continent}, terr_templates[cind]))
    # At this point, pid_from_cube should be a 1-1 mapping (because we haven't done the larger regions).
    terr_from_pid = {v:terr_from_cube[k] for k,v in pid_from_cube.items() if k in terr_from_cube}
    land_cube_from_pid = {v:k for k,v in pid_from_cube.items()}
    # Split out wastelands / mountains / lakes
    non_land = sorted(find_contiguous(set(valid_cubes(config["n_x"], config["n_y"])) - land_cubes), key=len)
    sea_cubes = set(non_land.pop(-1))  # The largest non-land chunk is the ocean.
    # Determine straits
    straits = []
    for k in land_cubes:
        for other_land, sea_1, sea_2 in k.valid_straits(land_cubes, sea_cubes):
            straits.append((k, other_land, sea_1, sea_2))
            sea_centers.append(sea_1)
    impassable = []
    impassable_rids = []
    for iind, nlg in enumerate(non_land):
        # TODO: do something sensible with terrain assignments.
        impassable.append(last_pid)
        impassable_rids.append(last_rid)
        pid_from_title[f"i_{str(iind)}"] = last_pid
        name_from_pid[last_pid] = f"i_{str(iind)}"
        name_from_rid[last_rid] = f"i_{str(iind)}"
        for nlc in nlg:
            pid_from_cube[nlc] = last_pid
            terr_from_cube[nlc] = BaseTerrain.mountains
            terr_from_pid[last_pid] = BaseTerrain.mountains
            land_cubes.add(nlc)
        rid_from_pid[last_pid] = last_rid
        # TODO: determine continent
        # cont_from_pid[last_pid] = 
        last_pid += 1
        last_rid += 1
    #TODO: Assigning sea provinces should 1) look for major inland seas, like the med, 2) use more regular things that are faster for the deep ocean
    sid_from_cube, rid_from_sid, srid_from_sid = assign_sea_zones(sea_cubes, config, province_centers=sea_centers, region_centers=sea_region_centers, style=config.get("SEA_PROVINCE_STYLE", "even"))
    pid_from_cube.update({k:v + last_pid for k,v in sid_from_cube.items()})
    sea_region = {"ocean": []}  # TODO: multiple oceans
    for k, sid in sid_from_cube.items():
        pid = sid + last_pid
        pid_from_cube[k] = pid
        sea_title = f"s_{sid}"
        pid_from_title[sea_title] = pid
        name_from_pid[pid] = sea_title
    for sid, rid in rid_from_sid.items():
        rid_from_pid[sid + last_pid] = rid + last_rid
        srid_from_pid[sid + last_pid] = srid_from_sid[sid] + last_srid
        sea_title = "s_" + str(rid + last_rid)
        name_from_rid[rid + last_rid] = sea_title
        if sea_title in sea_region:
            sea_region[sea_title].append(sid + last_pid)
        else:
            sea_region[sea_title] = [sid + last_pid]
            sea_region["ocean"].append(sea_title)
        terr_from_pid[sid + last_pid] = BaseTerrain.ocean
    last_pid += max(sid_from_cube.values())
    last_rid += max(rid_from_sid.values())
    name_from_srid.update({k + last_srid: "ocean_"+str(k) for k in sorted(set(srid_from_sid.values()))})
    last_srid += max(srid_from_sid.values())
    terr_from_cube.update({k:BaseTerrain.ocean for k in sea_cubes})
    # Finish up straits
    straits = [(k, ok, pid_from_cube[x1]) for (k, ok, x1, x2) in straits]
    # Assign region points
    coast_from_cube = {}
    coast_from_rid = {}  # This is not quite what I want.
    for cube in land_cubes:
        sids = [pid_from_cube[nbr] for nbr in cube.neighbors() if nbr in sea_cubes]
        if len(sids) > 0:
            coast_from_cube[cube] = min(sids)
    locs_from_rid = {}
    for rid in range(1,last_rid):
        if rid in impassable_rids:
            continue
        pid_from_loc = {}
        title = name_from_rid[rid]
        if title[0] == "s":
            continue
        pids = [pid for pid, rr in rid_from_pid.items() if rr==rid]
        pid_from_loc["city"] = min(pids)
        coastal_pid_cubes = sorted([(pid, coast_from_cube[cube]) for cube, pid in pid_from_cube.items() if pid in pids and cube in coast_from_cube])
        if len(coastal_pid_cubes) > 0:
            pid_from_loc["port"] = coastal_pid_cubes[0][0]
            coast_from_rid[rid] = coastal_pid_cubes[0][1]
        cubes = [cube for cube, pid in pid_from_cube.items() if pid in pids and pid != pid_from_loc["city"]]
        if len(cubes) == 0:
            print(f"Province {pid} only has one cube in it!")
        # TODO: farm, mine, wood dependent on trade goods
        pid_from_loc["farm"] = pid_from_cube[random.sample(cubes, k=1)[0]]
        pid_from_loc["mine"] = pid_from_cube[random.sample(cubes, k=1)[0]]
        pid_from_loc["wood"] = pid_from_cube[random.sample(cubes, k=1)[0]]
        locs_from_rid[rid] = pid_from_loc

    # Determine distance from land/water boundary
    coast = [cube for cube in land_cubes if any([nbr in sea_cubes for nbr in cube.neighbors()])]
    remaining_cubes = land_cubes.difference(coast)
    land_height_from_cube = {cube: 0 for cube in coast}
    distance = 1
    # The height calculation is surprisingly slow. Fix it?
    while len(remaining_cubes) > 0:
        coast = [cube for cube in remaining_cubes if any([nbr in coast for nbr in cube.neighbors()])]
        land_height_from_cube.update({cube: distance for cube in coast})
        remaining_cubes = remaining_cubes.difference(coast)
        distance += 1
    coast = [cube for cube in sea_cubes if any([nbr in land_cubes for nbr in cube.neighbors()])]
    remaining_cubes = sea_cubes.difference(coast)
    water_depth_from_cube = {cube: 0 for cube in coast}
    distance = 1
    while len(remaining_cubes) > 0:
        coast = [cube for cube in remaining_cubes if any([nbr in coast for nbr in cube.neighbors()])]
        water_depth_from_cube.update({cube: distance for cube in coast})
        remaining_cubes = remaining_cubes.difference(coast)
        distance += 1
    # Make heightmap
    height_from_vertex = {}
    for cube, height in land_height_from_cube.items():
        a,b = TERRAIN_HEIGHT[terr_from_cube[cube]]
        height_from_vertex[Vertex(cube, 0)] = height * 3 + sum([random.randint(a,b) for _ in range(4)]) + WATER_HEIGHT
        l = height + random.randint(a,b) + random.randint(a,b)
        r = height + random.randint(a,b) + random.randint(a,b)
        for k in [cube.add(Cube(-1,1,0)), cube.add(Cube(-1,0,1))]:
            if k in land_height_from_cube:
                a,b = TERRAIN_HEIGHT[terr_from_cube[k]]
                l += land_height_from_cube[k] + random.randint(a,b) + random.randint(a,b)
            else:
                l -= 2
        height_from_vertex[Vertex(cube, 1)] = max(1,l) + WATER_HEIGHT
        for k in [cube.add(Cube(1,-1,0)), cube.add(Cube(1,0,-1))]:
            if k in land_height_from_cube:
                a,b = TERRAIN_HEIGHT[terr_from_cube[k]]
                r += land_height_from_cube[k] + random.randint(a,b) + random.randint(a,b)
            else:
                r -= 2
        height_from_vertex[Vertex(cube, -1)] = max(1,r) + WATER_HEIGHT
    a,b = TERRAIN_HEIGHT[BaseTerrain.ocean]
    base_water = WATER_HEIGHT * 4 // 5
    for cube, depth in water_depth_from_cube.items():
        if depth > 3:
            continue
        height_from_vertex[Vertex(cube, 0)] = max(0, base_water - 3 * depth * depth + sum([random.randint(a,b) for _ in range(4)]))
        vl = Vertex(cube, -1)
        if vl not in height_from_vertex:  # Why did I think I needed to check this?
            l = base_water - depth * depth + random.randint(a,b) + random.randint(a,b)
            coast = False
            for k in [cube.add(Cube(-1,1,0)), cube.add(Cube(-1,0,1))]:
                if k in water_depth_from_cube:
                    l += random.randint(a,b) - water_depth_from_cube[k] * water_depth_from_cube[k]
                else:
                    coast = True
            if coast:
                height_from_vertex[vl] = WATER_HEIGHT + 1
            else:
                height_from_vertex[vl] = min(max(0, l), WATER_HEIGHT - 1)
        else:
            print("it was a real check.")
        vr = Vertex(cube, 1)
        if vr not in height_from_vertex:
            r = base_water - depth * depth + random.randint(a,b) + random.randint(a,b)
            coast = False
            for k in [cube.add(Cube(1,-1,0)), cube.add(Cube(1,0,-1))]:
                if k in water_depth_from_cube:
                    r += random.randint(a,b) - water_depth_from_cube[k] * water_depth_from_cube[k]
                else:
                    coast = True
            if coast:
                height_from_vertex[vr] = WATER_HEIGHT + 1
            else:
                height_from_vertex[vr] = min(max(0, r), WATER_HEIGHT - 1)
        else:
            print("it was a real check.")
    print(f"Heightmap heights range from {min(height_from_vertex.values())} to {max(height_from_vertex.values())}.")
    # Create rivers
    # Determine the coastal vertices
    coastal_vertices = set()
    for cube in [k for k,v in land_height_from_cube.items() if v == 0]:
        nbrs = sorted(cube.neighbors())
        for ind0 in range(0,6):
            if nbrs[ind0] not in land_height_from_cube:
                for v in Edge.from_pair(cube, nbrs[ind0]).vertices():
                    coastal_vertices.add(v)
    # TODO: better river creation
    mouths = []
    for v in coastal_vertices:
        for ov, e in v.edge_vertices():
            if ov not in coastal_vertices and height_from_vertex[ov] >= WATER_HEIGHT:
                mouths.append((v, e))
    river_edges = {}
    river_vertices = {}
    vs = set()
    for m in random.sample(mouths, k=len(mouths)//20):
        edges = [m[1]]
        if m[0] in vs:
            continue
        vs.add(m[0])
        evs = m[1].vertices()
        nextv = evs[1] if evs[0] == m[0] else evs[0]
        if nextv in coastal_vertices:
            continue
        vs.add(nextv)
        new_h = 255
        max_h = max([height_from_vertex[v] for v in vs])
        while new_h >= max_h:
            new_h, v, e = sorted([(height_from_vertex[v], v, e) for v, e in nextv.edge_vertices()], key=lambda x: x[0])[-1]
            if new_h >= max_h and v not in vs and v not in coastal_vertices:
                max_h = new_h
                vs.add(v)
                edges.append(e)
                nextv = v
            else:
                river_vertices[nextv] = 0
                new_h = 0
        edges.reverse()
        for ind, e in enumerate(edges):
            river_edges[e] = (min(12, 4 + ind),1)
    type_from_pid = {}
    lakes = []  # This should be pids, not cubes
    for k in land_cubes:
        type_from_pid[pid_from_cube[k]] = "land"
    for k in sea_cubes:
        type_from_pid[pid_from_cube[k]] = "sea"
    for k in lakes:
        type_from_pid[k] = "lake"
    return continents, pid_from_cube, land_cube_from_pid, rid_from_pid, srid_from_pid, cont_from_pid, terr_from_cube, terr_from_pid, type_from_pid, height_from_vertex, land_height_from_cube, water_depth_from_cube, region_trees, pid_from_title, name_from_pid, name_from_rid, name_from_srid, impassable, river_edges, river_vertices, straits, locs_from_rid, coast_from_rid, coast_from_cube, tag_from_pid, sea_region


if __name__ == "__main__":
    with open("config.yml", 'r') as inf:
        config = yaml.load(inf, yaml.Loader)
    buffer = {}
    for k,v in config.items():  # We should compute the sizes of the templates here rather than making the user do it.
        if "SIZE_LIST" in k:
            sumk = k.replace("SIZE_LIST", "SIZE")
            if sumk not in config:
                if isinstance(v[0],list):
                    buffer[k.replace("SIZE_LIST", "DUCHY_LIST")] = [sum(x) for x in v]
                    buffer[sumk] = sum([sum(x) for x in v])
                else:
                    buffer[sumk] = sum(v)
    config.update(buffer)
    config["n_x"] = config.get("n_x", 129)
    config["n_y"] = config.get("n_y", 65)
    config["max_x"] = config.get("max_x", config.get("box_width", 10)*(config["n_x"]*3-3))
    config["max_y"] = config.get("max_y", config.get("box_height", 17)*(config["n_y"]*2-2))

    continents, pid_from_cube, land_cube_from_pid, rid_from_pid, srid_from_pid, cont_from_pid, terr_from_cube, terr_from_pid, type_from_pid, height_from_vertex, land_height_from_cube, water_depth_from_cube, region_trees, pid_from_title, name_from_pid, name_from_rid, name_from_srid, impassable, river_edges, river_vertices, straits, locs_from_rid, coast_from_rid, coast_from_cube, tag_from_pid, sea_region = create_data(config)
    cultures, religions = assemble_culrels(region_trees=region_trees)  # Not obvious this should be here instead of just derived later?
    rgb_from_pid = create_colors(pid_from_cube)
    pids_from_rid = {}
    for pid, rid in sorted(rid_from_pid.items()):
        if rid in pids_from_rid:
            pids_from_rid[rid].append(pid)
        else:
            pids_from_rid[rid] = [pid]
    pids_from_srid = {}
    for pid, rid in sorted(srid_from_pid.items()):
        if rid in pids_from_srid:
            pids_from_srid[rid].append(pid)
        else:
            pids_from_srid[rid] = [pid]
    rid_from_cube = {k: rid_from_pid[pid_from_cube[k]] for k in land_cube_from_pid.values()}
    supply_nodes, railways = create_supply_rails(terr_from_cube, pids_from_rid, rid_from_cube, land_cube_from_pid, pid_from_cube, name_from_rid,)
    weather_periods_from_srid = {}
    cont_names = ["europe", "asia", "africa", "north_america", "south_america", "oceania",]
    for srid in name_from_srid.keys():
        weather_periods_from_srid[srid] = [{
            "between": "{ 0.0 30.11}",
            "temperature": "{ 1.0 6.0 }",
            "no_phenomenon": "0.500",
            "rain_light": "0.250",
            "rain_heavy": "0.100",
            "snow": "0.000",
            "blizzard": "0.000",
            "arctic_water": "1.000",
            "mud": "1.000",
            "sandstorm": "0.000",
            "min_snow_level": "0.000",
        }]
    naval_from_srid = {}
    if "CK3" in config["MOD_OUTPUTS"]:
        ck3.create_mod(
            file_dir=config["MOD_OUTPUTS"]["CK3"],
            config=config,
            pid_from_cube=pid_from_cube,
            terr_from_cube=terr_from_cube,
            terr_from_pid=terr_from_pid,
            rgb_from_pid=rgb_from_pid,
            height_from_vertex=height_from_vertex,
            pid_from_title=pid_from_title,
            name_from_pid=name_from_pid,
            region_trees=region_trees,
            cultures=cultures,
            religions=religions,
            impassable=impassable,
            river_edges=river_edges,
            river_vertices=river_vertices,
            straits=straits,
            sea_region=sea_region,
        )
    if "EU4" in config["MOD_OUTPUTS"]:
        eu4.create_mod(
            file_dir=config["MOD_OUTPUTS"]["EU4"],
            config=config,
            region_trees=region_trees,
            rgb_from_pid=rgb_from_pid,
            name_from_pid=name_from_pid,
            pids_from_rid=pids_from_rid,
            name_from_rid=name_from_rid,
            pid_from_cube=pid_from_cube,
            terr_from_cube=terr_from_cube,
            gov_from_tag={},
            height_from_vertex=height_from_vertex,
            river_edges=river_edges,
            river_vertices=river_vertices,
            srid_from_pid=srid_from_pid,
            name_from_srid=name_from_srid,
            cont_names=cont_names,
            cont_from_pid=cont_from_pid,
        )
    if "V3" in config["MOD_OUTPUTS"]:
        v3.create_mod(
            file_dir=config["MOD_OUTPUTS"]["V3"],
            config=config,
            pid_from_cube=pid_from_cube,
            rid_from_pid=rid_from_pid,
            pids_from_rid=pids_from_rid,
            terr_from_cube=terr_from_cube,
            terr_from_pid=terr_from_pid,
            rgb_from_pid=rgb_from_pid,
            height_from_vertex=height_from_vertex,
            river_edges=river_edges,
            river_vertices=river_vertices,
            locs_from_rid=locs_from_rid,
            coast_from_rid=coast_from_rid,
            name_from_rid=name_from_rid,
            region_trees=region_trees,
            tag_from_pid=tag_from_pid,
            straits=straits,
        )
    if "HOI4" in config["MOD_OUTPUTS"]:
        hoi4.create_mod(
            file_dir=config["MOD_OUTPUTS"]["HOI4"],
            config=config,
            pid_from_cube=pid_from_cube,
            rgb_from_pid=rgb_from_pid,
            terr_from_cube=terr_from_cube,
            terr_from_pid=terr_from_pid,
            rid_from_pid=rid_from_pid,
            tag_from_pid=tag_from_pid,
            type_from_pid=type_from_pid,
            cont_from_pid=cont_from_pid,
            coast_from_cube=coast_from_cube,
            name_from_rid=name_from_rid,
            pids_from_rid=pids_from_rid,
            river_edges=river_edges,
            river_vertices=river_vertices,
            locs_from_rid=locs_from_rid,
            height_from_vertex=height_from_vertex,
            region_trees=region_trees,
            supply_nodes=supply_nodes,
            railways=railways,
            pids_from_srid=pids_from_srid,
            name_from_srid=name_from_srid,
            weather_periods_from_srid=weather_periods_from_srid,
            naval_from_srid=naval_from_srid,
        )
