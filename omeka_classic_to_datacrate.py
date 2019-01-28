"""

Quick and dirty script to create a DataCrate from an Omeka Classic repository

At this stage it just handles working datacrates, not bagged data crates

TODO:
 - Create the index.html file
 - Handle bagging

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
                    print("HEADERS", r.headers)
                    if "content-length" in r.headers:
                        download_size = r.headers[ "content-length"]  
                    else:
                        download_size =  -1

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


class Elements:
    def __init__(self):
        self.element_names = {}

    def get_element_name(self, id):
        if id not in self.element_names:

            r = requests.get(endpoint + "/elements/" + str(id))
            element = json.loads(r.content)
            self.element_names[id] = element["name"]
        return self.element_names[id]


class Relations:

    def __init__(self):
        self.relation_names = {}

    def get_relation_name(self, id):
        if id not in self.relation_names:
            r = requests.get(
                endpoint + "/item_relations_properties/" + str(id)
            )
            print(endpoint + "/item_relations_properties/" + str(id))
            element = json.loads(r.content)
            print(element)
            self.relation_names[id] = element["local_part"]
        return self.relation_names[id]


class ItemTypes:

    def __init__(self):
        self.item_types = {}

    def get_item_type_name(self, item_json, id):
        if id not in self.item_types:
            r = requests.get(endpoint + "/item_types/" + str(id))
            element = json.loads(r.content)
            print("EL", element)
            self.item_types[id] = element["name"]
        item_json["@type"].append(self.item_types[id])


relation_stash = Relations()
item_type_stash = ItemTypes()


def get_relations(item_json, id):
    """ Find all inter-related items. Note that this will fail for more than 50 relations"""
    
    r = requests.get(endpoint + "/item_relations?subject_item_id=%s" % (str(id)) )
    relations = json.loads(r.content)
    print(endpoint + "/item_relations?subject_item_id=%s"  % (str(id)))
    for rel in relations:
        #relation_name = relation_stash.get_relation_name(rel["property_id"])
        #print(rel)
        relation_name = rel["property_local_part"]
        item_json[relation_name] = {"@id": str(rel["object_item_id"])}
        print("RELATION", {"@id": str(rel["object_item_id"])})

    # {'id': 165, 'subject_item_id': 149,
    # 'property_id': 39, 'object_item_id': 167, 'property_vocabulary_id': 1, 'pro


def get_collection_members(id, item_json):
    page = 1
    item_json["hasMember"] = []

    while True:
        collection_url = endpoint + "/items?collection=%s&page=%s" % (
            str(id), str(page)
        )
        print(collection_url)
        r = requests.get(collection_url)
        page += 1
        items = json.loads(r.content)
        if items == []:
            break
        for item in items:
            print("Member", item["url"])
            item_json["hasMember"].append({"@id": str(item["id"])})
        return (item_json)


def load_collections(endpoint, api_key, data_dir, catalog, parts):
    page = 1
    while True:
        r = requests.get(endpoint + "/collections?page=" + str(page))
        page += 1
        items = json.loads(r.content)
        if items == []:
            break

        print("Got a set of %s collections" % len(items))
        for item in items:
            id = str(item["url"])
            item_json = {"@id": str(id), "@type": ["RepositoryCollection"]}

            for val in item["element_texts"]:
                text = val["text"]
                # uri = val["uri"]
                el_id = val["element"]["id"]
                el_name = els.get_element_name(el_id)
                el_name = el_name.replace(" ", "")
                el_name = el_name[0].lower() + el_name[1:]
                if not el_name in item_json:
                    item_json[el_name] = []
                item_json[el_name].append(text)

            item_json = get_collection_members(item["id"], item_json)
            parts.append({"@id": str(id)})
            catalog["@graph"].append(item_json)
    return (catalog)


def load_items(endpoint, api_key, data_dir, metadata_file):
    if metadata_file:
        catalog = json.loads(open(metadata_file, "r").read())

    else:
        catalog = {
            "@graph": [
                {"@id": "Anonymous_datacrate", "path": "./", "@type": ["Dataset"]}
            ]
        }

    graph = catalog["@graph"]
    graph[0]["hasPart"] = []

    # By convention... this is bad...
    parts = graph[0]["hasPart"]
    page = 1

    while True:
        r = requests.get(endpoint + "/items?page=" + str(page))
        page += 1
        items = json.loads(r.content)
        if items == []:
            break

        print("Got a set of %s items" % len(items))
        for item in items:
            id = item["id"]
            item_json = {"@id": str(id), "@type": ["RepositoryObject"]}
            if "item_type" in item and item["item_type"] and "id" in item["item_type"]:
                item_type = item["item_type"]["id"]
                item_type_stash.get_item_type_name(item_json, item_type)

            for val in item["element_texts"]:
                text = val["text"]
                # uri = val["uri"]
                el_id = val["element"]["id"]
                el_name = els.get_element_name(el_id)
                el_name = el_name.replace(" ", "")
                el_name = el_name[0].lower() + el_name[1:]
                if not el_name in item_json:
                    item_json[el_name] = []
                item_json[el_name].append(text)

            # Geolocations
            if "geolocations" in item["extended_resources"]:
                place_url = item["extended_resources"]["geolocations"]["url"]
                # TODO - Up to 50...
                r = requests.get(place_url)
                place = r.json()
                place_json = {"@id": place_url, "@type": "Place"}
                if "address" in place:
                    place_json["address"] = place["address"]
                    place_json["@label"] = place["address"]
                if "latitude" in place and "longitude" in place:
                    geo_json = {
                        "@id": place_url + "#GEO",
                        "latitude": str(place["latitude"]),
                        "longitude": str(place["longitude"]),
                        "@type": "GeoCoordinates",
                        "@label": "Lat: %s Long: %s "
                        % (str(place["latitude"]), str(place["longitude"])),
                    }
                    place_json["geo"] = {"@id": place_url + "#GEO"}
                    graph.append(geo_json)
                graph.append(place_json)
                item_json["contentLocation"] = {"@id": place_url}

            deal_with_files(graph, item_json, item, data_dir)
            if not args["no_relations"]:
                get_relations(item_json, id)
            # print(json.dumps(item_json, indent=4))
            graph.append(item_json)
    catalog = load_collections(endpoint, api_key, data_dir, catalog, parts)
    with args["outfile"] as j:
        j.write(json.dumps(catalog, indent=3))


# Define and parse command-line arguments


if __name__ == "__main__":
    els = Elements()
    parser = argparse.ArgumentParser()
    parser.add_argument("-k", "--key", default=None, help="Omeka API Key")
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
        "-n",
        "--no_relations",
        action='store_true',
      
        help="Don't try to fetch item relations",
    )
    parser.add_argument(
        "outfile", nargs="?", type=argparse.FileType("w"), default=sys.stdout
    )

    args = vars(parser.parse_args())

    endpoint = args["api_url"]
    api_key = args["key"]
    data_dir = args["download_cache"]
    metadata_file = args["metadata"]
    if api_key:
        auth = {"key": api_key}
    else:
        auth = {}

    load_items(endpoint, api_key, data_dir, metadata_file)
