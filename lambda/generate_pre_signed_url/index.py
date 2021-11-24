import os
import simplejson as json
import logging
import boto3
import uuid
from botocore.exceptions import ClientError
from botocore.client import Config

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):

    #generate random S3 filename - this will prevent users uploading the same filename more than once
    filename_uuid = str(uuid.uuid4())

    #get S3 bucket from environment variable
    bucket = os.environ.get('CZ_S3_BUCKET')

    #force image file to go into uploads/x.jpg
    key = "uploads/"+filename_uuid+".jpg"

    #load S3 client - inc config
    #1 - legacy sig version won't work with simple xhttp requests
    #2 - when first spinning up the environment the domain name isn't resolved so you get a 307 response for the cors request causing the browser to 500 error
    s3_client = boto3.client('s3', config=Config(signature_version='s3v4', s3={'addressing_style': 'path'}))

    #try to generate put object pre signed URL
    try:
        #try to generate URL // 2 minute timeline for submission
        response = s3_client.generate_presigned_url('put_object',Params={'Bucket': bucket, 'Key': key }, ExpiresIn=120)
    except ClientError as e:
        return_message = e.response['Error']['Message']
        return_status=500
    else:
        #create object for return message
        return_message = {
                'key':key,
                'pre_signed_url': response
            }
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
