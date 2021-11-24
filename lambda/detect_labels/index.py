import simplejson as json
import boto3
import os
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):

    logger.info(event)
    
    photo = ''
    try:
        #take s3 image from reference field
        photo = event['main_form']['image_reference_s3']
    except:
        logger.info('No image submission')

    if not photo:
        #status 200 / no rekognition complete (want to do remaining items)
        return_message = {'rekognition_success':'false'}
        return_status=200
    else:
        #load rekognition client
        client=boto3.client('rekognition')
        #load bucket default from ENV variables
        bucket = os.environ.get('CZ_S3_BUCKET')
        #load min confidence from ENV variables
        rekognition_min_confidence = float(os.environ.get('CZ_REKOG_MIN_CONFIDENCE'))

        #Start rekognition service
        try:
            data = client.detect_labels(
                Image={'S3Object': {'Bucket': bucket, 'Name': photo}},
                MinConfidence=rekognition_min_confidence
            )
            response = {'rekognition_success':'false'}
            #only return labels if there have been any returned, else return false submission

            try:
              if(len(data['Labels']) > 0):
                #create smaller object - no PII released
                response['Labels'] = data['Labels']
                response['rekognition_success'] = 'true'
            except:
              logger.info('No result found')

                
        except ClientError as e:
            return_message = e.response['Error']['Message']
            return_status=500
        else:
            return_message = response
            return_status=200

    #return to service
    return {
        'statusCode': return_status,
        'body': return_message,
        'headers': {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*'
        },
    }
