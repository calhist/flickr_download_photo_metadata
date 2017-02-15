#############DESCRIPTION##############
##This script uses the Flickr API to catalog descriptions, tags and other information about photos stored on Flickr.com into a local database.


#############NOTES####################
##This script was written for Python 2.6 using the Flickr API for Python v1.2(http://stuvel.eu/projects/flickrapi) on Windows Vista, but it should work on nearly any OS.
##Requires you to get a Flickr API from http://www.flickr.com/services/api/
##Current version of csv module (as of 20090726) does not support Unicode (which is how SQL stores things and how some of the characters are stored in Flickr DB as well.  So we need to convert them to UTF-8 for export which may cause some odd characters in the export file.  See http://docs.python.org/library/csv.html


#############HISTORY##################
##2009-06-08 - Joshua Hunter - Initial script.
##2009-06-25 - JH - Decided to use sqlite3 for storage and then allow export to other formats, opens up lots of options for data manipulation, queries, etc. See http://sqlite.org
##2009-07-28 - JH - First version released into the wild.

##############TODO/Wishlist####################
##20090701 - done - validate dates
##20090715 - done - write database cleanup module (remove duplicates)
##20090725 - done - write database dump to csv or similar
##catch errors, exit more gracefully
####Get it to restart download after error a given number of times (count errors until max reached defined by user variable)
##retrieve comments
##download security settings, exif data
##move user configurable variables to .ini file using ConfigParser module
####once the .ini is done it might be possible to create this as .exe
##use indexes in the db to speed up some of the query and export processes
##function (with command line option) for statistics (# of photos, unique tags, etc)
##check to see if there is a better way to do the export database queries (in one sql query).  Maybe with a UNION?
##add function to allow remove of data about a single photo id (remove photo, tags, etc)
##Try converting the unicode to Ascii rather than UTF8 so & becomes & not scrambled.  See http://www.peterbe.com/plog/unicode-to-ascii


##################################################################
####################### BEGIN DEFINING VARIABLES ########################
##################################################################

#flickr info, you can get a key from http://flickr.com/services/api
api_key = 'API_KEY'
api_secret = 'API_SECRET'
userid = 'USERID'

#Date ranges of photos to gather information about.  Dates are UPLOAD dates, not photo taken dates (since not all photos will have taken dates that are accurate because missing exif taken date gets set to upload date anyway).  If both dates are set to "0" then all photos will be processed
#Begin date photos taken on and after this date. Format: yyyy-mm-dd, eg 2001-01-15(set to 0 to get photos back to your first upload)
begin_date = "0"
#end date: photos taken on and before this date. Format: yyyy-mm-dd, eg 2001-01-15(set to 0 to get photos up to your most recent upload)
end_date = "0"

#Number of results to return per page, the specific value doesn't matter that much and 100 is a good setting
perpage = '100'

#Name of the database file to output, in same directory as this script
db_file = "flickr_metadata.db"

#Name of the export file (not the database) that will be created
export_file = "flickr_metadata.csv"

#set the export file delimiter, "," is default
export_file_delim = ","
#set the export file quote character, '"' is default
export_file_quote = '"'

#How should any previous database file be treated?  Overwritten? Appended to?
#0 = append to current database, 2 = overwrite/replace current database
replaceappend = 0

##################################################################
############### NOTHING BELOW THIS LINE SHOULD NEED EDITING #################
##################################################################

#information about most of these modules can be found at http://docs.python.org/modindex.html

#
#
##### Import Modules ######
#
#

#To ignore the md5 module deprecation warnings. Comment out to see them again
import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
#import the FlickrAPI python module.  This needs to be downloaded and installed prior, http://stuvel.eu/projects/flickrapi
import flickrapi
#imports the time module which we'll use to calculate dates and change date formats
import time
#import the os.path module to do a lookup to see if a file exists
import os.path
#import the sqlite3 module for data storage/manipulation
import sqlite3
#import this module to handle user command line options
from optparse import OptionParser


#
#
##### Work with command line options #####
#options are parsed at the end once the functions have already been defined.
#

