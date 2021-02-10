
import json
import shelve
import requests
import sys
import logging
import os
import hashlib
import re
import argparse

import subprocess



class Properties():
    def __init__(self):
        self.prop_ids = {}
    
    def get_prop_id(self, nom):
        if nom in self.prop_ids:
            return self.prop_ids[nom]

        elif nom in context:
            name = context[nom]
            if "@id" in name:
                name = name["@id"]
            # HACK - need to deal with other vocabs at some point
            name = name.replace("http://schema.org/", "schema:")
            url = "%sproperties?%s&per_page=1&term=%s" % (host_url, auth, name)
            res = requests.get(url)
            prop_data = res.json()
            #print(prop_data)
            if prop_data and "o:id" in prop_data[0]:
                print(nom, prop_data)
                self.prop_ids[nom] = prop_data[0]["o:id"]
                #print("Getting prop.", nom, self.prop_ids[nom])
                return self.prop_ids[nom]

        else:
            return None

class JSON_Index():
    def __init__(self, json_ld):
        self.json_ld = json_ld
        self.item_by_id = {}
        for item in json_ld["@graph"]:
            self.item_by_id[item["@id"]] = item

class Resource_classes():
      def __init__(self):
          self.class_ids = {}

      def get_class_id(self,names):
          if not isinstance(names, list):
             names = [names]
          print("Gettng CLASSES", names)
          for nom in names:
              
              if nom in self.class_ids:
                  return self.class_ids[nom]
              elif nom in context:
                  name = context[nom]
                  # HACK HACK HACK
                  name = name.replace("http://schema.org/", "schema:")

                  if "@id" in name:
                      name = name["@id"]
                  url = "%sresource_classes?%s&per_page=100000&term=%s" % (host_url, auth, name)
                  print(url)
                  r = requests.get(url)
                  #print(r.content)
                  prop_data = r.json()

                  if prop_data and "o:id" in prop_data[0]:
                      self.class_ids[nom] = prop_data[0]["o:id"]
                      print("CLASS", self.class_ids[nom])
                      return self.class_ids[nom]

                  else:
                       #print("Can't find this class", name )
                       return None


props = Properties()
classes = Resource_classes()

# TODO - turn these into parameters


parser = argparse.ArgumentParser()
parser.add_argument('-u', '--api-url',default=None, help='Omeka API Endpoint URL (hint, ends in /api/)')
parser.add_argument('-f', '--files', action="store_true", help='Upload files - default is false')
parser.add_argument('-s', '--shelf', default="saved_data", help='Where to stash intermediate results')
parser.add_argument('-d', '--download_cache', default="./content", help='Path to a directory in which to chache dowloads (defaults to ./data)')
parser.add_argument('-j', '--json-ld', default="./CATALOG.json", help="Datacrate style JSON-LD file")
parser.add_argument('infile', help='Catalog file to load')



args = vars(parser.parse_args())

root_dir, _ = os.path.split(args['infile'])

with open(args["infile"], 'r') as cat:
    dc = json.load(cat)
cont = dc["@context"]
context = {}

if isinstance(cont, str):
    r = requests.get(cont)
    context.update(r.json()["@context"])

else:
    for c in cont:
        if isinstance(c, dict):
            context.update(c)
        elif c.startswith("http"):
            r = requests.get(c)
            context.update(r.json()["@context"])



json_index = JSON_Index(dc)

# Hack ... not sure if this is the best way but Omeka seems to be built around having these on every page
context["name"] = "dcterms:title"
context["description"] = "dcterms:description"

key_identity = os.environ['OMEKA_KEY_IDENTITY']
key_credential = os.environ['OMEKA_KEY_CREDENTIAL']

host_url = args["api_url"]
upload_files = args["files"]

if not host_url.endswith("/"):
    host_url += "/"# "http://localhost/api/"
# Don't treat files as primary objects only upload to parent item with hasFile

shelf = shelve.open(args["shelf"]) # Remember what's been uploaded before keyed by datacrate ID
lookup_collection = {} # Keyed by datacrate id, lists omeka IDs for collections




auth = "key_identity=%s&key_credential=%s" % (key_identity, key_credential)
json_header =  {'Content-Type': 'application/json'};



        

# Item sets (collections)
for item in [col for col in dc["@graph"] if  "RepositoryCollection"  in col["@type"] ]:
    item_set_to_upload = {}
    id = item["@id"]
    for (k, v) in item.items():
        prop_id = props.get_prop_id(k)
        if not isinstance(v, list):
            vals = [v]
        else:
            vals = v
        if prop_id:
            item_set_to_upload[k] = []
            for val in vals:
                item_set_to_upload[k].append({
                    "type": "literal",
                    "property_id": prop_id,
                    "@value": val
                    })
    if item_set_to_upload:
        if id in shelf:
            print("Redoing old set", id)
            prev_id = shelf[id]["o:id"]
            r = requests.put("%sitem_sets/%s?%s" % (host_url, prev_id, auth),
                                            data=json.dumps(item_set_to_upload), headers=json_header)
            #print(r.content)

        else:
            print("Uploading new set", id)
            r  = requests.post("%sitem_sets?%s" % (host_url, auth),
                                            data=json.dumps(item_set_to_upload), headers=json_header)

        shelf[id] = r.json()
        # Remember which items are part of this collection / item_set
        for part in []: #item["hasMember"]:
            if part["@id"] not in lookup_collection:
                lookup_collection[part["@id"]] = []
            lookup_collection[part["@id"]].append(shelf[id]["o:id"])



