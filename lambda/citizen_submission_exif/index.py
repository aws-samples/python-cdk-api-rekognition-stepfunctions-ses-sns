import simplejson as json
import boto3
import os
import logging
import uuid
from exif import Image
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):

	logger.info(event)

	return_message = {}
	lat = lon = datetime = 0
	photo = ''
	try:
		photo = event['main_form']['image_reference_s3']
	except:
		logger.info('No image submission')
	if not photo:
		return_message['exif_success'] = 'false'
		return_status=200
	else:
		try:
			bucket = os.environ.get('CZ_S3_BUCKET')

			filename = uuid.uuid4().hex

			s3 = boto3.client('s3')
			s3.download_file(bucket, photo, '/tmp/'+filename+'.jpg')
			
			with open("/tmp/"+filename+".jpg", "rb") as uploaded_image:
				image = Image(uploaded_image)
			
			if image.has_exif:
				try:
					lat = exif_coord_to_decimal(image.gps_latitude,image.gps_latitude_ref)
					lon = exif_coord_to_decimal(image.gps_longitude,image.gps_longitude_ref)
				except:
					logger.info('No image location')
				try:
					datetime = image.datetime_original
				except:
					logger.info('No image date')
		except ClientError as e:
			return_message['error'] = e.response['Error']['Message']
			return_status=500
		else:
			return_message['exif_success'] = 'true'
			return_status=200

	return_message['lat'] = lat
	return_message['lon'] = lon
	return_message['img_datetime'] = datetime

	#return to service
	return {
		'statusCode': return_status,
		'body': return_message,
		'headers': {
		  'Content-Type': 'application/json',
		  'Access-Control-Allow-Origin': '*'
		},
	}
	
def exif_coord_to_decimal(c, cr):
	dd = c[0] + c[1]/60 + c[2]/3600
	if cr == "S" or cr == "W":
		dd = -dd
	return dd