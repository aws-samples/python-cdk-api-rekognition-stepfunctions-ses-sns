import simplejson as json
import boto3
import os
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):

	logger.info(event)

	labels_body = {}
	has_image = ""
	try:
	  labels_body = event['RekognitionResult']['Payload']['body']
	  has_image = labels_body['rekognition_success']
	except:
	  logger.info('No rekognition submission')

	#default return object
	data = {
		'size':'unknown',
		'notification_team':'default',
		'rekognition_label':'none',
		'total_mass':'0',
		'total_volume':'0',
		'total_density':'0'
	}
	
	#only try to load the size if we've successfully completed rekognition
	if(has_image == 'true'):
		#we have a successful rekognition result
		#load search term from FIRST label (most rekognised item)
		search_term = labels_body['Labels'][0]['Name']

		#load dynamodb resource
		dynamodb = boto3.resource('dynamodb')

		#try dynamodb execution
		try:
		  #load dynamodb table
		  table = dynamodb.Table(os.environ.get('CZ_SIZE_TABLE_NAME'))
		  search_result = table.get_item(
		  	Key={
		  	    'item_label': search_term
		  	}
		  )
		  
		  data['rekognition_label'] = search_term

		  try:
		    if(len(search_result['Item']) > 0):
		      #calculate the mass/volume
		      #load number of items from form
		      num_items = float(event['main_form']['item_count'])

		      #only return the single item result
		      data['Item'] = search_result['Item']

		      #calculate size of objects
		      data['size'] = 'calculated'
		      data['notification_team'] = search_result['Item']['default_team']
		      data['total_mass'] = num_items*float(search_result['Item']['mass'])
		      data['total_volume'] = num_items*float(search_result['Item']['volume'])
		      data['total_density'] = num_items*float(search_result['Item']['density'])
		  except:
		    logger.info('No result found')

		except ClientError as e:
		    return_message = e.response['Error']['Message']
		    return_status=500
		else:
		    return_message = data
		    return_status=200
	else:
		return_message = data
		return_status=200

	#return to front end service
	return {
	    'statusCode': return_status,
	    'body': return_message,
	    'headers': {
	      'Content-Type': 'application/json',
	      'Access-Control-Allow-Origin': '*'
	    },
	}
	

