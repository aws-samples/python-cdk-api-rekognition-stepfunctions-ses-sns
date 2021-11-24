import simplejson as json
import boto3
import os
import logging
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):

	logger.info(event)

	#load dynamodb resource
	dynamodb = boto3.resource('dynamodb')

	#try dynamodb execution
	try:
	  #load dynamodb table
	  dynamodb = boto3.resource('dynamodb')
	  table = dynamodb.Table(os.environ.get('CZ_SUBMISSION_TABLE_NAME'))
	  response = table.scan(
	  	ProjectionExpression = '#uu, date_created, #ss, #ll, what_flytipped',
	  	ExpressionAttributeNames = {'#ss': 'status', '#uu':'uuid', '#ll':'location'},
	  	FilterExpression=Attr('status').contains('new')
	  )

	  #createempty response object
	  data = {'message':'no item found'}

	  try:
	    if(len(response['Items']) > 0):
	    	#create smaller object - no PII released
	    	data = response['Items']
	  except:
	    logger.info('No result found')

	except ClientError as e:
	    return_message = e.response['Error']['Message']
	    return_status=500
	else:
	    return_message = data
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
	