for item in [col for col in dc["@graph"] if "Collection" not in col["@type"]]:
    item_to_upload = {"o:item_set": []}
    id = item["@id"]

    if "@type" in item:
        types = item["@type"]
        if not isinstance(types, list):
            types = [types]
        if not("File" in types):
            item_to_upload["o:resource_class"] = {
                "o:id": classes.get_class_id(types[-1])
                }

            for (k, v) in item.items():
                prop_id = props.get_prop_id(k)
                if not isinstance(v, list):
                    vals = [v]
                else:
                    vals = v

                if prop_id:
                    item_to_upload[k] = []
                    for val in vals:

                        if "@id" in val and val["@id"] in shelf:
                            if "o:id" in shelf[val["@id"]]:
                                item_to_upload[k].append({
                                    "type": "resource",
                                    "property_id": prop_id,
                                    "value_resource_id": shelf[val["@id"]]["o:id"]
                                    })
                            else:
                                print("Can't upload item", shelf[val["@id"]])

                        else:
                            m = re.match("(.*)<a\s+href *= *(?P<quote>['\"])(.*?)(?P=quote).*>(.*)</a>$", str(val))
                            if m: #value is a URI
                                #{"type":"uri","property_id":4,"property_label":"Description","@id":"http:\/\/ptsefton.com","o:label":"This!"
                                item_to_upload[k].append({
                                    "type": "uri",
                                    "property_id": prop_id,
                                    "o:label": m.group(4),
                                    "@id": m.group(1) + " " + m.group(3)
                                    })
                                #print(item_to_upload[k])
                            else:
                                item_to_upload[k].append({
                                    "type": "literal",
                                    "property_id": prop_id,
                                    "@value": val
                                    })

            if item_to_upload:
                if "dcterms:title" not in item_to_upload and "path" in item:
                    item_to_upload["dcterms:title"] = [{
                        "type": "literal",
                        "property_id": props.get_prop_id("name"),
                        "@value": item["path"]
                        }]

                if id in lookup_collection:
                    for coll_id in lookup_collection[id]:
                        item_to_upload["o:item_set"].append({"o:id": coll_id})
                        #print("Adding to set", item_to_upload)


                if id in shelf:
                    #print("ID FROM SHELF", id, shelf[id])
                    prev_id = shelf[id]["o:id"]
                    r = requests.put("%sitems/%s?%s" % (host_url,prev_id, auth),
                                                    data=json.dumps(item_to_upload), headers=json_header)
                    #print("Uploaded", item_to_upload)

                else:
                    r = requests.post("%sitems?%s" % (host_url, auth),
                                                    data=json.dumps(item_to_upload), headers=json_header)
                    #print("Uploaded", item_to_upload)
                shelf[id] = r.json()
                print(r.json())
                print("Stored", id)


                if "hasFile" in item and upload_files:
                    #print("Uploading files", item['hasFile'])
                    index = 0
                    if not(isinstance(item['hasFile'], list)):
                        item['hasFile'] = [item['hasFile']]
                    for f in item['hasFile']:
                        #Hack - move this somewhere nicer
                        if True or "original_" in  f["@id"]:
                            upload_this_file = True
                            # if f["@id"] in shelf and "o:sha256" in shelf[f["@id"]]:
                            #     print("Been here before")
                            #     original_sha = shelf[f["@id"]]["o:sha256"]
                            #     with open(f["@id"], 'rb') as hash_this:
                            #         this_sha = hashlib.sha256(hash_this.read()).hexdigest()
                            #     if original_sha == this_sha:
                            #         upload_this_file = False
                            #         print("NOT UPLOADING")
                            #     print("KEYS", original_sha, this_sha)
                            if upload_this_file and "o:id" in shelf[id]:
                                data= {
                                    "o:ingester": "upload",
                                    "file_index":  str(index),
                                    "o:item": { "o:id": shelf[id]["o:id"]}
                                    }
                                filename = json_index.item_by_id[f["@id"]]["path"]
                                if isinstance(filename, list):
                                    filename = filename[0]
                                print(filename)
                                path = os.path.join(root_dir, filename)
                                print(path)
                                if os.path.exists(path):
                                    files = [("file[%s]" % str(index), open(path,'rb').read())]
                                    #s = requests.Session()
                                    #s.config = {'verbose': sys.stderr}

                                    #r = s.post(host_url + "media?%s" % (auth), files=files, data=data)
                                    # HORRIBLE HACK TODO: fix this but requests was not working for me
                                    curl_command = ["curl", "-F", "'file[%s]=@%s'" % (index, path), "-F", "data='%s'" % json.dumps(data), "'%smedia?%s'" % (host_url, auth), "2> ", "/dev/null"]
                                else:
                                    print("File not found", path)
                                
                                #subprocess.run(curl_command)
                                res = os.popen(" ".join(curl_command)).read()
                                try:
                                    print("Uploading: ", path)
                                    result = json.loads(res)
                                    #print("RESULT!", json.dumps(result, indent=2))
                                    #shelf[f["@id"]] = result
                                except:
                                    print("Failed uploading: ", path)
                                    pass

                            index += 1
                #config = {'verbose': sys.stderr}
#curl -F 'file[0]=@./content/373/fullsize_9bb3f1085681806200a85f898ce570b6.jpg' -F 'data={"o:ingester": "upload", "file_index": "0", "o:item": {"o:id": "657"}}' 'http://localhost/api/media?key_identity=GMauLUNqOe8ifubbeapIwPDV9k7uRfo5&key_credential=ReRyOeh5HcvLXy6UjPfZziHBI9tFmSM3'
                #print (r, r.json(), json.dumps(data))