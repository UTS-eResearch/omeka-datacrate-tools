# omeka-datacrate-tools
Quick and dirty (so far) python3 scripts to push  DataCrates into Omeka S and to move data out of Omeka Classic

These are not packaged or installable yet.

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


# Download data

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

     python omeka_classic_to_datacrate.py \
         -d ~/working/f2f/farms_to_freeways/files  \
         -u  http://omeka.uws.edu.au/farmstofreeways/api \
         -m ./examples/f2f/F2F-CATALOG-template.json \
         ~/working/f2f/data_migration/CATALOG_raw.json



   -  -u is An API_URL that points to the API of the Omeka Repository

   -  -d is a directory into which to write the files (you created it above)

   -  -m is a CATALOG.json file which describes the whole dataset; there is a
      sample one in this repository in the examples directory

   -  The final argument is the (temporary) output file in the data_migration
      directory


Once you have run ```omeka_classic_to_datacrate.py``` there should be
DataCrate-type CATALOG file in migration-data. This file will not be ready to
use, as the properties and types used in it don't match the DataCrate context
(which is based on schema.org). For example, the "title" item needs to be
changed to name. This example ships with a file that does the mapping: ex

-  Fix the CONTEXT file so it is datacrate_ready using the file supplied to map keys in the JSON-LD created above to DataCrate-friendly keys:

    python doctor_datacrate.py \
           -m examples/f2f/farms_to_freeways_mapping.json\
           ~/working/f2f/data_migration/CATALOG_raw.json\
          ~/working/f2f/farms_to_freeways/CATALOG.json

# Use Calcyte.js to bag the content and create a index.html

To generate HTML (-g), bag (-b) and zip (-z) ```~/working/f2f/farms_to_freeways/```:

-  use this command:

   calcyfy -z  -g  -b ~/working/f2f/bags/ ~/working/f2f/farms_to_freeways/



# TODO: More! Upload the data into Omeka S

Full instructions coming at some point, but:

-  Install Omeka S

-  Load the Schema.org vocab into Omeka S

-  Run this:

    python datacrate_to_omeka_s.py   -i ofiCqzOrQyOEAvRlt09Ii26ywxK7674u -c iq0AcRgHSQBs5MqTqwwrRNXxGGVo2uHV     -u http://localhost/api/ -s ~/working/f2f/data_migration/saved_ids  ~/working/f2f/farms_to_freeways/CATALOG.json
