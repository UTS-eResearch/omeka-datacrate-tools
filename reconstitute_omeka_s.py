"""
Quick and dirty script to push Datacrate to Omeka
"""

import json
import shelve
import requests
import sys
import logging
import os
import hashlib
import re
import argparse
import time
import subprocess


class Properties():
    def __init__(self):
        self.prop_ids = {}
    def get_prop_id(self, nom):
        
        if nom in self.prop_ids:
            return self.prop_ids[nom]
        else:
            name = nom
            # Filthy hack but datacrate only supports direct mapping from Key to ID
            
            url = "%sproperties?%s&per_page=1&term=%s" % (host_url, auth, name)
            print(url)
            res = requests.get(url)
            prop_data = res.json()

            if prop_data and "o:id" in prop_data[0]:
                self.prop_ids[nom] = prop_data[0]["o:id"]
                print("Getting prop.", nom, self.prop_ids[nom])
                return self.prop_ids[nom]


class JSON_Index():
    def __init__(self, json_ld):
        self.json_ld = json_ld
        self.item_by_id = {}
        for item in json_ld["@graph"]:
            self.item_by_id[item["o:id"]] = item

class Resource_classes():
      def __init__(self):
          self.prop_ids = {}
      def get_class_id(self,names):
          if not isinstance(names, list):
             names = [names]

          for nom in names:
              if nom in self.prop_ids:
                  return self.prop_ids[nom]
              elif nom in context:
                  name = context[nom]
                  if "o:id" in name:
                      name = name["o:id"]
                  url = "%sresource_classes?%s&per_page=100000&term=%s" % (host_url, auth, name)
                  r = requests.get(url)
                  #print(r.content)
                  prop_data = r.json()

                  if prop_data and "o:id" in prop_data[0]:
                      self.prop_ids[nom] = prop_data[0]["o:id"]
                      return self.prop_ids[nom]

                  else:
                       #print("Can't find this class", name )
                       return None


props = Properties()
classes = Resource_classes()

# TODO - turn these into parameters


#key_identity: K9sFGVEAEexubJFvIG0zbzHthLPnDcgD
#key_credential: n7kC4VN0pGAtcpQbRuGNEwBYxPcBxUtx

parser = argparse.ArgumentParser()
parser.add_argument('-c', '--credential', default=None, help='Omeka API Key')
parser.add_argument('-i', '--identity', default=None, help='Omeka API identify')
parser.add_argument('-u', '--api-url',default=None, help='Omeka API Endpoint URL (hint, ends in /api/)')
parser.add_argument('-s', '--shelf', default="saved_data", help='Where to stash intermediate results')
parser.add_argument('infile', help='Catalog file to load')



args = vars(parser.parse_args())

root_dir, _ = os.path.split(args['infile'])

with open(args["infile"], 'r') as cat:
    dc = json.load(cat)



key_identity = args["identity"] 
key_credential = args["credential"] 

host_url = args["api_url"]

if not host_url.endswith("/"):
    host_url += "/"# "http://localhost/api/"

# Don't treat files as primary objects only upload to parent item with hasFile

shelf = shelve.open(args["shelf"]) # Remember what's been uploaded before keyed by datacrate ID
lookup_collection = {} # Keyed by datacrate id, lists omeka IDs for collections

auth = "key_identity=%s&key_credential=%s" % (key_identity, key_credential)
json_header =  {'Content-Type': 'application/json'};


media_index = {}
for media_item in dc["media"]:
    media_index[media_item["@id"]] = media_item

def global_id(type, id):
    return type + str(id)



def upload_media_item(item, parent_item_id):
    #path = "makefile" # hee!
    if  global_id("media", item["@id"]) in shelf:
        item["o:id"] = shelf[global_id("media",item["@id"])]["o:id"]
    
    data = {
    "o:ingester": "upload", 
    "file_index": "0", 
    "o:item": {"o:id": str(parent_item_id)}
    }
   
    params = {
     'key_identity': args["identity"],
     'key_credential': args["credential"]
    }
    files = [
         ('data', (None, json.dumps(data), 'application/json')),
         ('file[0]', ('test.jpg', open('test.jpg', 'rb'), 'image/jpg'))
        ]
    
    url = "%smedia" % (host_url)
    r = requests.post(url,  files=files, params=params)
    if "errors" in r.json():
            print("errors", r.json())
    else:
        shelf[global_id("media", item["@id"])] = r.json()

    return item["@id"]

# Item sets (collections)

def get_id_from_thing(thing):
    if "@id" in thing:
        return thing["@id"]
    else:
            return None


def get_simple_id_from_thing(thing):
    if "o:id" in thing:
        return thing["o:id"]
    else:
        return None

def check(value, key, to_remove):
        update_thing_ids(value) 
        id = get_id_from_thing(value)
        #print("ID", id)
        if id:
            glob_id = get_id_from_thing(value)
            #print(glob_id)
            if glob_id and glob_id in shelf:
                #print("Found an id", id, "for key", key)
                simple_id = get_simple_id_from_thing(shelf[glob_id])
                if simple_id:
                    value["o:id"] = simple_id
                else:
                    #print("Can't find a simple ID for ", id)
                    to_remove.add(key)
            else:
                to_remove.add(key)
         #else "id" in value:
         #   to_remove.add(key) # Get rid of this at least for now TODO: Check

        

def update_thing_ids(thing):
    to_remove = set()
    for key, value in thing.items():
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    check(item, key, to_remove)
        elif isinstance(value, dict):
            check(value, key, to_remove)

    for remove in to_remove:
        #print("Removing", remove)
        thing.pop(remove)

 
def upload_anything(type, first_pass=True):
    
    for item_to_upload  in dc[type]:
        media_to_upload = []
        
        id = get_id_from_thing(item_to_upload)
        if id:
            keys_to_lose = set()
            update_thing_ids(item_to_upload)     
            #if "o:slug" in item_to_upload:
            #   item_to_upload.pop("o:slug")

            if  id in shelf and "o:id" in shelf[id]:
                if first_pass:
                    break # this thing is already uploaded 
                prev_id = shelf[id]["o:id"]
                item_to_upload["o:id"] = prev_id
                print("Redoing old one: ", id, "to id", prev_id)
                url = "%s%s/%s?%s" % (host_url, type, prev_id, auth)
                print(url)

                r = requests.put(url, data=json.dumps(item_to_upload), headers=json_header)    

            else:
                print("Making new: ", id)
                url = "%s%s?%s" % (host_url, type, auth)
                if "o:id" in item_to_upload:
                    item_to_upload.pop("o:id")
                #print(item_to_upload)  
                r  = requests.post(url, data=json.dumps(item_to_upload), headers=json_header)
            
            item_id = None # TODO actually set this :)

            new_item = None
            try:
                new_item = r.json()
                shelf[id] = new_item
                if "errors" in new_item:
                    print("errors", r.json())
                    print(json.dumps(item_to_upload, indent=3))
                    die
            except:
                print("we didn't manage to upload that")
                

                
            if item_id:
                for media in media_to_upload:
                    print("Media upload for", item_id)
                    upload_media_item(media_index[media_item["o:id"]], item_id)
            else:
                pass
                #print("Cant't find an id", new_item)
   
#TODO VOCABS - need to load the whole thing...


for first_pass in [True, False]:
    for type in ["sites", "site_pages"]:  # "resource_templates", "item_sets", "items",   #"resource_templates", "media" "items"
        upload_anything(type, first_pass)
