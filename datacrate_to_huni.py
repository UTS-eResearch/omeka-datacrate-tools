"""
Quick and dirty script to push Datacrate to and experimental huni XML output
"""

import json
import sys
import os
import re
import argparse
from xml.sax.saxutils import escape as esc


def escape(s):
    return esc(s).replace("&","_")
class JSON_Index():
    def __init__(self, json_ld):
        self.json_ld = json_ld
        self.item_by_id = {}
        for item in json_ld["@graph"]:
            self.item_by_id[item["@id"]] = item


parser = argparse.ArgumentParser()

parser.add_argument('infile', help='Catalog file to load')
parser.add_argument('outdir', help='Name of xml file')


args = vars(parser.parse_args())

root_dir, _ = os.path.split(args['infile'])

with open(args["infile"], 'r') as cat:
    dc = json.load(cat)

#context = dc["@context"]
json_index = JSON_Index(dc)

def get_value(val):
    if isinstance(val, dict):
        if "@name" in val:
            return val["@name"]
        elif "@value" in val:
            return val["@value"]
    elif isinstance(val, str):
        return val
    else: 
        return ""


for item in dc["@graph"]:
    if "@type" in item and  "RepositoryObject" in item["@type"]:
        xml = " <record>\n"

        for prop in item:
            if not isinstance(item[prop], list):
                vals = [item[prop]]
            else:
                vals = item[prop]
            
            for v in vals:
                id = ""
                if "@id" in v:
                    id = v["@id"];
                    if id in json_index.item_by_id:
                        if  "name" in json_index.item_by_id[id]:
                            v = escape(get_value(json_index.item_by_id[id]["name"][0]))
                        else:
                            v = id
                    else:
                         v = id

                if isinstance(v, dict) and "@value" in v:
                    v = v["@value"]

                print(v)
                
                xml += f'     <meta name="{escape(prop)}" ref="{escape(id)}">{escape(v)}</meta>\n'
        xml += " </record>\n"
        with open(os.path.join(args["outdir"], id.replace("/","_").replace(":","_").replace("&","_") + ".xml"), 'w') as out:
             out.write(xml)


xml += "</datacrate>"



