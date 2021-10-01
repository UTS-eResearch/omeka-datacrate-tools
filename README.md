# omeka-datacrate-tools

Quick and dirty (so far) python3 scripts to push  DataCrates/RO-Crates in and out of Omeka S and to move data out of Omeka Classic. As time permits we're updating these scripts to follow the [RO-Crate specification](https://researchobject.github.io/ro-crate/).

These are not packaged or installable yet.

## The scripts

There are two script for extracting data from Omeka repositories:

-  [`omeka_classic_to_datacrate.py`](./omeka_classic_to_datacrate.py) exports
   from Omeka Classic repositories into DataCrate format.

-  [`omeka_s_to_ro-crate.py`](./omeka_s_to_ro-crate.py) exports from Omeka S
   to DataCrate format, it puts metadata into both CATALOG.json and into a file
   containing raw Omeka S API data: API.json.

There are two ways to import DataCrate metadata into Omeka S.

-   [`datacrate_to_omeka_s.py`](./datacrate_to_omeka_s.py) will work with ANY
    DataCrate data, and uses the CATALOG.json file for metadata. To run this the target repository must have the schema.org vocabulary installed.
-   [`reconstitute_omeka_s.py`](./reconstitute_omeka_s.py) uses the API dump from an omeka site.



# Audience and platform

This is for experience Python developers

# An example

This is a worked example of how to export data from an Omeka Classic repostiory to a DataCrate, and optionally to re-upload it.

The example repository "Farms to Freeways" is here:
<http://omeka.scem.ws/farmstofreeways/exhibits/show/viewall>.

## Get this code and set up a virtual environment

-  Get the code:
    ```
    git clone https://github.com/UTS-eResearch/omeka-datacrate-tools.git
    cd omeka-datacrate-tools
    ```

-  Make a virtual environment and activate it:

   ```
   mkdir ~/venvs
   python3 -m venv ~/venvs/omeka-datacrate-tools
   source ~/venvs/omeka-datacrate-tools/bin/activate
   ```

-  Install packages into the activated virtual environment (this is not packaged yet - help wanted!)

   ```
   pip install requests
   ```

## Install Calcyte.js for generating the HTML page for datacrate and bagging it

Install Calycte.js, which is a node.js project. You will use Calcyte to generate
and HTML index page drom the CATALOG.json file created by
```omeka_classic_to_datacrate.py```, and to bag the files using the Bagit standard.


# Create working area

- Create a place to put the downloaded Farms to Freeways dataset

    ```
    mkdir ~/working/f2f                   # Doesn't have to be ~/working of course
    mkdir ~/working/f2f/data_migration    # Intermediate files, multistep process
    mkdir ~/working/f2f/farms_to_freeways # This is the actual data package
    mkdir ~/working/f2f/farms_to_freeways/files  # For downloaded files
    ```


# Download data from Omeka Classic

-  To see what the ```omeka_classic_to_datacrate.py``` script takes as arguments type:

```
    python omeka_classic_to_datacrate.py --help



    usage: omeka_classic_to_datacrate.py [-h] [-k KEY] [-u API_URL]
                                     [-d DOWNLOAD_CACHE] [-m METADATA]
                                     [outfile]

    positional arguments:
       outfile

    optional arguments:
      -h, --help            show this help message and exit
      -k KEY, --key KEY     Omeka API Key
      -u API_URL, --api_url API_URL
                        Omeka API Endpoint URL (hint, ends in /api)
      -d DOWNLOAD_CACHE, --download_cache DOWNLOAD_CACHE
                        Path to a directory in which to cache dowloads
                        (defaults to ./data)
      -m METADATA, --metadata METADATA
                        Datacrate Metadata file (CATALOG.json) to use as a
                        base.

```

-  For this example use this command:

    ```
     python omeka_classic_to_datacrate.py \
      -d ~/working/f2f/farms_to_freeways/files\
      -u  http://omeka.uws.edu.au/farmstofreeways/api\
      -m ./examples/f2f/F2F-metadata-template.json\
         ~/working/f2f/data_migration/ro-crate-metadata-raw.json
    ```



   -  -u is An API_URL that points to the API of the Omeka Repository

   -  -d is a directory into which to write the files (you created it above)

   -  -m is a CATALOG.json file which describes the whole dataset; there is a
      sample one in this repository in the examples directory

   -  The final argument is the (temporary) output file in the data_migration
      directory


