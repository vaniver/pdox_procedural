import os
import pickle
import random
import yaml

from eu4 import *
from gen import *
from map_io import *
from region_tree import RegionTree
from terrain import BaseTerrain, EU4Terrain, EU4Terrain_from_BaseTerrain

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

orig_rgb = {}
with open(os.path.join(config["BASE_EU4_DIR"], "map", "definition.csv")) as inf:
    for line in inf.readlines():
        sline = line.split(";")
        if len(sline)>0:
            try:
                pid = int(sline[0])
                r,g,b = [int(x) for x in sline[1:4]]
            except:
                continue
            orig_rgb[pid] = (r,g,b)

# China, Japan, India, Australia
random.seed(8964)
last_cid = 333
last_rid = 69
last_srid = 13
n_x = 117
n_y = 129
num_k = 3
weight_from_cube = {cub: random.randint(1,8) for cub in valid_cubes(n_x,n_y)}
num_centers = 80
centers, chunks, cids = create_chunks(weight_from_cube, num_centers)
candidates = compute_func(chunks, cids, num_k)
yearning = True
ind = -1
while yearning:
    ind += 1
    subweights = {k:v for k,v in weight_from_cube.items() if any([k in chunks[cid].members for cid in candidates[ind][0]])}
    try:
        china, terr_template, sea_centers = create_triangular_continent(subweights, chunks, candidates[ind], config)
        yearning = False
    except CreationError:
        print("Creation error")
        if ind == len(candidates) - 1:
            yearning = False
            print("Total error.")
china_inds = candidates[ind][0]
candidates = compute_func(chunks, cids, 4)
ind = 0
yearning = True
while yearning:
    ind += 1
    if any([cid in china_inds for cid in candidates[ind][0]]):
        continue
    subweights = {k:v for k,v in weight_from_cube.items() if any([k in chunks[cid].members for cid in candidates[ind][0]])}
    try:
        india, terr_template, sea_centers = create_triangular_continent(subweights, chunks, candidates[ind], config)
        yearning = False
    except CreationError:
        print("Creation error")
        if ind == len(candidates) - 1:
            yearning = False
            print("Total error.")
india_inds = candidates[ind][0]
aussi_possi = []
for chid, chunk in enumerate(chunks):
    if chid in china_inds or chid in india_inds:
        continue
    if chunk.outside:
        continue
    for nbr in chunk.self_edges.keys():
        if nbr in china_inds or nbr in india_inds:
            continue
    aussi_possi.append(chid)
eastmost = -1
eid = -1
for chid in aussi_possi:
    chunk = chunks[chid]
    if len(chunk.boundary) < 4+4+6+6:
        continue
    this_east = 0
    this_num = 0
    for member in chunk.members:
        this_east += member.x
        this_num += 1
    if this_east / this_num > eastmost:
        eastmost = this_east / this_num
        eid = chid
australia = {}  # This needs to be a dictionary because we're letting the number of baronies per border province vary.
aussi_coast = sorted([(len(members), members, oid) for oid, members in chunks[eid].other_edges.items()], reverse=True)
allocated = set()
adj_size_list = [x for x in config["KINGDOM_DUCHY_LIST"]]
adj_size_list[0] -= 6
if aussi_coast[1][2] in chunks[aussi_coast[0][2]].self_edges:
    raise CreationError