#define command line options
parser = OptionParser()
parser.add_option("--dedup",action="store_true", help="Removes duplicates from database.", dest="dedup")
parser.add_option("--export", action="store_true", help="Export to CSV file.", dest="export")
parser.add_option("--compactdb", action="store_true", help="Compacts the database.",dest="compactdb")
(options,args) = parser.parse_args()


#
#
##### Define functions #####
#
#

#Function that compacts the database
def compactdb(dbname):
	try:
		import sqlite3
	except:
		pass
	origsize = os.path.getsize(db_file)
	print "Connecting to database: %s" % dbname
	print "Original size in bytes: %s" % origsize
	db = sqlite3.connect(dbname)
	print "Beginning to shrink database"
	db.execute("VACUUM")
	db.close()
	newsize = os.path.getsize(db_file)
	print "New size in bytes: %s" %newsize
	print "Exiting..."

#function that removes duplicates from the photos table
def dedup_photos(dbname, tablename):
	import sqlite3
	print "Removing duplicates from the %s table" % tablename
	print "Connecting to database: %s" % dbname
	db = sqlite3.connect(dbname)
	print "Preparing temporary table(s)..."
	db.execute("DROP TABLE IF EXISTS temptable")
	db.execute("CREATE TABLE temptable (id int,photo_title text,photo_origformat text,photo_media text,photo_description text,photo_date_posted text,photo_date_taken text,photo_url text)")
	db.execute("INSERT INTO temptable SELECT DISTINCT * FROM %s" % tablename)
	db.execute("DROP TABLE IF EXISTS %s" % tablename)
	db.execute("ALTER TABLE temptable RENAME TO %s" % tablename)
	#db.execute("DROP TABLE IF EXISTS temptable")
	print "Duplicates removed."
	db.close()

#function that removes duplicates from the tags table	
def dedup_tags(dbname, tablename):
	import sqlite3
	print "Removing duplicates from the %s table" % tablename
	print "Connecting to database: %s" % dbname
	db = sqlite3.connect(dbname)
	print "Preparing temporary table(s)..."
	db.execute("DROP TABLE IF EXISTS temptable")
	db.execute("CREATE TABLE temptable (id int,tag text)")
	db.execute("INSERT INTO temptable SELECT DISTINCT * FROM %s" % tablename)
	db.execute("DROP TABLE IF EXISTS %s" % tablename)
	db.execute("ALTER TABLE temptable RENAME TO %s" % tablename)
	#db.execute("DROP TABLE IF EXISTS temptable")
	print "Duplicates removed."
	db.close()

#function that calls the de-duplication functions above
def dedup():
	dedup_photos(db_file,"photos")
	dedup_tags(db_file,"tags")

#function that exports the resuts from the db
def export(dbname, exportfile):
	import sqlite3, unicodedata
	print "Connecting to database: %s" % dbname
	db = sqlite3.connect(dbname)
	print "Querying database..."
	photo_id_result = db.execute("SELECT * FROM photos")
	photos_list = photo_id_result.fetchall()
	output_list=[] #create the list that will contain all the data about each photo for export
	for photo in photos_list: #work through the list of photo information one at a time
		photoid = photo[0]
		# print "photoid: ", photoid
		tag_result = db.execute("SELECT tag FROM tags WHERE id = '%s'" % photoid) #search for the current photos photoid in the tags list, return results if it has a tag
		tag_result_list = tag_result.fetchall()
		tags_nonunicode = []
		for tag in tag_result_list: #for each tag in the list of results add it to the photo information
			tag = tag[0]
			tag = tag.encode("utf-8") #convert to utf-8 from unicode
			#print "tag: " , tag
			tags_nonunicode.append(tag) #create a non-unicode list of tags
		#print tags_nonunicode
		photo_nonunicode = []
		for item in photo:
			try: #integers(photo ids) fail if you try to convert to utf-8, so we'll skip any errors.
				#item = unicodedata.normalize('NFKD', item).encode('ascii','ignore')

				item = item.encode("utf-8")
			except:
				pass
			photo_nonunicode.append(item) #create a non-unicode list of photo info
		photo_nonunicode.extend(tags_nonunicode) #merge the photo info list with the tags list
		output_list.append(photo_nonunicode) #add the merged list to the master output list which we'll iterate over later with the csv module
	#print output_list
			
	import csv #used to write export file
	csv.register_dialect('primary', delimiter=export_file_delim, quoting=csv.QUOTE_ALL, quotechar=export_file_quote) #builds a set or rules, a dialect, that we can apply to read or write the output file
	print "Writing output file: %s" % export_file
	outputwriter = csv.writer(open(export_file, 'wb'),'primary')
	outputwriter.writerow(['PhotoID','FileName','FileFormat','MediaType','Description','UploadDateTime','CreatedDateTime','URL','Tags'])
	for row in output_list:
		outputwriter.writerow(row)
	print "Finished.  Exiting..."
	
	
	
	
