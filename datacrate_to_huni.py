"""
Quick and dirty script to push Datacrate to and experimental huni XML output
"""

import json
import sys
import os
import re
import argparse
from xml.sax.saxutils import escape



class JSON_Index():
    def __init__(self, json_ld):
        self.json_ld = json_ld
        self.item_by_id = {}
        for item in json_ld["@graph"]:
            self.item_by_id[item["@id"]] = item


parser = argparse.ArgumentParser()

parser.add_argument('infile', help='Catalog file to load')
parser.add_argument('outfile', help='Name of xml file')


args = vars(parser.parse_args())

root_dir, _ = os.path.split(args['infile'])

with open(args["infile"], 'r') as cat:
    dc = json.load(cat)

#context = dc["@context"]
json_index = JSON_Index(dc)

xml = "<datacrate>\n"

for item in dc["@graph"]:
    if "@type" in item and  "RepositoryObject" in item["@type"]:
        xml += " <record>\n"

        for prop in item:
            if not isinstance(item[prop], list):
                vals = [item[prop]]
            else:
                vals = item[prop]
            
            for v in vals:
                id = ""
                if "@id" in v:
                    id = v["@id"];
                    if "name" in json_index.item_by_id[id]:
                        v = str(json_index.item_by_id[id]["name"])
                    else:
                        v= ""
                print(vals)
                print(v)
                xml += f'     <meta name="{prop}" ref="{id}">{escape(v)}</meta>\n'
        xml += " </record>\n"


xml += "</datacrate>"

with open(args["outfile"], 'w') as out:
    out.write(xml)

