"""

Quick and dirty script to create a DataCrate from an Omeka Classic repository.

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
                    {"@type": "File", "path": file_rel_path, "@id": file_rel_path}
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
            item["@type"].append("RepositoryCollection")
            members.append({"@id": item["@id"]})
            catalog["@graph"].append(item)


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
                {"@id": ":_Anonymous_datacrate", "path": "./", "@type": ["Dataset"]}
            ]
        }
    graph = catalog["@graph"]
    graph[0]["hasPart"] = [] # Schema.org
    graph[0]["hasMember"] = [] # PCDM


    # By convention... this is bad...
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
            item["hasFile"] = []

            if "o:item_set" in item:
                item["memberOf"] = item["o:item_set"]
                item.pop("o:item_set")

            for media_item in item["o:media"]:
                r = requests.get(media_item["@id"])
                contents =  r.content.decode()
                contents = fix_keys(contents)
                file_metadata = json.loads(contents) 
                file_url = file_metadata["o:original_url"]
                file_metadata["@id"] = file_metadata["o:filename"]
   
                item["hasFile"].append({"@id": file_metadata["@id"]})
              

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
                file_metadata["path"] = os.path.relpath(file_path, start=data_dir)
                graph.append(file_metadata)
                
            graph.append(item)
    

    catalog = load_collections(endpoint, api_key, catalog, members)
    with args["outfile"] as j:
        j.write(json.dumps(catalog, indent=3))


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
        get_all_nodes_of_type(endpoint, auth, data_dir, type, api_graph)

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
