import simplejson as json
import boto3
import os
import uuid
import time
import logging
from botocore.exceptions import ClientError
from decimal import Decimal

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):

	#defaults for dynamodb insert
	insert_uuid = str(uuid.uuid4())
	created_date = str(time.time())
	
	#logging uuid
	logger.info('uuid: '+insert_uuid)

	#get state machine variables for submission
	body = event['main_form']
	size_result_body = event['InitResult'][0]['SizeFunctionResult']['Payload']['body']
	exif_result_body = event['InitResult'][1]['EXIFFunctionResult']['Payload']['body']

	#input for dynamodb
	item_details = {
	    'uuid': insert_uuid,
	    'location': {
	      'latitude': body['latitude'],
	      'longitude': body['longitude']
	    },
	    'image_reference_s3': body['image_reference_s3'],
	    'contact_details': {
	      'forename': body['forename'],
	      'contact_tel': body['contact_tel'],
	      'can_contact': bool(body['can_contact']),
	      'surname': body['surname'],
	      'contact_email': body['contact_email']
	    },
	    'other_information': body['other_information'],
	    'public_land': body['public_land'],
	    'what_flytipped': {
	      'item_count': body['item_count'],
	      'describe_type': body['describe_type'],
	      'item_type': body['item_type'],
	      'item_subtype': body['item_subtype']
	    },
	    'date_creation': created_date,
	    'date_last_updated':'0',
	    'status': 'new',
	    'exif': {
	    	'lat' : Decimal(str(exif_result_body['lat'])),
	    	'lon' : Decimal(str(exif_result_body['lon'])),
	    	'exif_datetime' : exif_result_body['img_datetime']
	    }
	}

	item_details['size'] = 'unknown'
	item_details['total_mass'] = Decimal("0")
	item_details['total_volume'] = Decimal("0")
	item_details['total_density'] = Decimal("0")
	item_details['rekognition_label'] = size_result_body['rekognition_label']
	item_details['notification_team'] = size_result_body['notification_team']

	if(size_result_body['size'] == 'calculated'):
		#we have a calculated size of the items - add this to dynamodb
		item_details['size'] = 'calculated'
		item_details['total_mass'] = Decimal(str(size_result_body['total_mass']))
		item_details['total_volume'] = Decimal(str(size_result_body['total_volume']))
		item_details['total_density'] = Decimal(str(size_result_body['total_density']))

	#load dynamodb client
	dynamodb = boto3.resource('dynamodb')
	table = dynamodb.Table(os.environ.get('CZ_SUBMISSION_TABLE_NAME'))

	#Start insert
	try:
		data_insert = table.put_item(
		  Item=item_details
		)
		data = {'uuid':insert_uuid}
		
	except ClientError as e:
	    return_message = e.response['Error']['Message']
	    return_status=500
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
