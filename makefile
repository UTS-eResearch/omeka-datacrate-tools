dharmae: get-dharmae calcyfy-dharmae

calcyfy-dharmae:
	calcyfy ~/working/dharmae/dharmae/ro-crate-metadata.json -c https://data.research.uts.edu.au/examples/ro-crate/0.2

get-dharmae:
	python omeka_classic_to_datacrate.py -d ~/working/dharmae/dharmae/  -u https://dharmae.research.uts.edu.au/api   -m ./examples/dharmae/dharmae-ro-crate-metadata-template.json   ~/working/dharmae/temp/ro-crate-metadata_raw.json
	python doctor_datacrate.py -m examples/dharmae/dharmae_mapping.json  ~/working/dharmae/temp/ro-crate-metadata_raw.json  ~/working/dharmae/dharmae/ro-crate-metadata.json
	
get-f2f: 
	python omeka_classic_to_datacrate.py          -d ~/working/f2f/farms_to_freeways/files           -u  http://omeka.uws.edu.au/farmstofreeways/api          -m ./examples/f2f/F2F-metadata-template.json          ~/working/f2f/data_migration/ro-crate-metadata-raw.json
	fix-f2f

fix-f2f:
	  python doctor_datacrate.py \
           -m examples/f2f/farms_to_freeways_mapping.json\
           ~/working/f2f/data_migration/ro-crate-metadata-raw.json\
           ~/working/f2f/data_migration/ro-crate-metadata.json
	  maketml ~/working/f2f/data_migration/ro-crate-metadata.json