else:
    for border in [0,1]:
        cubes = aussi_coast[border][1]
        edges = [k for k in cubes if sum([ok in cubes for ok in k.neighbors()]) == 1]
        _, _, edist = voronoi([edges[0]], {k: 1 for k in cubes})
        ordered_cubes = [y[0] for y in sorted(edist.items(), key=lambda x: x[1])]
        for pind in range(6):
            for bind in range(pind*len(ordered_cubes)//6, (pind+1)*len(ordered_cubes)//6):
                australia[ordered_cubes[bind]] = pind + border * 6
    pid = 11  # increment before use
    # There will be some number of remaining chunks. Split them into contiguous groups.
    # TODO: Make this robust to longer strings of bordering regions
    first = [aussi_coast[2][2]] + [x[2] for x in aussi_coast[3:] if x[2] in chunks[aussi_coast[2][2]].other_edges]    
    second = [x[2] for x in aussi_coast[3:] if x[2] not in first]
    for chids in [first, second]:
        guaranteed = []
        subweights = {}
        for chid in chids:
            guaranteed.extend(chunks[eid].other_edges[chid])
            subweights.update({k:weight_from_cube[k] for k in chunks[chid].members if k not in guaranteed})
        subweights.update({k: 0 for k in guaranteed})
        _, gfc = growing_voronoi([guaranteed[0]], [config["KINGDOM_SIZE"]], subweights)
        kingdom = [x for x, y in gfc.items() if y == 0]
        cdistmap = {k: 1 for k in subweights}
        this_capital, ksplit = split_kingdom(kingdom, allocated, cdistmap, adj_size_list)
        pid += 1
        for k in this_capital:
            australia[k] = pid
        for dind, duchy in enumerate(ksplit):
            start_ind = 1 if dind == 0 else 0  # We don't need to split out the capital county for the capital duchy; it's already done for us.
            try:
                dsplit = split_chunk(duchy, config["KINGDOM_SIZE_LIST"][dind][start_ind:])
            except:
                print("Kingdom failed to split.")
                raise CreationError
            for county in dsplit:
                pid += 1
                for k in county:
                    australia[k] = pid
pid += 1
for k in chunks[eid].members:
    australia[k] = pid

# America
random.seed(1788)
n_x = 117
m_x = n_x//2
n_y = 129
m_y = -(n_y+m_x)//2
num_k = 3
weight_from_cube = {cub: random.randint(1,8) for cub in valid_cubes(n_x,n_y)}
center = Cube(m_x, m_y, -m_x-m_y)
_, _, cdistmap = voronoi([center], weight_from_cube)
slist = sorted(cdistmap.items(), key=lambda x: x[1])
america = {}  # Needs to be a dictionary b/c of different sizes. 0-indexed for easy adding.
rid_from_pid = {}
center_cubes = split_chunk([x[0] for x in slist[:24]], [6]*4)
for ind, cc in enumerate(center_cubes):
    for c in cc:
        america[c] = ind
    rid_from_pid[ind] = 0
pid = 3
rid = 0
great_plains_cubes = [x[0] for x in slist[24:240]]
sector_chunks = split_chunk(great_plains_cubes, [72]*3)
for sector in sector_chunks:
    areas = split_chunk(sector, [24]*3)
    for area in areas:
        rid += 1
        counties = split_chunk(area, [6]*4)
        for cc in counties:
            pid += 1
            rid_from_pid[pid] = rid
            for c in cc:
                america[c] = pid
annular_ring = [x[0] for x in slist[240:240+6*6*6*3]]
subweights = {k: weight_from_cube[k] for k in annular_ring}
_, grp_from_cube, _ = iterative_voronoi(3,subweights, 6*6*3)
for grp_ind in range(3):
    subweights = {k: weight_from_cube[k] for k, v in grp_from_cube.items() if v == grp_ind}
    _, area_from_cube, _ = iterative_voronoi(6,subweights, 6*3, max_iters=10)
    for area_ind in range(6):
        rid += 1
        area = [k for k, v in area_from_cube.items() if v == area_ind]
        thirds = split_chunk(area, [(x+1)*len(area)//3 - x*len(area)//3 for x in range(3)])
        for third in thirds:
            provs = split_chunk(third, [(x+1)*len(third)//2 - x*len(third)//2 for x in range(2)])
        # subweights = {k: weight_from_cube[k] for k, v in area_from_cube.items() if v == area_ind}
        # _, prov_from_cube, _ = iterative_voronoi(6,subweights, 1)
            for prov_ind in range(2):
                pid += 1
                rid_from_pid[pid] = rid
                # for prov in [k for k,v in prov_from_cube.items() if v == prov_ind]:
                for prov in provs[prov_ind]:
                    america[prov] = pid

# Africa
random.seed(1808)
n_x = 117
m_x = n_x//2
n_y = 129 // 2
m_y = -(n_y+m_x)//2
num_k = 3
weight_from_cube = {cub: random.randint(1,8) for cub in valid_cubes(n_x,n_y)}
num_centers = 40
centers, chunks, cids = create_chunks(weight_from_cube, num_centers)
candidates = compute_func(chunks, cids, num_k)
yearning = True
ind = -1
while yearning:
    ind += 1
    subweights = {k:v for k,v in weight_from_cube.items() if any([k in chunks[cid].members for cid in candidates[ind][0]])}
    try:
        africa, terr_template, sea_centers = create_triangular_continent(subweights, chunks, candidates[ind], config)
        yearning = False
    except CreationError:
        print("Creation error")
        if ind == len(candidates) - 1:
            yearning = False
            print("Total error.")
base_chunk = -1
for x in candidates[ind][0]:
    if sea_centers[0] in chunks[x].members:
        base_chunk = x
poss = [x for x in chunks[base_chunk].members if x.z + 1 < sea_centers[0].z and x not in africa]
grow_center = sorted(poss, key=lambda x: sea_centers[0].sub(x).mag())[0]
allocated = set()
adj_size_list = [x for x in config["KINGDOM_DUCHY_LIST"]]
adj_size_list[0] -= 6
subweights = {k: weight_from_cube[k] for k in poss}
_, gfc = growing_voronoi([grow_center], [config["KINGDOM_SIZE"]], subweights)
kingdom = [x for x, y in gfc.items() if y == 0]
cdistmap = {k: 1 for k in subweights}
this_capital, ksplit = split_kingdom(kingdom, allocated, cdistmap, adj_size_list)
pid += 1
for k in this_capital:
    africa.append(k)
for dind, duchy in enumerate(ksplit):
    start_ind = 1 if dind == 0 else 0  # We don't need to split out the capital county for the capital duchy; it's already done for us.
    try:
        dsplit = split_chunk(duchy, config["KINGDOM_SIZE_LIST"][dind][start_ind:])
    except:
        print("Kingdom failed to split.")
        raise CreationError
    for county in dsplit:
        pid += 1
        for k in county:
            africa.append(k)
left_chunk = -1
right_chunk = -1
for x in candidates[ind][0]:
    if sea_centers[1] in chunks[x].members:
        left_chunk = x
    if sea_centers[2] in chunks[x].members:
        right_chunk = x
poss = [k for k in chunks[left_chunk].members if (k.x - 1 > sea_centers[1].x or k.y + 1 < sea_centers[1].y) and k not in africa] + [k for k in chunks[right_chunk].members if (k.x + 1 < sea_centers[2].x or k.z - 1 > sea_centers[2].z) and k not in africa]
out_edge = [x for x in poss if any([nbr in africa for nbr in x.neighbors()])]
grow_centers = [sorted(out_edge, key=lambda x: sea_centers[1].sub(x).mag())[0]] + [sorted(poss, key=lambda x: sea_centers[2].sub(x).mag())[0]]
_, _, distmap = voronoi(grow_centers, {k: 1 for k in out_edge + grow_centers})
maxdist = max(distmap.values())
grow_centers.extend(random.sample([k for k,v in distmap.items() if v == maxdist], k=1))
grow_centers.extend(random.sample([k for k,v in distmap.items() if v == maxdist // 2], k=2))
subweights = {k: 1 if k in out_edge else weight_from_cube[k] for k in poss}
_, gfc = growing_voronoi(grow_centers, [config["KINGDOM_SIZE"]] * 2 + [config["CENTER_SIZE"]] + [config["BORDER_SIZE"]]*2, subweights)
bad_cube = [k for k,v in gfc.items() if v == 3 and any(gfc.get(nbr,-1) == 4 for nbr in k.neighbors())][0]
good_spot = [k for k,v in gfc.items() if v == -1 and all(gfc.get(nbr,-1) != -1 for nbr in k.neighbors())][0]
gfc[good_spot] = gfc[bad_cube]
gfc[bad_cube] = -1
rgb_from_ijk = {k.tuple(): (128,128,128) for k in africa}
for k,v in gfc.items():
    if v < 0:
        continue
    rgb_from_ijk[k.tuple()] = (255,40*v,255-40*v)
for gid in [0,1]:
    kingdom = [x for x, y in gfc.items() if y == gid]
    cdistmap = {k: 1 for k in subweights}
    this_capital, ksplit = split_kingdom(kingdom, allocated, cdistmap, adj_size_list)
    pid += 1
    for k in this_capital:
        africa.append(k)
    for dind, duchy in enumerate(ksplit):
        start_ind = 1 if dind == 0 else 0  # We don't need to split out the capital county for the capital duchy; it's already done for us.
        try:
            dsplit = split_chunk(duchy, config["KINGDOM_SIZE_LIST"][dind][start_ind:])
        except:
            print("Kingdom failed to split.")
            raise CreationError
        for county in dsplit:
            pid += 1
            for k in county:
                africa.append(k)
gid = 2
dsplit = split_chunk([x for x, y in gfc.items() if y == gid], config["CENTER_SIZE_LIST"])
for county in dsplit:
    pid += 1
    for k in county:
        africa.append(k)
for gid in [3,4]:
    dsplit = split_chunk([x for x, y in gfc.items() if y == gid], config["BORDER_SIZE_LIST"])
    for county in dsplit:
        pid += 1
        for k in county:
            africa.append(k)

# Put it all together
max_x = 5632
max_y = 2048
n_x = 470
n_y = 129
vc = valid_cubes(n_x=n_x,n_y=n_y,)
s_x = n_x // 4
m_x = s_x // 2
m_y = -(n_y+m_x)//2
# Old world
# Somehow import the old world
max_srid = 0
max_rid = 0
name_from_rid = {}
srid_from_rid = {}
with open("geographical_region.txt") as inf:
    for line in inf.readlines():
        if line.startswith("\t\td"):
            max_srid += 1
            for name in [x[2:]+"_area" for x in line.strip().split(" ")]:
                max_rid += 1
                name_from_rid[max_rid] = name
                srid_from_rid[max_rid] = max_srid
title = ""
title_from_cid = {}
pids_from_cid = {}
cid_from_pid = {}
cid = 0
with open("00_landed_titles.txt") as inf:
    for line in inf.readlines():
        if "\tc_" in line and "=" in line:
            title = line.split("=")[0].strip()
            cid += 1
            title_from_cid[cid] = title
        if "province =" in line:
            pid = int(line.split("=")[1].strip())
            cid_from_pid[pid] = cid
            if cid in pids_from_cid:
                pids_from_cid[cid].append(pid)
            else:
                pids_from_cid[cid] = [pid]
with open("pid_from_cube-med.txt", 'rb') as inf:
    pid_from_cube, med = pickle.load(inf)
max_pid = max(pid_from_cube.values())
southern_tip = min([(x.y, x) for x in pid_from_cube.keys()])[1]
offset = Cube(s_x + m_x, -n_y + 5 - (s_x + m_x) // 2 - (s_x + m_x) % 2, n_y - 5 - (s_x + m_x)//2).sub(southern_tip)
print(offset)
cid_from_cube = {}
seen_pids = {}
for cube, pid in pid_from_cube.items():
    if pid in cid_from_pid:
        cid_from_cube[cube.add(offset)] = cid_from_pid[pid]
    else:
        if pid in seen_pids:
            cid_from_cube[cube.add(offset)] = seen_pids[pid]
        else:
            max_pid += 1
            seen_pids[pid] = max_pid
            cid_from_cube[cube.add(offset)] = max_pid
tfp = {}
with open("00_province_terrain.txt") as inf:
    for line in inf.readlines():
        try:
            sline = line.split("=")
            pid = int(sline[0])
            terr = EU4Terrain_from_BaseTerrain[BaseTerrain[sline[1].strip()]]
            tfp[pid] = terr
        except:
            continue
terr_from_cube = {}
terr_from_cid = {}
cube_from_pid = {v:k for k,v in pid_from_cube.items()}
for cid in range(1, 291):
    terrs = []
    for pid in pids_from_cid[cid]:
        terr_from_cube[cube_from_pid[pid]] = tfp[pid]
        terrs.append(tfp[pid])
    if len(terrs) > 5:
        terr_from_cid[cid] = EU4Terrain.farmlands
    else:
        terr_from_cid[cid] = random.choice(terrs)
rgb_from_cid = {}
for cid in range(291):
    rgb_from_cid[cid] = assign_color(rgb_from_cid,True)
for cid in range(291,max_pid+1):
    rgb_from_cid[cid] = assign_color(rgb_from_cid,False)
# TODO: populate both of these
rid_from_pid = {}  # max_rid already computed
srid_from_pid = {}  # max_srid already computed
# China / India
# These are continent lists; we need to calculate the pids for ourselves as we go along.
offset = Cube(s_x * 2, -s_x, -s_x)
china_size_list = [config["CENTER_SIZE_LIST"]] + [config["BORDER_SIZE_LIST"]] * 3  + [config["KINGDOM_SIZE_LIST"]] * 3 
india_size_list = [config["CENTER_SIZE_LIST"]] * 2 + [config["BORDER_SIZE_LIST"]] * 5  + [config["KINGDOM_SIZE_LIST"]] * 4
for cont_list, cont_size_list in [(china, china_size_list), (india, india_size_list)]:
    ind = 0
    max_srid += 1
    for size_list in cont_size_list:
        if isinstance(size_list[0], int):  # It's an area
            max_rid += 1
            srid_from_rid[max_rid] = max_srid
            for size in size_list:
                max_pid += 1
                rgb_from_cid[max_pid] = assign_color(rgb_from_cid,True)
                rid_from_pid[max_pid] = max_rid
                for cc in range(size):
                    cid_from_cube[cont_list[ind].add(offset)] = max_pid
                    ind += 1
        else:
            for sl in size_list:
                assert isinstance(sl[0], int)
                max_rid += 1
                srid_from_rid[max_rid] = max_srid
                for size in sl:
                    max_pid += 1
                    rgb_from_cid[max_pid] = assign_color(rgb_from_cid,True)
                    rid_from_pid[max_pid] = max_rid
                    for cc in range(size):
                        cid_from_cube[cont_list[ind].add(offset)] = max_pid
                        ind += 1
# Australia (same offset)
max_srid += 1
max_rid += 1
srid_from_rid[max_rid] = max_srid
for k,v in australia.items():
    cid_from_cube[k.add(offset)] = max_pid + v + 1
for _ in range(max(australia.values())+1):
    max_pid += 1
    rgb_from_cid[max_pid] = assign_color(rgb_from_cid,True)
# Africa
offset = Cube(s_x, -m_x, m_x-s_x)
max_srid += 1
max_rid += 1
srid_from_rid[max_rid] = max_srid
africa_size_list = [config["CENTER_SIZE_LIST"]] + [config["BORDER_SIZE_LIST"]] * 3  + [config["KINGDOM_SIZE_LIST"]] * 6 + [config["CENTER_SIZE_LIST"]] + [config["BORDER_SIZE_LIST"]] * 2
ind = 0
for size_list in africa_size_list:
    if isinstance(size_list[0], int):  # It's an area
        max_rid += 1
        srid_from_rid[max_rid] = max_srid
        for size in size_list:
            max_pid += 1
            rgb_from_cid[max_pid] = assign_color(rgb_from_cid,True)
            rid_from_pid[max_pid] = max_rid
            for cc in range(size):
                cid_from_cube[africa[ind].add(offset)] = max_pid
                ind += 1
    else:
        for sl in size_list:
            assert isinstance(sl[0], int)
            max_rid += 1
            srid_from_rid[max_rid] = max_srid
            for size in sl:
                max_pid += 1
                rgb_from_cid[max_pid] = assign_color(rgb_from_cid,True)
                rid_from_pid[max_pid] = max_rid
                for cc in range(size):
                    cid_from_cube[africa[ind].add(offset)] = max_pid
                    ind += 1
# America (diff offset)
max_srid += 1
offset = Cube(0, 0, 0)  # Doing this for uniformity's sake
america_size_list = [[[4] * 10]] + [[6] * 6] * 3 + [config["KINGDOM_SIZE_LIST"]] * 9  # Not needed b/c America handles it correctly?
for k,v in america.items():
    cid_from_cube[k.add(offset)] = v + max_pid + 1
for _ in range(max(america.values())+1):
    max_pid += 1
    rgb_from_cid[max_pid] = assign_color(rgb_from_cid,True)
print("Land:", max_pid)
create_hex_map(rgb_from_ijk={k.tuple():rgb_from_cid[v] for k,v in cid_from_cube.items()}, max_x=max_x, n_x=n_x, max_y=max_y, n_y=n_y,).save("land_provinces.bmp")

coastal = [k for k in vc if k not in cid_from_cube and any([nbr in cid_from_cube for nbr in k.neighbors()])]
shallow = sorted(set([nbr for k in coastal for nbr in k.neighbors() if nbr not in cid_from_cube and nbr in vc]))
shallows = find_contiguous(shallow)
impassable = []
center_from_pid = {}
for region in shallows:
    if len(region) < 10:
        max_pid += 1
        impassable.append(max_pid)
        rgb_from_cid[max_pid] = assign_color(rgb_from_cid,False)
        for k in region:
            cid_from_cube[k] = max_pid
    else:
        max_rid += 1
        this_coastal = [k for k in region if k in coastal]
        centers, grp_from_cube, _ = max_voronoi(random.sample(this_coastal, k=1), {k: 1 for k in region}, this_coastal, 5)
        cid_from_cube.update({k: v+max_pid+1 for k,v in grp_from_cube.items()})
        for ind, center in enumerate(centers):
            max_pid += 1
            rid_from_pid[max_pid] = max_rid
            center_from_pid[max_pid] = center
            rgb_from_cid[max_pid] = assign_color(rgb_from_cid,False)
for k in shallow:
    for nbr in k.neighbors():
        if nbr not in cid_from_cube and sum([nn in cid_from_cube for nn in nbr.neighbors()]) >= 4:
            poss = [cid_from_cube[nn] for nn in nbr.neighbors() if nn in cid_from_cube]
            cid_from_cube[nbr] = random.choice(poss)
print("Shallows:", max_pid)
ocean = set([k for k in vc if k not in cid_from_cube.keys()])
centers, grp_from_cube, distmap = max_voronoi([Cube(2,-2,0)], {k: 1 for k in ocean}, ocean, 7)
for k, v in grp_from_cube.items():
    cid_from_cube[k] = max_pid + v + 1
for v in range(max(grp_from_cube.values()) + 1):
    max_pid += 1
    center_from_pid[max_pid] = centers[v]
    rgb_from_cid[max_pid] = assign_color(rgb_from_cid,False)
print("Ocean:", max_pid)

emap = EU4Map("", max_x=max_x, max_y=max_y, n_x=n_x, n_y=n_y)
emap.create_provinces(orig_rgb, pid_from_cube, ".bmp")
emap.create_terrain(terr_from_cube, config["BASE_EU4_DIR"], ".bmp")
