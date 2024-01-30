import random
import yaml

from alt_map import create_hex_map, valid_cubes
from area import Area
from chunk_split import check_contiguous, split_chunk, SplitChunkMaxIterationExceeded
from voronoi import growing_voronoi, voronoi

# CENTER_SIZE_LIST = [7,5,5,5]
# CENTER_SIZE = sum(CENTER_SIZE_LIST)
# KINGDOM_SIZE_LIST = [[6,4,4,4,4], [4,4,3,3], [4,4,3,3], [4,4,3]]
# KINGDOM_DUCHY_LIST = [sum(x) for x in KINGDOM_SIZE_LIST]
# KINGDOM_SIZE = sum(KINGDOM_DUCHY_LIST)
# BORDER_SIZE_LIST = [4,4,4,4,4,4]
# BORDER_SIZE = sum(BORDER_SIZE_LIST)

class CreationError(Exception):
    pass

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
    a,b,c = candidate[0]
    abc_center = list(chunks[a].self_edges[b].intersection(chunks[a].self_edges[c]))[0]
    _, _, cdistmap = voronoi([abc_center], weight_from_cube)
    cube_from_pid = [abc_center] + list(abc_center.neighbors())
    # We're going to mostly hardcode how the central duchy works.
    if not all([x in weight_from_cube for x in cube_from_pid]):  # Check to make sure the center is actually contained.
        raise CreationError
    # Add the three counties to the central duchy, each one carved out of a different original region.
    for cid, other in enumerate([a,b,c]):
        options = {k:weight_from_cube[k] for k in cdistmap.keys() if k in chunks[other].members and k not in cube_from_pid}
        _, _, selection = voronoi([min(options, key=cdistmap.get)],options)
        ss = sorted(selection, key=selection.get)
        for k in ss[:config["CENTER_SIZE_LIST"][cid+1]]:
            cube_from_pid.append(k)
    allocated = set([x for x in cube_from_pid])
    # Set up the centers for the annular regions
    new_centers = []
    # Add the borders
    for o1, o2 in [(a,b),(b,c),(a,c)]:
        options = {k for k in chunks[o1].self_edges[o2].union(chunks[o1].other_edges[o2]) if k not in allocated}
        new_centers.append(min(options, key=cdistmap.get))
    # Add the kingdoms
    for o in [a,b,c]:
        options = {k: min([k.sub(nc).mag() for nc in new_centers[:3]]) for k in chunks[o].members if k not in allocated and any([kn in allocated for kn in k.neighbors()])}
        new_centers.append(max(options, key=options.get))
    subweights = {k:v for k,v in weight_from_cube.items() if k not in allocated}
    new_centers, group_from_cube = growing_voronoi(new_centers, [config["BORDER_SIZE"]]*3 + [config["KINGDOM_SIZE"]]*3, subweights)
    # Split the border duchies into counties
    for ind in range(3):
        duchy = [k for k,v in group_from_cube.items() if v==ind]
        try:
            counties = split_chunk(duchy, config["BORDER_SIZE_LIST"])
        except:  # Covers both difficult-to-split and incorrectly-sized regions.
            raise CreationError
        for county in counties:
            cube_from_pid.extend(county)
    # Split the kingdoms into duchies
    adj_size_list = [x for x in config["KINGDOM_DUCHY_LIST"]]
    adj_size_list[0] -= 6
    for kind in range(3,6):  # 3 border duchies - 3 kingdoms
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
                        raise CreationError
        if not to_be_continued:
            cube_from_pid.extend(this_capital)
            for dind, duchy in enumerate(ksplit):
                start_ind = 1 if dind == 0 else 0  # We don't need to split out the capital county for the capital duchy; it's already done for us.
                try:
                    dsplit = split_chunk(duchy, config["KINGDOM_SIZE_LIST"][dind][start_ind:])
                except:
                        raise CreationError
                for county in dsplit:
                    cube_from_pid.extend(county)
    return cube_from_pid
    

def create_triangle_continents(size_list, weight_from_cube = None, n_x=129, n_y=65, num_centers=40):
    """Create len(size_list) continents with size_list kingdoms. (Currently ordered from smallest to largest.)
    Uses the standard triangle-border system, which requires size_list to have elements between 3 and 5."""
    assert max(size_list) <= 3
    assert min(size_list) >= 3
    continents = []
    if weight_from_cube is None:
        weight_from_cube = {cub: random.randint(1,8) for cub in valid_cubes(n_x,n_y)}
    centers, chunks, cids = create_chunks(weight_from_cube, num_centers)
    ind = -1
    for cind, size in enumerate(size_list):
        candidates = compute_func(chunks, cids, size)
        while len(continents) <= cind:
            ind += 1
            print(ind)
            subweights = {k:v for k,v in weight_from_cube.items() if any([k in chunks[cid].members for cid in candidates[ind][0]])}
            try:
                continents.append(create_triangular_continent(subweights, chunks, candidates[ind]))
            except CreationError:
                print("Creation error")
                if ind == len(candidates):
                    print(f"Failed to make enough of size {size}, had to rechunk.")
                    centers, chunks, cids = create_chunks(subweights, num_centers)
                    candidates = compute_func(chunks, cids, size)
                    ind = -1
    return continents


def assign_terrain_subregion(region, template):
    """Assign terrain to the region according to the template."""
    pass


def assign_terrain_continent(region, templates):
    """Assign terrain to the continent according to the template list.
    Also generates the heightmap."""
    pass


def arrange_triangle_continents(continents):
    """Given three continents, arrange them to have straits around a central inner sea."""
    assert len(continents) == 3


if __name__ == "__main__":
    with open("config.yaml", 'r') as inf:
        config = yaml.load(inf, yaml.Loader)
    for k,v in config.items():  # We should compute the sizes of the templates here rather than making the user do it.
        if "SIZE_LIST" in k:
            sumk = k.replace("SIZE_LIST", "SIZE")
            if sumk not in config:
                if type(v[0]) is list:
                    config[sumk] = [sum(x) for x in v]
                else:
                    config[sumk] = sum(v)
    random.seed(config.get("seed", 1945))
    n_x = config.get("n_x", 129)
    n_y = config.get("n_x", 65)
    rgb_from_ijk = {cub.tuple():(random.randint(0,64), random.randint(0,64), random.randint(0,64)) for cub in valid_cubes(n_x,n_y)}
    max_x = config.get("box_width", 10)*(n_x*3-3)
    max_y = config.get("box_height", 17)*(n_y*2-2)
    continents = create_triangle_continents(config.get("size_list", [3,3,3]), n_x=n_x, n_y=n_y, num_centers=config.get("num_centers", 40))
    for cind, cont in enumerate(continents):
        print(cind, len(cont), cont[0], cont[-1])
        for pid, k in enumerate(cont):
            color_tuple = (62*(cind+1),min(255,pid),0)
            rgb_from_ijk[k.tuple()] = color_tuple[cind:] + color_tuple[:cind]
    img = create_hex_map(rgb_from_ijk, max_x,max_y,n_x,n_y)
    img.show()
    img.save("continent_test.png")