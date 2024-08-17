import random

from area import Area
from cube import Cube

def simple_voronoi(centers, weights_from_cube):
    """Uses the domain of weights_from_cube to determine which cubes are eligible to be filled.
    - centers is a list of cubes
    - weights_from_cube is a dictionary of cube tuples to numbers
    returns a dictionary of cube tuples to the index of the centers list that they correspond to."""
    centers = [Cube(x) for x in centers]  #If they're tuples, make them cubes.
    # If any of the centers are duplicates, delete them. This will unfortunately muck up the ordering.
    if len(centers) != sum([sum([x == c for x in centers]) for c in centers]):
        centers = list(set(centers))
    result = {}
    mindistmap = {}
    for cub in weights_from_cube.keys():
        dists = {cind:Cube(cub).dist(c) for cind, c in enumerate(centers)}
        result[cub] = min(dists, key=dists.get)
        mindistmap[cub] = dists[result[cub]]
    return centers, result, mindistmap


def voronoi(centers, weight_from_cube):
    """Uses the domain of weight_from_cube to determine which cubes are eligible to be filled.
    - centers is a list of cubes; if they aren't unique they will be made unique
    - weight_from_cube is a dictionary of cube tuples to numbers. Does not have to be connected!
    returns a dictionary of cube tuples to the index of the centers list that they correspond to, centers, and the distmap."""
    centers = [Cube(x) for x in centers]  #If they're tuples, make them cubes.
    # If any of the centers are duplicates, delete them. This will unfortunately muck up the ordering.
    if len(centers) != sum([sum([x == c for x in centers]) for c in centers]):
        centers = list(set(centers))
    # Overall strategy: 
    # - seed all of the centers with distance 0
    # - add all neighbors of the centers to expand sets with the weight of the center as the 'distance'
    # - while there are any elements in the expansion sets, pick the lowest distance one and expand it
    # - if it's the lowest distance to the cell it expands to, add that to the expansion set
    # = finally, point each cell at its lowest distance source. 
    distmap = {Cube(k):{} for k in weight_from_cube.keys()}
    # Each center is in its own voronoi cell
    for cind, center in enumerate(centers):
        distmap[center][cind] = 0
        to_explore = set([center])
        # explored = set()
        while len(to_explore) > 0:
            cub = to_explore.pop()
            base_dist = distmap[cub][cind] + weight_from_cube[cub]
            expanding = [c for c in cub.neighbors() if c in weight_from_cube ]  # and c not in explored]
            for other in expanding:
                if len(distmap[other]) == 0 or min(distmap[other].values()) > base_dist:
                    distmap[other][cind] = base_dist
                    to_explore.add(other)
                else:
                    continue            
    #TODO: This currently is 'kind of fast' but could be faster. Two possible improvements:
    # Instead of starting with center 1 and fully calculating the distances, start with all centers simultaneously.
    # The previous, but instead of having to argmin the to_explore queue each time, have the queue split out by distance so that it's obvious where the next place to go is.
    group_from_cube = dict()
    mindistmap = dict()
    for cub in weight_from_cube.keys():
        dists = distmap.get(Cube(cub),None)
        if dists is not None and len(dists) > 0:
            group_from_cube[cub] = min(dists, key=dists.get)
            mindistmap[cub] = min(dists.values())
    return centers, group_from_cube, mindistmap


