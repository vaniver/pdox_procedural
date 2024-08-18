import yaml

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
    def __init__(self, title=None, tag=None, culture=None, religion=None, rough=None, holy_site=None, color=("0","0","0"), capital_title=None, capital_pid=-1, capital_rid=-1, children = []):
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
    
    def all_rough_pids(self, last_rough=""):
        """Returns a list of rough terrain mappings defined by this region_tree.
        Defaults to forest."""
        if self.rough is not None:
            last_rough = self.rough
        rough_list = []
        for child in self.children:
            if isinstance(child,RegionTree):
                rough_list.extend(child.all_rough_pids(last_rough=last_rough))
            else:
                rough_list.append(last_rough)
        return rough_list

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
    
    def size_list(self):
        """Returns a tuple of depth and the size_list implied by this region_tree, in the same format as the config.
        If children is ever a singleton--for example, a kingdom with only one duchy--it is passed thru b/c there's no splitting step necessary later.
        For example, this might be (1, [7,5,5,5]) for a center duchy, or (2, [[6,4,4,4,4],[4,4,3,3],[4,4,3,3],[4,4,3]]) for a player kingdom, or (0, 5) for a county with 5 baronies."""
        if len(self.children) == 0:
            return (0,[])
        if len(self.children) == 1 and isinstance(self.children[0], RegionTree):
            return self.children[0].size_list()
        if isinstance(self.children[0], str):
            return (0, len(self.children))
        result = []
        depth = 0
        for child in self.children:
            cd, cr = child.size_list()
            depth = max(depth, cd+1)
            result.append(cr)
        return (depth, result)

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
        rough = contents.get("rough", None)
        result = cls(title=title, color=color, tag=tag, culture=culture, religion=religion, rough=rough, holy_site=holy_site, capital_rid=last_rid, children=result_children)
        return result, last_pid, last_rid, last_srid, localization
            

    @classmethod
    def from_yml(cls, filename, last_pid=1, last_rid=1, last_srid=1):
        """Processes a .yml file to create a dictionary, which then is run thru from_dict. Also returns localization dictionary."""
        with open(filename, encoding='utf_8_sig') as inf:
            contents = yaml.load(inf, yaml.Loader)
        return cls.from_dict(contents, last_pid, last_rid, last_srid)

    @classmethod
    def from_eu4_dict(cls, contents, last_pid=1, last_rid=1, last_srid=1):
        """Given a dictionary of region details, recursively create a RegionTree. Also returns pid/rid/srid and localization dictionary."""
        children = contents.get("children", [])
        result_children = []
        if len(children) > 0 and isinstance(children[0], str):
            result_children = children
            last_pid += len(children)
        else:
            for child in children:
                result, last_pid, last_rid, last_srid = cls.from_eu4_dict(child, last_pid, last_rid, last_srid)
                result_children.append(result)
        title = contents["title"]  # This should break if it's not there
        if "area" in title:
            last_rid += 1
        if "region" in title:
            last_srid += 1
        culture = contents.get("cul", None)
        religion = contents.get("rel", None)
        holy_site = contents.get("holy", None)
        tag = contents.get("tag", None)
        rough = contents.get("rough", None)
        result = cls(title=title, color=None, tag=tag, culture=culture, religion=religion, rough=rough, holy_site=holy_site, capital_rid=last_rid, children=result_children)
        return result, last_pid, last_rid, last_srid
    
    @classmethod
    def from_eu4_yml(cls, filename, last_pid=1, last_rid=1, last_srid=1):
        """Processes a .yml file to create a dictionary, which is then run thru from_dict. """
        with open(filename, encoding='utf_8_sig') as inf:
            contents = yaml.load(inf, yaml.Loader)
        return cls.from_eu4_dict(contents, last_pid, last_rid, last_srid)