#
#
##### Parse command line arguments.  Run various functions based on option selected #####
#
#

#--dedup
#remove the duplicates from database
if options.dedup:
	dedup()
	exit()

#--export
#export the data to a flat file
if options.export:
	export(db_file,export_file)
	exit()

#--compactdb
#shrink the size of the database (by removing uneeded space)
if options.compactdb:
	compactdb(db_file)
	exit()
	
#
#
##### Work with output file #####
#
#
print "Looking for previous output file..."

if replaceappend == 0: #keeping old data
	if os.path.isfile(db_file): #checking for old database
		print "Previous SQLite database found"
	else:
		print "The previous SQLite database was not found. A new database will be created later in the process."
if replaceappend == 2: #discard old data, if present
	if os.path.isfile(db_file):
		print "Previous SQLite database found, removing old data..."
		db = sqlite3.connect(db_file, isolation_level=None)
		db.execute("DROP TABLE IF EXISTS photos")
		db.execute("DROP TABLE IF EXISTS tags")
		db.close()
	else:
		print "The previous SQLite database was not found. A new database will be created later in the process."
		
#
#
##### Convert user entered dates #####
#
#

#convert start and end dates to epoch time required by flickr api
#http://www.goldb.org/goldblog/2007/03/22/PythonConvertDateTimeToEpoch.aspx
if begin_date == "0":
	begindateepoch = 0
	printdatebegin = "forever ago"
else:
	format = '%Y-%m-%d %H:%M:%S'
	begin_date = begin_date + " 00:00:00"
	begindateepoch = int(time.mktime(time.strptime(begin_date, format)))
	printdatebegin = begin_date
if end_date == "0":
	enddateepoch = time.time()
	printdateend = "now"
else:
	format = '%Y-%m-%d %H:%M:%S'
	end_date = end_date + " 23:59:59"
	enddateepoch = int(time.mktime(time.strptime(end_date, format)))
	printdateend = end_date
#
#
##### Query Flickr for Photo IDs Matching Criteria ######
#
#

print "Connecting to Flickr.  You may be asked to authenticate."
#Authenticate script with Flickr account to read non-public photo info
flickr = flickrapi.FlickrAPI(api_key, api_secret)
#check to see if the program has already been given access to the flickr acount
(token, frob) = flickr.get_token_part_one(perms='read') #readonly access
#a web browser will open to flickr asking the user to authorize the access
if not token: raw_input("Press ENTER after you authorized this program")
flickr.get_token_part_two((token, frob))

print "Querying for photos between and including %s to %s" % (printdatebegin, printdateend)
#content_type='1' returns only the photos
photos = flickr.photos_search(user_id=userid, per_page=perpage, min_upload_date=begindateepoch, max_upload_date=enddateepoch, content_type='1')

#Find the number of pages of photos
pages = photos.find('photos').attrib['pages']
print "Number of pages of photos (at %s per page): " % (perpage) + pages

#create an empty list we will append photo id to
photoids = []

