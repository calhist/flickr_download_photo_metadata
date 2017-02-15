# Get Flickr Photo Metadata as a CSV

Python script to grab Flickr photo metadata.

From Joshua Hunter: http://huntertrek.com/wp/2009/07/27/flickr-metadata-downloader-in-python/

See also: http://drewtarvin.com/business/export-flickr-metadata-csv-file/

We used this to grab all photo metadata from our Flickr Commons albums: https://www.flickr.com/photos/chs_commons/albums

### Steps to run: 

* For simplicity's sake, make sure Python script is in same folder as where you want the resulting database and CSV to be.
* In Windows command line, navigate to that folder
* Type: 

```$ python.exe flickr_download_photo_metadata.py```
* Script will run, creating a DB file in the folder
* Once that's complete, run the script again, but append the export flag:

```$ python.exe flickr_download_photo_metadata.py --export```
* This creates a CSV file

### Now let's parse the CSV:

 * Open CSV in OpenRefine, creating a new project
 * Transform Description column by replacing all line breaks with semi-colons (or any character not used in the data itself -- pipes, etc.) using GREL script:

```value.replace("\n", ";")```
 * Parse Description column by choosing Add column based on this column...
 * Use Jython match function with regex to parse out all descriptive metadata , e.g.
```python
import re
m = re.match(r".*publisher:(.*?);", value, re.I)
return m.group(1)
```
 * Repeat this step for all of the metadata fields:
  * Repository
  * Collection
  * Date
  * Call Number
  * Digital Object ID
  * Preferred Citation
  * Photographer
  * Publisher
  * Format
  * Online Finding Aid