def max_voronoi(centers, weight_from_cube, poss_centers, max_dist):
    """Uses the domain of weight_from_cube to determine which cubes are eligible to be filled.
    - centers is a list of cubes; if they aren't unique they will be made unique
    - weight_from_cube is a dictionary of cube tuples to numbers. Does not have to be connected!
    - poss_centers is a list of cubes that could be added to centers
    - max_dist is the maximum allowable distance of a center in poss_centers from a center on the list.
    If weight_from_cube is disconnected and none of the original centers are in a region, even if some elements of poss_centers are in that region they will not be added to centers.
    returns a dictionary of cube tuples to the index of the centers list that they correspond to, centers, and the distmap."""
    centers = [Cube(x) for x in centers]  #If they're tuples, make them cubes.
    centers = [x for x in centers if x in weight_from_cube]  # If they're not in the region, remove them.
    # If any of the centers are duplicates, delete them. This will unfortunately muck up the ordering.
    if len(centers) != sum([sum([x == c for x in centers]) for c in centers]):
        centers = list(set(centers))
    # Overall strategy: 
    # - seed all of the centers with distance 0
    # - add all neighbors of the centers to expand sets with the weight of the center as the 'distance'
    # - while there are any elements in the expansion sets, pick the lowest distance one and expand it
    # - if it's the lowest distance to the cell it expands to, add that to the expansion set
    # = finally, point each cell at its lowest distance source. 
    distmap = {Cube(k):{} for k in weight_from_cube.keys()}
    # Each center is in its own voronoi cell
    for cind, center in enumerate(centers):
        distmap[center][cind] = 0
        to_explore = set([center])
        # explored = set()
        while len(to_explore) > 0:
            cub = to_explore.pop()
            base_dist = distmap[cub][cind] + weight_from_cube[cub]
            expanding = [c for c in cub.neighbors() if c in weight_from_cube ]  # and c not in explored]
            for other in expanding:
                if len(distmap[other]) == 0 or min(distmap[other].values()) > base_dist:
                    distmap[other][cind] = base_dist
                    to_explore.add(other)
                else:
                    continue
    group_from_cube = dict()
    mindistmap = dict()
    for cub in weight_from_cube.keys():
        dists = distmap.get(Cube(cub),None)
        if dists is not None and len(dists) > 0:
            group_from_cube[cub] = min(dists, key=dists.get)
            mindistmap[cub] = min(dists.values())
    while len(mindistmap) > 0 and max(mindistmap.values()) > max_dist:
        eligible_centers = [c for c in poss_centers if c in mindistmap and mindistmap[c] > max_dist]
        if len(eligible_centers) == 0:  # idk how this could happen
            break
        center = random.choice(eligible_centers)
        centers.append(center)
        cind += 1
        distmap[center][cind] = 0
        mindistmap[center] = 0
        group_from_cube[center] = cind
        to_explore = set([center])
        while len(to_explore) > 0:
            cub = to_explore.pop()
            base_dist = distmap[cub][cind] + weight_from_cube[cub]
            expanding = [c for c in cub.neighbors() if c in weight_from_cube ]  # and c not in explored]
            for other in expanding:
                if len(distmap[other]) == 0 or mindistmap[other] > base_dist:
                    distmap[other][cind] = base_dist
                    mindistmap[other] = base_dist
                    group_from_cube[other] = cind
                    to_explore.add(other)
                else:
                    continue
    return centers, group_from_cube, mindistmap

def growing_voronoi(centers, region_sizes, weight_from_cube, group_from_cube=None):
    """Grow regions from their centers out to the appropriate size from region_sizes.
    Demands that all centers be unique.
    They'll steal from neighbors if necessary to reach the correct size."""
    centers = [Cube(x) for x in centers]  #If they're tuples, make them cubes.
    # If any of the centers are duplicates, delete them. This will unfortunately muck up the ordering.
    assert len(centers) == sum([sum([x == c for x in centers]) for c in centers])
    group_from_cube = {k: -1 for k in weight_from_cube}
    num_centers = len(centers)
    options = dict()
    easy_options = dict()
    for ind, cen in enumerate(centers):
        group_from_cube[cen] = ind
        options[ind] = {x: weight_from_cube[x] for x in cen.neighbors() if x in weight_from_cube}
    for ind, cen in enumerate(centers):
        easy_options[ind] = {k:v for k,v in options[ind].items() if group_from_cube[k] == -1}
    hist = {x:0 for x in range(-1,num_centers)}
    for v in group_from_cube.values():
        hist[v] += 1
    # At this point we know hist is {-1:lots, 0:1, ... n-1:1}
    poss = [v for v in range(num_centers) if hist[v] != region_sizes[v]]
    while len(poss) > 0:  # We still need to do a swap.
        # While we could start with the region that's the most off, that will preferentially fill the big regions first, which is not what we want.
        # Instead let's compute how many options each has and pick the one with the fewest options (in a weighted way).
        taker = random.choices(poss, weights=[2**(-len(easy_options[ind])) for ind in poss])[0]
        if len(easy_options[taker]) > 0:
            taken = min(easy_options[taker], key=options[taker].get)
        else: #We need to steal from someone else.
            ok_options = {k:v for k,v in options[taker].items() if len(easy_options[group_from_cube[k]]) > 0}
            taken = min(ok_options, key=options[taker].get)
        hist[group_from_cube[taken]] -= 1
        hist[taker] += 1
        if hist[taker] == region_sizes[taker]:
            poss.remove(taker)
        group_from_cube[taken] = taker
        for p in poss:
            if taken in easy_options[p]:
                easy_options[p].pop(taken)
        for tn in taken.neighbors():
            if tn not in weight_from_cube:
                continue
            elif tn in options[taker]:
                options[taker][tn] = min(options[taker][tn], options[taker][taken] + weight_from_cube[tn])
            else:
                options[taker][tn] = options[taker][taken] + weight_from_cube[tn]
            if group_from_cube.get(tn,0) == -1:
                easy_options[taker][tn] = options[taker][tn]
    return centers, group_from_cube
    

