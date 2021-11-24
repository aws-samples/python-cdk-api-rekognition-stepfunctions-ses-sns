import simplejson as json
import boto3
import os
import uuid
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):

  #load the body into a python JSON object
  body = event['body']
  
  #fix for postman vs lambda console testing
  try:
    body = json.loads(body)
  except:
    logger.info('Body already JSON object')
  
  #input for state machine - mirror existing submission
  step_input = {
      'main_form': body
  }

  #load state machine client
  execute_step_function = boto3.client('stepfunctions')

  #Start state machine
  try:
    start_step_response = execute_step_function.start_execution(
        stateMachineArn = os.environ.get('CZ_STATE_MACHINE'),
        input = json.dumps(step_input)
    )
  except ClientError as e:
      return_message = e.response['Error']['Message']
      return_status=500
  else:
      return_message = 'Success'
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
