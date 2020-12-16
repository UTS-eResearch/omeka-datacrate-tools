"""
Quick and dirty script to push Datacrate to an experimental huni XML output

HuNI has no standard input format this will need a custom harvester when I wrote this, the folks at Strategic Data handled that and we successfully imported data from Farms To Freeways.

This converts all of the items with a @type RepostitoryObject into an XML file with the following format - the first record is for a Person. A HuNI harvester can look for this...

<datacrate>
    <record>
     <meta name="@context" ref="">http://43.240.98.92/api-context</meta>
     <meta name="@id" ref="">http://43.240.98.92/api/items/24</meta>
     <meta name="@type" ref="">o:Item</meta>
     <meta name="@type" ref="">schema:Person</meta>
     <meta name="@type" ref="">RepositoryObject</meta>
     <meta name="schema:url" ref="https://siouxziconnor.com">https://siouxziconnor.com</meta>
     <meta name="dcterms:isPartOf" ref="http://43.240.98.92/api/item_sets/10">2003 Golden Eye Awards</meta>
     <meta name="name" ref="">Siouxzi Connor</meta>
     <meta name="description" ref="">Siouxzi Connor is an Australian-born writer and artist.
Her first book was published by Repeater Books and distributed by Penguin Random House in early 2017, titled ‘Little Houses, Big Forests (desire is no light thing).’ It was launched in London at the Tenderbooks Gallery and then in New York at Spoonbill Books, and soon to launch with an exhibition in Australia. It received coverage on the BBC World Service.
</meta>
     <meta name="description" ref="https://www.imdb.com/name/nm2424588/">https://www.imdb.com/name/nm2424588/</meta>
 </record>

    ...
    <record> </record>
</datacrate>
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
     
xml += "</datacrate>"
with open(os.path.join(args["outdir"], id.replace("/","_").replace(":","_").replace("&","_") + ".xml"), 'w') as out:
    out.write(xml)



