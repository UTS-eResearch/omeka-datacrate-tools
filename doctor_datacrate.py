import argparse
import json
import sys

"""
Tries to link within a datacrate by looking for value that reference a known
title or name

"""
parser = argparse.ArgumentParser()
parser.add_argument("infile", nargs="?", type=argparse.FileType("r"), default=sys.stdin)
parser.add_argument(
    "outfile", nargs="?", type=argparse.FileType("w"), default=sys.stdout
)
parser.add_argument(
    "-m", "--mapping", type=argparse.FileType("r"), help="JSON mapping file"
)
parser.add_argument("-n", "--no-link", default=False, action='store_true', help="Don't try to cross-link items (eg for Omeka S exports)")
parser.add_argument("-r", "--remove-omeka-namespace", default=False, action='store_true', help="Remove and keys from the Omeka S namespace after mapping")

args = vars(parser.parse_args())
catalog = json.load(args["infile"])
if args["mapping"]:
    mapper = json.loads(args["mapping"].read())
else:
    mapper = {}

# Build a table of names
names = {}

# Look up external mapping table and add new data
items_to_remove = []
for item in catalog["@graph"]:
    keys = list(item.keys())
    for k in keys:
        if k in mapper:
            item[mapper[k]] = item[k]
            items_to_remove.append(k)

# Remove old data
for item in catalog["@graph"]:
    for k in items_to_remove:
        if k in item:
            item.pop(k)

    for k, v in item.items():
        if not isinstance(v, list):
            v = [v]
        for val in v:
            if k == "title" or k == "name":
                if isinstance(val, dict):
                    if "@value" in val:
                        names[val["@value"]] = item["@id"]
                    elif "@label" in val:
                        names[val["@label"]] = item["@id"]
                else:
                    names[val] = item["@id"]

for item in []:  # catalog["@graph"]:
    for k, v in item.items():
        if not isinstance(v, list):
            v = [v]
        if k not in ["title", "name", "@id", "@type"]:
            item[k] = []
            for val in v:
                if str(val) in names:
                    item[k].append({"@id": names[val], "@label": val})
                else:
                    item[k].append(val)


if args["remove_omeka_namespace"]:
    for item in catalog["@graph"]:
        to_remove = set()
        for k, v in item.items():
            if not isinstance(v, list):
                v = [v]
                
            if k.startswith("o:"):
                to_remove.add(k)
        for remove_key in to_remove:
                item.pop(remove_key)
             
            

with args["outfile"] as new:
    new.write(json.dumps(catalog, indent=2))
