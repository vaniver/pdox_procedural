import os
from gen import *

for filename in os.listdir("data"):
    if not filename.endswith(".yml") or filename.endswith("_template.yml"):
        continue
    try:
        db = int(filename[:2])
    except:
        continue
    try:
        rt = RegionTree.from_yml(os.path.join("data", filename))[0]
    except:
        print(filename + " failed completely!")
    lb = len(rt.some_ck3_titles("b"))
    if lb != db:
        print(filename, lb, db)
    if rt.culture == "":
        print(filename, "missing culture!")
    if rt.religion == "":
        print(filename, "missing religion!")