pages = int(pages)
pagecount = 1
print "Retrieving all the photo ids..."
while pagecount <= pages:
	#print "Pages: ", pages, ", " , "Pagecount: " , pagecount , ", " "length: ", len(photoids)
	#get a list of photos on a specific page of results
	photopage = flickr.photos_search(user_id=userid,page=pagecount,per_page=perpage,min_upload_date=begindateepoch, max_upload_date=enddateepoch, content_type='1')
	#make a list of all the photo info for a given page
	photoinfo_perpage = photopage.find('photos').findall('photo')
	for photo in photoinfo_perpage:
		photoids.append(photo.attrib['id'])
	pagecount += 1

print "Number of photos on Flickr in this range: ", len(photoids)

#
#
##### Connect to the database (output file) ######
#
#

#connect to the database, create the needed tables if they don't already exists
print "Connecting to SQLite database to enter results as data is received..."
db = sqlite3.connect(db_file, isolation_level=None) #connect to the database file
db.execute("CREATE TABLE IF NOT EXISTS photos(id int,photo_title text,photo_origformat text,photo_media text,photo_description text,photo_date_posted text,photo_date_taken text,photo_url text)")
db.execute("CREATE TABLE IF NOT EXISTS tags(id int,tag text)")	
		
#
#
##### Process each photo id, insert metadata into database ######
#
#
	
if replaceappend == 0: #in this case we want only the ids of photos we don't have in our DB
	print "Querying local database for photoids already retrieved..."
	result = db.execute("SELECT id FROM photos")
	reslist = result.fetchall()
	idlist = []
	subphotolist = []
	for id in reslist:
		idlist.append(int(id[0]))
	for photo in photoids:
		if int(photo) not in idlist:
			subphotolist.append(photo)
	photoids = subphotolist #sets photoids equal to our new smaller list of ids before we search for that entire list on flickr
print "Photoids not found in database: ", len(photoids)

#
#
##### Query Flickr for Photo Metadata ######
#
#
if len(photoids) == 0:
	print "Exiting...bye"
	exit()
	
print "Gathering all the meta data for each photo..."
#The list, photoids, now contains the id of every photo in the account for the given range.
#get the info for each photo by using its photo_id to query flickr
	
idprocessed = 0 #used as counter
for id in photoids:
	idprocessed += 1
	if idprocessed % 250 == 0: #print a process dialog every so often
		print "Processing: ", idprocessed
	photoinfo = flickr.photos_getinfo(photo_id=id) #gets the info about the individual photo
	photo_title = photoinfo.find('photo').find('title').text #gets the photos title/name
	photo_origformat = photoinfo.find('photo').attrib['originalformat'] #gets the original uploaded photo's format eg, jpg, gif
	photo_media = photoinfo.find('photo').attrib['media'] #gets the original uploaded photo's media type, eg, video, photo
	photo_description = photoinfo.find('photo').find('description').text #gets the description of the photo
	#We have to convert the descriptions to utf-8
	photo_date_posted = photoinfo.find('photo').find('dates').attrib['posted'] #date photo was posted, in seconds since epoch (jan 1 1970)
	photo_date_posted = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(photo_date_posted)))
	photo_date_taken = photoinfo.find('photo').find('dates').attrib['taken'] #date photo was taken (or uploaded if date taken info not avail), in yyyy-mm-dd HH:mm:ss
	photo_tags_list = photoinfo.find('photo').find('tags').findall('tag') #gets the tags for the photo
	photo_tags = [] #create a blank list to put the tags into
	for tag in photo_tags_list: #search through the tags xml list
		tag_tuple = (id,tag.text)
		db.execute("INSERT INTO tags VALUES(?,?)",tag_tuple)
	photo_url = photoinfo.find('photo').find('urls').find('url').text #get URL of photo page
	photo_all_info = (id,photo_title,photo_origformat,photo_media,photo_description,photo_date_posted,photo_date_taken,photo_url) #create a tuple of all the info we gathered for this one photo
	db.execute("INSERT INTO photos values (?,?,?,?,?,?,?,?)",photo_all_info) #insert all non-tag info
	
print "Closing database connection..."	
db.close()	
print "Exiting...bye."