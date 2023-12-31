from cube import Cube
from alt_map import create_hex_map, valid_cubes
from functools import reduce
from itertools import permutations


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
    - weight_from_cube is a dictionary of cube tuples to numbers
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
    result = dict()
    mindistmap = dict()
    for cub in weight_from_cube.keys():
        dists = distmap.get(Cube(cub),{0:0})
        result[cub] = min(dists, key=dists.get)
        mindistmap[cub] = min(dists.values())
    return centers, result, mindistmap


def iterative_voronoi(num_centers, weight_from_cube, min_size, max_iters=5):
    """Given a set of weights, seed num_centers random centers and then keep going until all of the regions are at least min_size.
    Returns the pair of centers and ind_from_cube mapping."""
    assert num_centers * min_size < len(weight_from_cube)
    centers = random.sample(list(weight_from_cube.keys()),num_centers)
    centers, guess, distmap = voronoi(centers, weight_from_cube)
    sizes = {c:0 for c in range(num_centers)}
    means = {c:Cube(0,0,0) for c in range(num_centers)}
    for cub, ind in guess.items():
        sizes[ind] += 1
        means[ind].add_in_place(cub)
    print(sum([min_size <= sizes[ind] for ind in range(num_centers)]))
    if all([min_size <= sizes[ind] for ind in range(num_centers)]):
        return centers, guess
    iter = 1
    while not all([min_size <= sizes[ind] for ind in range(num_centers)]):
        to_remove = []
        for ind in range(len(centers)):
            if min_size <= sizes[ind]:
                x = means[ind].x // sizes[ind]
                y = means[ind].y // sizes[ind]
                z = -x-y
                centers[ind] = Cube(x,y,z)
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
        print(sum([min_size <= sizes[ind] for ind in range(num_centers)]))
    return centers, guess, distmap