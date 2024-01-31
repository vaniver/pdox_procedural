from enum import Enum

# HEIGHTMAP constants
WATER_HEIGHT = 18 # TODO: I think this is game-specific, fix that.

# RIVERS constants
MAJOR_RIVER_THRESHOLD = 9
RIVER_EXTEND = 3
RIVER_BRANCH_CHANCE = 0.5
SOURCE = 0
MERGE = 1
SPLIT = 2
WATER = 254
LAND = 255

BaseTerrain = Enum('BaseTerrain', 'plains farmlands hills mountains forest desert marsh jungle')
TERRAIN_HEIGHT = {
    BaseTerrain.farmlands: (0,1), BaseTerrain.plains: (0,1), BaseTerrain.marsh: (0,1), BaseTerrain.desert: (0,1),
    BaseTerrain.jungle: (1,3), BaseTerrain.forest: (1,3),
    BaseTerrain.hills: (1,5), 
    BaseTerrain.mountains: (3,10),
}

CK3Terrain = Enum('CK3Terrain','plains farmlands hills mountains desert desert_mountains oasis jungle forest taiga wetlands steppe floodplains drylands')
CK3Terrain_from_BaseTerrain = {
    BaseTerrain.plains: CK3Terrain.plains,
    BaseTerrain.farmlands: CK3Terrain.farmlands,
    BaseTerrain.hills: CK3Terrain.hills,
    BaseTerrain.mountains: CK3Terrain.mountains,
    BaseTerrain.forest: CK3Terrain.forest,
    BaseTerrain.desert: CK3Terrain.desert,
    BaseTerrain.marsh: CK3Terrain.wetlands,
    BaseTerrain.jungle: CK3Terrain.jungle,
}

EU4Terrain = Enum('EU4Terrain', 'grasslands farmlands hills mountains forest desert marsh jungle')
EU4Terrain_from_BaseTerrain = {
    BaseTerrain.plains: EU4Terrain.grasslands,
    BaseTerrain.farmlands: EU4Terrain.farmlands,
    BaseTerrain.hills: EU4Terrain.hills,
    BaseTerrain.mountains: EU4Terrain.mountains,
    BaseTerrain.forest: EU4Terrain.forest,
    BaseTerrain.desert: EU4Terrain.desert,
    BaseTerrain.marsh: EU4Terrain.marsh,
    BaseTerrain.jungle: EU4Terrain.jungle,
}

V3Terrain = Enum('V3Terrain', 'plains farmland hills mountain forest desert wetland jungle')
V3Terrain_from_BaseTerrain = {
    BaseTerrain.plains: V3Terrain.plains,
    BaseTerrain.farmlands: V3Terrain.farmland,
    BaseTerrain.hills: V3Terrain.hills,
    BaseTerrain.mountains: V3Terrain.mountain,
    BaseTerrain.forest: V3Terrain.forest,
    BaseTerrain.desert: V3Terrain.desert,
    BaseTerrain.marsh: V3Terrain.wetland,
    BaseTerrain.jungle: V3Terrain.jungle,
}

HOI4Terrain = Enum('HOI4Terrain', 'plains urban hills mountain forest desert marsh jungle')
HOI4Terrain_from_BaseTerrain = {
    BaseTerrain.plains: HOI4Terrain.plains,
    BaseTerrain.farmlands: HOI4Terrain.urban,
    BaseTerrain.hills: HOI4Terrain.hills,
    BaseTerrain.mountains: HOI4Terrain.mountains,
    BaseTerrain.forest: HOI4Terrain.forest,
    BaseTerrain.desert: HOI4Terrain.desert,
    BaseTerrain.marsh: HOI4Terrain.marsh,
    BaseTerrain.jungle: HOI4Terrain.jungle,
}