def iterative_voronoi(num_centers, weight_from_cube, min_size, max_iters=5):
    """Given a set of weights, seed num_centers random centers and then keep going until all of the regions are at least min_size.
    Returns the pair of centers and ind_from_cube mapping."""
    assert num_centers * min_size < len(weight_from_cube), (num_centers, min_size, len(weight_from_cube))
    centers = random.sample(list(weight_from_cube.keys()),num_centers)
    centers, guess, distmap = voronoi(centers, weight_from_cube)
    sizes = {c:0 for c in range(num_centers)}
    means = {c:Cube(0,0,0) for c in range(num_centers)}
    for cub, ind in guess.items():
        sizes[ind] += 1
        means[ind].add_in_place(cub)
    print(sum([min_size <= sizes[ind] for ind in range(num_centers)]))
    if all([min_size <= sizes[ind] for ind in range(num_centers)]):
        return centers, guess, distmap
    iter = 1
    while not all([min_size <= sizes[ind] for ind in range(num_centers)]):
        to_remove = []
        for ind in range(len(centers)):
            if min_size <= sizes[ind]:
                x = means[ind].x // sizes[ind]
                y = means[ind].y // sizes[ind]
                z = -x-y
                candidate = Cube(x,y,z)
                if candidate in weight_from_cube:
                    centers[ind] = candidate
                else:
                    centers[ind] = sorted([cub for cub, c_ind in guess.items() if c_ind == ind], key= lambda k: k.sub(candidate).mag())[0]
            elif sizes[ind] < min_size:
                to_remove.append(ind)
        argmaxes = sorted(sizes, key=sizes.get, reverse=True)
        for from_ind, to_ind in zip(to_remove, argmaxes):
            centers[from_ind] = random.sample([k for k,v in guess.items() if v==to_ind and k != centers[to_ind]], k=1)[0]
        centers, guess, distmap = voronoi(centers, weight_from_cube)
        iter += 1
        if iter >= max_iters:
            return centers, guess, distmap
        sizes = {c:0 for c in range(num_centers)}
        means = {c:Cube(0,0,0) for c in range(num_centers)}
        for cub, ind in guess.items():
            sizes[ind] += 1
            means[ind].add_in_place(cub)
    return centers, guess, distmap


def area_voronoi(area_from_cube, centers):
    """Given a dictionary area_from_cube which maps from cubes to area ids, and a list of centers (indices of the areas list), return a dictionary from area index to center index."""
    rid_from_aid = {}
    areas = {}
    aids = sorted(set(area_from_cube.values()))
    for aid in aids:
        areas[aid] = Area(aid, [k for k,v in area_from_cube.items() if v == aid])
        areas[aid].calc_edges(area_from_cube)
    distmap = {aid:{} for aid in aids}  # Each area will have a distance to other centers.
    for cind, center in enumerate(centers):
        if center in rid_from_aid: # We're going to silently remove duplicate centers instead of being loud about it. Maybe a mistake?
            continue
        rid_from_aid[center] = cind
        distmap[center][cind] = 0
        to_explore = set([center])
        while len(to_explore) > 0:
            next_area = to_explore.pop()
            base_dist = distmap[next_area][cind] + 1.
            for other, other_len in areas[next_area].self_edges.items():
                other_dist = base_dist + 1. / len(other_len)
                if len(distmap[other]) == 0 or min(distmap[other].values()) > other_dist:
                    distmap[other][cind] = other_dist
                    to_explore.add(other)
                else:
                    continue
    for aid in aids:
        dists = distmap.get(aid,{0:0})
        rid_from_aid[aid] = min(dists, key=dists.get)
    return rid_from_aid
    
