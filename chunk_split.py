# Version without custom class
import random

from cube import Cube
from doodle import Doodler


class SplitChunkMaxIterationExceeded(Exception):
    pass


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


def show_splits(chunk, splits):
    """ Draw a partially split chunk """
    assert len(splits) <= 3, f"only 3 colors supported for now"
    colors = (255, 0, 0), (0, 255, 0), (0, 0, 255)
    cubes = {c: (255, 255, 255) for c in chunk}
    for color, split in zip(colors, splits):
        for c in split:
            cubes[c] = color
    Doodler(cubes, size=(200,200)).show()


if __name__ == "__main__":
    for seed in range(10):
        chunk = make_chunk(12, seed=seed)
        try:
            splits = split_chunk(chunk, [4, 4, 4], rng=random.Random(seed))
            show_splits(chunk, splits)
        except SplitChunkMaxIterationExceeded:
            Doodler({c: (255, 255, 255) for c in chunk}, size=(200,200)).show()