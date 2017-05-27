import csv
from bs4 import BeautifulSoup
from pymongo import MongoClient
import xml.etree.cElementTree as ET
import re
import pprint
#Get stats on exec time
import time

start_time = time.time()


#Setup global vars for local db
DBNAME ='test'
client = MongoClient('127.0.0.1', 27017)
db = client.dwp3
cur = db[DBNAME]


#Setup variables for file processing and various audit parking constructs
OSMFILE = 'orlando_florida.osm'
ERRLOG = 'error_'+OSMFILE
expected_way_endings = ['Street', 'Avenue', 'Boulevard', 'Drive', 'Court',\
						'Play', 'Way', 'Pike', 'Parkway','Road', 'Trail', \
						'Turnpike', 'Loop', 'Circle', 'Lane']
unexpected_way_endings = set()
split_endings_re = re.compile(r'\b\S+\.?$')


street_mappings = {'St': 'Street',
		            'St.': 'Street',
		            'Ave':'Avenue',
		            'Rd.': 'Road',
		            'Blvd': 'Boulevard',
		            'Ct':' Court'}


name_fixes = {  'H.S.': 'High School',
                'HS': 'High School'}
records_with_errors = set()

def check_street_endings():
	'''
	This is an audit method to check for odd street name endings
	If a strange ending and  is already mapps it replaces the value
	If it can't be mapped the record is added to an error dict 
	'''

	for record in  cur.find({'addr': {'$exists': True }}):
		split_endings_re_search = split_endings_re.search(record['addr'])
		if split_endings_re_search:
			street_type = split_endings_re_search.group()
			if street_type not in expected_way_endings:
				unexpected_way_endings.add(street_type)
				fix_street_name(record)
	   		else:
	   			records_with_errors.add(record['_id'])
	pprint.pprint( unexpected_way_endings)


def fix_street_name(node):
	'''
		This menthod fixes the street endings that aren't expected and replaces them
		with the dict values contained in street_mappings
		Future dev: abstract this to a generic update fuction. Let it handle all updates to map values and dicsts
		Use a set w/ the object id's to track itesms with issues
	'''
	split_endings_re_search = split_endings_re.search(node['addr']).group()
	if split_endings_re_search in street_mappings:
		#replace the incorrect entry identifyed with the dict mapping
		corrrected_addr = re.sub(split_endings_re, street_mappings[split_endings_re_search], node['addr']) 
		#update db with the corrected value
		cur.update( {'_id':node['_id']}, \
						{'$set': {'addr':corrrected_addr, 'corrected':True }}, \
						upsert=False)

		

def is_highway(node):
	#deprecated/unused
	re.compile(r'')

def print_tag(tag):
	for attrib in tag.iter('attrib'):
		print attrib
		print "sub"


def fix_postal_code(filename):
	
	with open(filename, 'r') as osmfile:
		#Parse through the file interatively
		#Debug option, limit processing
		i=0
		for event, elem in ET.iterparse(filename, events=('start',)):
				#Filter tags for only node or ways tha will have tag elements
				if elem.tag =='node' or elem.tag =='way':
					for tag in elem.iter('tag'):
						if tag.attrib['k'] == 'addr:postcode':
							zip = str(tag.attrib['v'])
							
							if (len(zip) != 5) and (len(zip) !=10):
								print 'zip error to fix: '+ zip
								print len(zip)
								print_tag(tag)
		
								#pprint.pprint(elem)
								if zip.find(' ') > 0:
									print zip.find(' ')
									print split_endings_re.search(zip).group()
							
							#Check if zip code isn't in FL by checking digiti
							elif int(zip[0]) != 3:
								print 'Error: Zip not in FL: '+ zip
								print split_endings_research(zip)


def find_addresses(filename):
	
	with open(filename, 'r') as osmfile:
		#Parse through the file interatively
		#Debug option, limit processing
		i=0
		for event, elem in ET.iterparse(filename, events=('start',)):
				#Filter tags for only node or ways tha will have tag elements
				if elem.tag =='node' or elem.tag =='way':
					for tag in elem.iter('tag'):
						if tag.attrib['k'].find('addr'):
							print "found address portion"
							print tag.attrib['k']
							print tag.attrib['v']
							


def xml_to_json(filename):

	with open(filename, 'r') as osmfile:
		#Parse through the file interatively
		#Debug option, limit processing
		element= { 'type': None,
					'child':{ 
							'type' : None,
							'tags': [] }
					}
		i=0
		for event, elem in ET.iterparse(filename, events=('start',)):
			element['type'] = elem.tag
			for child in elem.iter():
				element['child']['type'] =  child.tag

				#print  child.tag
				
				for tag in child.iter():
					element['child']['tags']+=[{tag.tag: tag.attrib}]
					#element[]['tags'] = tag.attrib
					#print tag.attrib
					#print type(tag.attrib)
					
					if tag.get('addr:postcode') != None:
						print "found add"
					
			
			#pprint.pprint(element)
			pprint.pprint(element)
			db['test2'].insert(element)
			element.clear()
			i+=1
			if i == 1000:
				break


