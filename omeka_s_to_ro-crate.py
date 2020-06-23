"""

Quick and dirty script to create a DataCrate from an Omeka-S repository.

"""

from sys import stdout, stdin
import argparse
import json
import urllib.parse
import os
import json
import csv
import shelve
import copy
import requests
import pickle
import sys
import re
crosswalk = {
    "dcterms:title": "name",
    "dcterms:description": "description",
    "dcterms:contributor": "contributor"
}

def deal_with_files(graph, item_json, item, data_dir):
    """Handle any dowloads, cache as files locally, then upload all files"""
    print("Dealing with files")
    download_this = True
    url = item["files"]["url"]
    print("Files url", url)
    r = requests.get(url)
    # print("JSON", r.json())
    if len(r.json()) > 0:
        for file_type, file_url in r.json()[0]["file_urls"].items():
            print("file_url", file_url)
            if file_url:
                filename = file_type + "_" + urllib.parse.urlsplit(file_url).path.split(
                    "/"
                )[
                    -1
                ]
                new_path = os.path.join(data_dir, str(item["id"]))
                if not os.path.exists(new_path):
                    os.makedirs(new_path)
                file_path = os.path.join(new_path, filename)
                print("Local filename: %s", file_path)

                # Check if we have one the same size already
                if os.path.exists(file_path):
                    r = requests.head(file_url)
                    download_size = r.headers[
                        "content-length"
                    ] if "content-length" in r.headers else -1
                    file_size = os.path.getsize(file_path)
                    print("Download size", download_size, "Local file size", file_size)
                    if download_size == str(file_size):
                        print(
                            "Already have a download of the same size: %s" % file_size
                        )
                        download_this = False

                if download_this:
                    # try:
                    print("Downloading")
                    r = requests.get(file_url)
                    open(file_path, "wb").write(r.content)

                    # except:
                    # print ("Some kind of download error happened fetching %s - pressing on" % file_url)
                file_rel_path = os.path.join(
                    os.path.basename(data_dir), os.path.relpath(file_path, data_dir)
                )
                

                graph.append(
                    {"@type": "File", "@id": file_rel_path, "dc_title": file_rel_path}
                )
                if file_type == "thumbnail":
                    print("Thumb!", file_rel_path)
                    item_json["thumbnail"] = {"@id": file_rel_path}

                if "hasFile" not in item_json:
                    item_json["hasFile"] = []
                item_json["hasFile"].append({"@id": file_rel_path})




def fix_keys(contents):
    return contents.replace('"o:type"', '"@type').replace('"o:label"', '"@label"')

def load_collections(endpoint, api_key, catalog, members):
    page = 1
    while True:
        r = requests.get(endpoint + "/item_sets?page=" + str(page))
        contents = fix_keys(r.content.decode())
        page += 1
        items = json.loads(contents)
        if items == []:
            break

        print("Got a set of %s collections" % len(items))
        for item in items:
            if not isinstance(item["@type"], list):
                item["@type"] = [item["@type"]]
            item.pop("@context")
            item["@type"].append("RepositoryCollection")
            new_item = {}
            fixProps(item, new_item, catalog["@graph"])
            members.append({"@id": new_item["@id"]})
            # TODO - handle this data structure better
            catalog["@graph"].append(new_item)


    return (catalog)

def get_all_nodes_of_type(endpoint, auth, data_dir, type, graph):
    page = 1
    graph[type] = []
    while True:
        r = requests.get(f"{endpoint}/{type}?page={page}{auth}")
        page += 1
        contents = r.content.decode()
        items = json.loads(contents) 
        if items == []:
            break
        print(f"Got a set of {len(items)} of type {type}")
        for item in items:
            graph[type].append(item)



    
