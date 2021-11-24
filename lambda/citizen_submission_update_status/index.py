import simplejson as json
import boto3
import os
import time
import logging
from botocore.exceptions import ClientError
from decimal import Decimal

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):

	#defaults for dynamodb update
	updated_date = str(time.time())

	#get variables for submission
	has_uuid = ''
	try:
	  has_uuid = event['queryStringParameters']['uuid']
	except:
	  logger.info('No uuid present')

	has_status = ''
	try:
	  has_statusx = event['queryStringParameters']['status']
	  if(has_statusx == "inprog"):
	  	has_status = 'In Progress'
	  elif(has_statusx == 'comp'):
	  	has_status = 'Complete'
	except:
	  logger.info('No status present')
	
	#must have uuid and status to update the database
	if(has_uuid != '' and has_status != ''):
		#load dynamodb client
		dynamodb = boto3.resource('dynamodb')
		table = dynamodb.Table(os.environ.get('CZ_SUBMISSION_TABLE_NAME'))

		#Start insert
		try:
			#update status, ignore update if already updated
			response = table.update_item(
			    Key={
			        'uuid': event['queryStringParameters']['uuid']
			    },
			    UpdateExpression='set #st = :status_val, date_last_updated = :date_updated',
			    ExpressionAttributeValues={
			        ':status_val': has_status,
			        ':date_updated': updated_date
			    },
			    ExpressionAttributeNames={
			        '#st': 'status'
			    },
			    ConditionExpression='#st <> :status_val',
			    ReturnValues='ALL_NEW'
			)	
		except ClientError as e:
			if e.response['Error']['Code'] != 'ConditionalCheckFailedException':
			    return_message = e.response['Error']['Message']
			    return_status=500
			else:
				return_status=200
				return_message = {'message':'no item updated, already in this state'}
		else:
			#successful - trigger email lambda to citizen
			lambda_email_payload = {
				'main_form' : {
					'can_contact' : str(response['Attributes']['contact_details']['can_contact']),
					'contact_email' : response['Attributes']['contact_details']['contact_email'],
					'forename' : response['Attributes']['contact_details']['forename'],
				},
				'DBFunctionResult' : {
					'Payload' : {
						'body' : {
							'uuid' : response['Attributes']['uuid']
						}
					}
				},
				'template' : '_STATUS_UPDATE'
			}
			#email lambda execution (async)
			lambda_client = boto3.client('lambda')
			lambda_email = lambda_client.invoke(
				FunctionName=os.environ.get('CZ_EMAIL_LAMBDA'),
				InvocationType='Event',
				Payload=json.dumps(lambda_email_payload)
			)
			#return to front end successful update
			return_message = {'message':'success - item updated'}
			return_status=200
	else:
		return_message = {'message':'no item found'}
		return_status=200
	
	#return to front end service
	return {
	    'statusCode': return_status,
	    'body': json.dumps(return_message),
	    'headers': {
	      'Content-Type': 'application/json',
	      'Access-Control-Allow-Origin': '*'
	    },
	}