def extract_and_write_nodes_to_db(filename):
	err_street_endings = dict()
	street = {}
	''' Document Structure
			'name': Name of element,
			'long': Longitude
			'lat" : lattitude'
			'addr': Address of Node if applicable,
			'type': type of tag way|node},
			'username':  Name of user who edited element
			'user id':  Id of user who edited element
			'loc_class':  Additional location information support furthuer cleaning
	'''

	with open(filename, 'r') as osmfile:
		#Parse through the file interatively
		#Debug option, limit processing
		i=0
		for event, elem in ET.iterparse(filename, events=('start',)):
				#Filter tags for only node or ways tha will have tag elements
				if elem.tag =='node' or elem.tag =='way':
					#Add type to dict to write to db
					street['type'] = elem.tag
					#Add locs to dict to write to db
					if elem.tag =='node':
						street['lat'] = get_attribute( elem, 'lat', ERRLOG)
						street['long'] = get_attribute( elem, 'lon', ERRLOG)
					for tag in elem.iter('tag'):
						#Get name of the element
						if tag.attrib['k'] == 'name':
							street['name'] = tag.attrib['v']
						#Get street names for each tag
						if tag.attrib['k']  =="addr:street":
							street['addr'] = tag.attrib['v']
						if tag.attrib['k'] == 'amenity':
							street['loc_class'] = tag.attrib['v']
					street['userid'] =get_attribute( elem, 'uid', ERRLOG)
					street['username'] = get_attribute( elem, 'user', ERRLOG)
				
				if bool(street):
					cur.insert(street)

				street.clear()
				
				
				'''
				#Debug option, limit processing while chaning documen structure
				i+=1
				if i == 1000:
					break
				

				'''



'''Added this bit since some nodes threw errors when looking for expected 
attributes we're going to get an error log that we can refernce'''
def get_attribute(tag, keyname, errlog):
	# DEBUG - Refactor this wih getattr
	with open(errlog, 'w') as fp:
		errout = csv.writer(fp)
	try:
		return tag.attrib[keyname]
	
	except:
		print tag.attrib
		errout.writerow(tag.attrib)
		return None


def find_strange_ways(filename):
	#deprecated/unused
	for event, elem in ET.iterparse(filename, events=('start',)):
		way_tags = {}
		if elem.tag == 'way':
			for tag in elem.iter('tag'):
				if  tag.attrib['k'] == 'addr:street':
					build_street_types(way_endings, tag.attrib['v'])

			
	
def dbStats():
	'''
	This section fulfils the requiremetns for Overview of the data in the grading rubric

	'''
	stats = {
				'total_db_size': db.command('collStats', DBNAME)['storageSize'],
				'unique_users' : len(cur.distinct('userid')),
				'unique_nodes' : cur.count( {'type':'node'} ),
				'unique_ways' : cur.count( {'type':'way'} ),
				'num_publix' : cur.count({'name':re.compile('.*ublix.*')}),
				'num_high_school' : cur.count({'name': re.compile('.*High School.*')}),
				'num_elem_school' : cur.count({'name': re.compile('.*Elementary School.*')}),
				#To do, give top 10 contributors


	}
	
	pprint.pprint( stats)


	
def topContributors():
	pipeline = [{'$group': {'_id':'$username', 'count': {'$sum':1}}}, \
				{'$sort': {'count':-1}}, \
				{'$project':{ 'userid': 1, 'username':1, 'count':1}}, \
				{'$limit': 10} ]

	print 'Top Contributors to Map:'					
	for i, user in enumerate(cur.aggregate(pipeline), start=1):
		print str(i)+'. '+user['_id']+' made '+str(user['count'])+' contributions'

	

def profileData(filename):
	'''
		This will spit out some information about the data we're preocessing
		we have the specs but I'd like to see how many of each tag we're 
		dealing with
	'''
	profile_file_name = 'profile_'+ filename
	with open(profile_file_name, 'w') as fp:
		tags = {}
		way_tags = {}
		tag_types={}

		csv_writer = csv.writer(fp)

		for event, elem in ET.iterparse(filename,  events=('start',)):
			try:
				tags[elem.tag] += 1
			except:
				tags[elem.tag] = 1
			for tag in elem.iter('tag'):
				try:
					way_tags[tag.attrib['k']] += 1
				except:
					way_tags[tag.attrib['k']] = 1
			elem.clear()
			break

		#Write header for tag dump section
		fp.write(str(len(tags))+" diff tags in document:")
		#write out all of the tags we've collected along with their counts
		for k, v in tags.items():
			csv_writer.writerow([k,v])

		#Write out all of the differnt type of tags
		fp.write('\nNumber of tags:\n')
		fp.write(str(len(tags)))
		fp.write('\n')
		fp.write('\nWay tag subtypes\n')
		for k, v in way_tags.items():
			csv_writer.writerow([k,v])

		

	

def audit_data():
	'''
	Checking for missing va
	lues gives us a check on multile levesl for the audit
	'''
	query_missing_gps =  {'$or' :[{'long' :{'$exists': False}}, \
							{'lat':{'$exists': False}} ] }
	query_missing_name = {'name' : {'$exists': False}}
	query_missing_username =  {'username' : {'$exists': False}}
	query_missing_userid =  { 'userid' : {'$exists': False}}
	

	query_builder = {'type': 'node'}
	query_builder.update( query_missing_username)
	query_builder.update( query_missing_userid)
		
	for record in cur.find(query_builder):
		pprint.pprint( record)



def main():

	#Inital parsing for adding new feilds to DB
	#extract_and_write_nodes_to_db(OSMFILE)
	


	#test consistency by finding mismatched long lat pairs
	#audit_data()

	#cleaning task to check streetnames
	#check_street_endings()

	#Cealning Postal codes
	#fix_postal_code(OSMFILE)
	
	xml_to_json(OSMFILE)
	#Dump stats for db per specs
	#dbStats()

	#find_addresses(OSMFILE)
	#Dump top contributors
	#topContributors()
	
	#Write out tag stats
	profileData(OSMFILE)

	print("--- %s seconds ---" % (time.time() - start_time))

if __name__ == '__main__': main()