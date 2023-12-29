def spliterative_voronoi(num_centers, weight_from_cube, min_size, split_size, max_iters=5):
    """Starts off with num_centers voronoi cells and then splits any that are more than 2*split_size 
    (by adding n new centers in the cell, for each multiple) and removes any below min_size.
    Will return once all cells are above min_size and none are below split_size, or max_iters has passed."""
    centers = random.sample(list(weight_from_cube.keys()),num_centers)
    centers, guess = voronoi(centers, weight_from_cube)
    sizes = {c:0 for c in range(num_centers)}
    means = {c:Cube(0,0,0) for c in range(num_centers)}
    for cub, ind in guess.items():
        sizes[ind] += 1
        means[ind].add_in_place(cub)
    if all([min_size <= sizes[ind] for ind in range(num_centers)]) and all([2 * split_size > sizes[ind] for ind in range(num_centers)]):
        return centers, guess
    iter = 1
    while not (all([min_size <= sizes[ind] for ind in range(num_centers)]) and all([2 * split_size > sizes[ind] for ind in range(num_centers)])):
        # Alternate subtracting and splitting.
        new_centers = []
        for ind in range(len(centers)):
            if sizes[ind] < min_size:
                continue
            x = means[ind].x // sizes[ind]
            y = means[ind].y // sizes[ind]
            z = -x-y
            new_center = Cube(x,y,z)
            if new_center in weight_from_cube:
                new_centers.append(new_center)
            else:
                new_centers.append(centers[ind])
        centers = new_centers
        num_centers = len(centers)
        centers, guess = voronoi(centers, weight_from_cube)
        sizes = {c:0 for c in range(num_centers)}
        means = {c:Cube(0,0,0) for c in range(num_centers)}
        for cub, ind in guess.items():
            sizes[ind] += 1
            means[ind].add_in_place(cub)
        for ind in range(len(centers)):
            if sizes[ind] < min_size:
                continue
            x = means[ind].x // sizes[ind]
            y = means[ind].y // sizes[ind]
            z = -x-y
            new_center = Cube(x,y,z)
            if new_center in weight_from_cube:
                new_centers.append(new_center)
            else:
                new_centers.append(centers[ind])
            num_splits = sizes[ind] // split_size
            if num_splits > 1 and iter < max_iters -1:
                new_centers.extend(random.sample([k for k,v in guess.items() if v == ind], num_splits-1))
        centers = new_centers
        num_centers = len(centers)
        centers, guess = voronoi(centers, weight_from_cube)
        iter += 1
        if iter >= max_iters:
            return centers, guess
        sizes = {c:0 for c in range(num_centers)}
        means = {c:Cube(0,0,0) for c in range(num_centers)}
        for cub, ind in guess.items():
            sizes[ind] += 1
            means[ind].add_in_place(cub)
    return centers, guess