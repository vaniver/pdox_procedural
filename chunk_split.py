# Version without custom class
import random

from cube import Cube


class SplitChunkMaxIterationExceeded(Exception):
    pass


def check_contiguous(chunk):
    """ Given a chunk (list of cubes), see if all cubes on the list can be reached from each other."""
    visited = {chunk[0]}
    to_visit = {cn for cn in chunk[0].neighbors() if cn in chunk}
    while len(to_visit) > 0:
        visiting = to_visit.pop()
        visited.add(visiting)
        to_visit = to_visit.union([cn for cn in visiting.neighbors() if cn in chunk and cn not in visited])
    return len(visited) == len(chunk)


def find_contiguous(cubes):
    """ Given an iterable of cubes, return a list of lists of cubes, each of which can be reached from each other."""
    unvisited = {x for x in cubes}
    result = []
    to_visit = set()
    visited = set()
    while len(unvisited) > 0:
        if len(to_visit) == 0:
            visiting = unvisited.pop()
            result.append([visiting])
            to_visit = {cn for cn in visiting.neighbors() if cn in unvisited}
            visited.add(visiting)
        else:
            visiting = to_visit.pop()
            unvisited.remove(visiting)
            visited.add(visiting)
            to_visit.update([cn for cn in visiting.neighbors() if cn in unvisited])
            result[-1].append(visiting)
    assert sum([len(x) for x in result]) == len(cubes)
    return result


def make_chunk(size, seed=0):
    """ Make a contiguous chunk of a given size """
    rng = random.Random(seed)
    cubes = set([Cube()])
    while len(cubes) < size:
        c = rng.choice(list(cubes))
        n = rng.choice(list(c.neighbors()))
        cubes.add(n)
    return cubes


def split_chunk_iter(chunk, sizes, neighbors, rng=None):
    """ Single step of split_chunk() """
    assert len(chunk) > len(sizes), f"{len(chunk)} !> {len(sizes)}"
    if not isinstance(rng, random.Random):
        rng = random
    # start by drawing three random items
    splits = [[c] for c in rng.sample(list(chunk), len(sizes))]
    unused = set(chunk) - set(sum(splits, []))
    max_iters = max(sizes) * len(sizes)  # worst case
    for j in range(max_iters):
        i = j % len(sizes)
        size = sizes[i]
        split = splits[i]
        if len(split) == size:
            continue
        # get all of the neighbors of the split
        candidates = set()
        for c in split:
            candidates |= neighbors[c]
        # filter to unused cubes
        candidates = candidates & unused
        if not candidates:
            return None
        # Pick a candidate at random and add it
        choice = rng.choice(list(candidates))
        split.append(choice)
        unused.remove(choice)
    return splits


def split_chunk(chunk, sizes, max_iter=1000, rng=None):
    """
    Split a chunk (list of cubes) into contiguous subsets of given sizes.

    chunk - list of cubes to split
    sizes - list of sizes to split into

    Returns a list of chunks (set of cubes) that correspond to the sizes.
    """
    assert len(chunk) == sum(sizes), f"{len(chunk)} != {sum(sizes)}"
    if not isinstance(rng, random.Random):
        rng = random
    # Precompute neighbors for each cube in the chunk
    neighbors = dict()
    for c in chunk:
        neighbors[c] = set(c.neighbors()) & set(chunk)
    for i in range(max_iter):
        result = split_chunk_iter(chunk, sizes, neighbors, rng)
        if result != None:
            return result
    raise SplitChunkMaxIterationExceeded("Ran out of iterations trying to split chunk")