def load_items(endpoint, api_key, data_dir, metadata_file):
    if metadata_file:
        catalog = json.loads(open(metadata_file, "r").read())

    else:
        catalog = {
            "@graph": [
                {"@id": "./", "@type": ["Dataset"]},
                {
                    "@type": "CreativeWork",
                    "@id": "ro-crate-metadata.jsonld",
                    "conformsTo": {"@id": "https://w3id.org/ro/crate/1.0"},
                    "about": {"@id": "./"}
                 }
            ]
        }
    if not "@context" in catalog:
        catalog["@context"] = {}
    graph = catalog["@graph"]
    graph[0]["hasPart"] = [] # Schema.org
    graph[0]["hasMember"] = [] # PCDM
    
    default_context = json.loads(open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "context.json"), "r").read())

  
    

    # Getting root dataset by convention... this is bad...
    parts = graph[0]["hasPart"]
    members = graph[0]["hasMember"]

    page = 1

    while True:
        r = requests.get(endpoint + "/items?page=" + str(page))
        page += 1  
        contents =  r.content.decode()
        contents = fix_keys(contents)
        items = json.loads(contents) 
        if items == []:
            break
        print("Got a set of %s items" % len(items))
        for item in items:
            #print(json.dumps(item, indent=2))
            parts.append({"@id": item["@id"]})
            new_item = {}
            new_item["hasFile"] = []
            new_item["@id"] = str(item["@id"])
            item.pop("@id")
            item.pop("@context")

            if "o:item_set" in item:
                new_item["memberOf"] = item["o:item_set"]
                item.pop("o:item_set")

            
            if "o:media" in item:
                for media_item in item["o:media"]:
                    r = requests.get(media_item["@id"])
                    contents =  r.content.decode()
                    contents = fix_keys(contents)
                    file_metadata = json.loads(contents) 
                    file_metadata.pop("@context")
                    file_url = file_metadata["o:original_url"]
                    file_metadata["@id"] = file_metadata["o:filename"]
    
                

                    new_path = os.path.join(data_dir, str(file_metadata["o:id"]))
                    if not os.path.exists(new_path):
                        os.makedirs(new_path)
                    file_path = os.path.join(new_path, file_metadata["@id"])
                    print("Local filename: %s", file_path)
                    download_this = True
                    # Check if we have one the same size already
                    if os.path.exists(file_path):
                        r = requests.head(file_url)
                        download_size = r.headers[
                            "content-length"
                        ] if "content-length" in r.headers else -1
                        file_size = os.path.getsize(file_path)
                        print("Download size", download_size, "Local file size", file_size)
                        if download_size == str(file_size):
                            print(
                                "Already have a download of the same size: %s" % file_size
                            )
                            download_this = False

                    if download_this:
                        # try:
                        print("Downloading")
                        r = requests.get(file_url)
                        open(file_path, "wb").write(r.content)
                    new_file = {}

                    file_metadata["@id"] = os.path.relpath(file_path, start=data_dir)
                    new_item["hasFile"].append({"@id": file_metadata["@id"]})

                    fixProps(file_metadata, new_file, graph)
                    
                   
                    if "dcterms:title" not in new_file:
                        new_file["dcterms:title"] = new_file["@id"]
                    graph.append(new_file)
            
                item.pop("o:media")
         
            
            fixProps(item, new_item, graph)            
                    
            new_item["@type"].append("RepositoryObject")
            graph.append(new_item)
    

    catalog = load_collections(endpoint, api_key, catalog, members)
    with args["outfile"] as j:
        #print(catalog)
        j.write(json.dumps(catalog, indent=3))

def fixProps(item, new_item, graph):
    for prop, values in item.items():
        
        prop = re.sub("^schema:","", prop)

        if values and isinstance(values, list):
            if prop not in new_item:
                new_item[prop] = []
            for value in values:
                new_item[prop].append(fixValue(value, graph))
        else:
            new_item[prop] = str(values)

def fixValue(value, graph):
    if isinstance(value, dict) and "@id" in value:
        if value["type"] == "uri":
            urlItem = {
                "@id": value["@id"],
                "@type": "URL",
                "name": value["@id"]
                }
            if "@label" in value:
                urlItem["name"] =  value["@label"]
            graph.append(urlItem)
        
        return {"@id": value["@id"]}
    elif  isinstance(value, dict) and "@value" in value:
        return value["@value"]
    else:
        return str(value)
                

# Define and parse command-line arguments


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-k", "--key-identity", default=None, help="Omeka S Key indetity")
    parser.add_argument("-c", "--key-credential", default=None, help="Omeka S Key credential")
    parser.add_argument(
        "-u",
        "--api_url",
        default=None,
        help="Omeka API Endpoint URL (hint, ends in /api)",
    )
    parser.add_argument(
        "-d",
        "--download_cache",
        default="./content",
        help="Path to a directory in which to cache dowloads (defaults to ./data)",
    )
    parser.add_argument(
        "-m",
        "--metadata",
        default=None,
        help="Datacrate Metadata file (CATALOG.json) to use as a base.",
    )
    parser.add_argument(
        "outfile", nargs="?", type=argparse.FileType("w"), default=sys.stdout
    )

    args = vars(parser.parse_args())

    endpoint = args["api_url"]
    key_identity = args["key_identity"]
    key_credential = args["key_credential"]
    data_dir = args["download_cache"]
    os.makedirs(data_dir, exist_ok=True)
    metadata_file = args["metadata"]
    if key_identity  and key_credential:
        #todo
        auth = "&key_identity=%s&key_credential=%s" % (key_identity, key_credential)

    else:
        auth = {}

    api_graph = {}
    for type in ["vocabularies", "properties", "resource_classes", "resource_templates", "items", "item_sets", "media", "sites", "site_pages" ]:
        #get_all_nodes_of_type(endpoint, auth, data_dir, type, api_graph)
        pass

    """
    items	Yes
    item_sets	Yes
    media	Yes
    resources	Yes
    properties	Yes
    vocabularies	Yes
    resource_classes	Yes
    resource_templates	Yes
    sites	Yes
    site_pages	Yes
    assets	Yes
    jobs	No
    modules	No
    users
    """

    api_filename = os.path.join(data_dir, "API.json")


    with open(api_filename, "w") as api:
        api.write(json.dumps(api_graph, indent=3))
  
    load_items(endpoint,auth, data_dir, metadata_file)