Once you have run ```omeka_classic_to_datacrate.py``` there should be
DataCrate-type "ro-crate-metadata-raw.json" file in migration-data. This file will not be ready to
use, as the properties and types used in it don't match the RO-Crate context
(which is based on schema.org). For example, the "title" item needs to be
changed to name. This example ships with a file that does the mapping: ```examples/f2f/farms_to_freeways_mapping.json```.

-  Fix the CONTEXT file so it is datacrate_ready using the file supplied to map keys in the JSON-LD created above to DataCrate-friendly keys:

    ```
    python doctor_datacrate.py \
           -m examples/f2f/farms_to_freeways_mapping.json\
           ~/working/f2f/data_migration/ro-crate-metadata-raw.json\
          ~/working/f2f/farms_to_freeways/ro-crate-metadata.json
     ```

# Download data from Omeka S

Use the script `omeka_s_to_ro-crate.py`.

Usage:
```
> python omeka_s_to_ro-crate.py -h
usage: omeka_s_to_ro-crate.py [-h] [-k KEY_IDENTITY] [-c KEY_CREDENTIAL]
                              [-u API_URL] [-d DOWNLOAD_CACHE] [-m METADATA]
                              [outfile]

positional arguments:
  outfile

optional arguments:
  -h, --help            show this help message and exit
  -k KEY_IDENTITY, --key-identity KEY_IDENTITY
                        Omeka S Key indetity
  -c KEY_CREDENTIAL, --key-credential KEY_CREDENTIAL
                        Omeka S Key credential
  -u API_URL, --api_url API_URL
                        Omeka API Endpoint URL (hint, ends in /api)
  -d DOWNLOAD_CACHE, --download_cache DOWNLOAD_CACHE
                        Path to a directory in which to cache dowloads
                        (defaults to ./data)
  -m METADATA, --metadata METADATA
                        Datacrate Metadata file (CATALOG.json) to use as a
                        base.
```

See the above section on downloading from Omeka Classic for how to fix the resulting file using `doctor_datacrate.py`


# Use Calcyte.js to bag the content and create a index.html

To generate HTML (-g), bag (-b) and zip (-z) ```~/working/f2f/farms_to_freeways/```:

-  use this command:

    ```
    calcyfy -z  -g  -b ~/working/f2f/bags/ ~/working/f2f/farms_to_freeways/
    ```



# Upload RO-Crate data into Omeka S



-  Install Omeka S - eg from here: https://git.research.uts.edu.au/eresearch/infra-aws-omeka-s/-/tree/master/docker

-  Load the Schema.org vocab into Omeka S
   - Go to https://schema.org/docs/developers.html
   -  Download the Vocabulary definition file for schema in Format: Triples
      <https://schema.org/version/latest/schemaorg-current-http.ttl>
   -  In Omeka S:
      -  click on Vocabularies and add Sechma.org using the file you downloaded above schemaorg-current-http.ttl
      -  Get an API key identity and crednetial (under Users)


-  Define environment variables like:
   ```
   export OMEKA_KEY_IDENTITY=bJCEy...j
   export OMEKA_KEY_CREDENTIAL=9Fzvqy...O

   ```


-  Run this:
    ```
    python datacrate_to_omeka_s.py   -u http://localhost/api/ -s ~/working/f2f/data_migration/saved_ids  ~/working/f2f/farms_to_freeways/CATALOG.json -f
    ```


TIPS / troubleshooting:

-  Files failing to upload? YOu need to set the upload limit in PHP (TODO: how???)

-  If you have errors then the local cache of IDs might get corrupted, delele it:
  ```
  rm ~/working/f2f/data_migration/saved_ids
  ```

-  To turn off file uploads remove the -f option - this will speed things up considerably for testing.

