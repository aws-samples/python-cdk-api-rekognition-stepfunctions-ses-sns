import simplejson as json
import boto3
import os
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):

    #get the API URL parameter
    api_gateway_url_value = os.environ.get('CZ_SENDER_API_LINK')
    
    sns_client = boto3.client('sns')

    # Try to send the SNS notification
    try:
        #need to load the SNS topic ARN from environment variables.
        #this topic is linked to the Label (eg. Tire = waste team)
        topic_arn = os.environ.get('CZ_TOPIC_'+event['InitResult'][0]['SizeFunctionResult']['Payload']['body']['notification_team'])

        #load default message in json (for https notifications)
        message = {
            'new_submission': 'true',
            'forename': event['main_form']['forename'],
            'surname': event['main_form']['surname'],
            'contact_email': event['main_form']['contact_email'],
            'contact_tel': event['main_form']['contact_tel'],
            'can_contact': event['main_form']['can_contact'],
            'latitude': event['main_form']['latitude'],
            'longitude': event['main_form']['longitude'],
            'image_reference_s3': event['main_form']['image_reference_s3'],
            'item_type': event['main_form']['item_type'],
            'item_subtype': event['main_form']['item_subtype'],
            'item_count': event['main_form']['item_count'],
            'describe_type': event['main_form']['describe_type'],
            'public_land': event['main_form']['public_land'],
            'other_information': event['main_form']['other_information'],
            'uuid': event['DBFunctionResult']['Payload']['body']['uuid'],
            'size': event['InitResult'][0]['SizeFunctionResult']['Payload']['body']['size'],
            'notification_team': event['InitResult'][0]['SizeFunctionResult']['Payload']['body']['notification_team'],
            'rekognition_label': event['InitResult'][0]['SizeFunctionResult']['Payload']['body']['rekognition_label'],
            'total_mass': event['InitResult'][0]['SizeFunctionResult']['Payload']['body']['total_mass'],
            'total_volume': event['InitResult'][0]['SizeFunctionResult']['Payload']['body']['total_volume'],
            'total_density': event['InitResult'][0]['SizeFunctionResult']['Payload']['body']['total_density']
        }

        #simple SMS message - uuid - searchable in platform
        sms_message = 'New submission to Fly Tipping Platform id: '+event['DBFunctionResult']['Payload']['body']['uuid']

        #email SNS notification, with human readible labels
        email_message = 'A new submission has been made to the Fly Tipping application\n\n' \
                                'Forename: '+event['main_form']['forename']+'\n' \
                                'Surname: '+event['main_form']['surname']+'\n' \
                                'Contact Email: '+event['main_form']['contact_email']+'\n' \
                                'Contact Telephone: '+event['main_form']['contact_tel']+'\n' \
                                'Can contact citizen: '+event['main_form']['can_contact']+'\n' \
                                'Latitude: '+str(event['main_form']['latitude'])+'\n' \
                                'Longitude: '+str(event['main_form']['longitude'])+'\n' \
                                'Image Reference: '+event['main_form']['image_reference_s3']+'\n' \
                                'Type: '+event['main_form']['item_type']+'\n' \
                                'Sub type: '+event['main_form']['item_subtype']+'\n' \
                                'Count: '+str(event['main_form']['item_count'])+'\n' \
                                'Description: '+event['main_form']['describe_type']+'\n' \
                                'On public land: '+event['main_form']['public_land']+'\n' \
                                'Any other information: '+event['main_form']['other_information']+'\n' \
                                'Size: '+str(event['InitResult'][0]['SizeFunctionResult']['Payload']['body']['size'])+'\n' \
                                'Notification Team: '+event['InitResult'][0]['SizeFunctionResult']['Payload']['body']['notification_team']+'\n' \
                                'Rekognition Label: '+event['InitResult'][0]['SizeFunctionResult']['Payload']['body']['rekognition_label']+'\n' \
                                'Total mass: '+str(event['InitResult'][0]['SizeFunctionResult']['Payload']['body']['total_mass'])+'\n' \
                                'Total volume: '+str(event['InitResult'][0]['SizeFunctionResult']['Payload']['body']['total_volume'])+'\n' \
                                'Total density: '+str(event['InitResult'][0]['SizeFunctionResult']['Payload']['body']['total_density'])+'\n' \
                                'uuid: '+event['DBFunctionResult']['Payload']['body']['uuid']+'\n\n\n' \
                                'Set status to IN PROGRESS: '+api_gateway_url_value+'/update_page?uuid='+event['DBFunctionResult']['Payload']['body']['uuid']+'&status=inprog \n\n' \
                                'Set status to COMPLETE: '+api_gateway_url_value+'/update_page?uuid='+event['DBFunctionResult']['Payload']['body']['uuid']+'&status=comp \n\n' \
                                '---END---' \

        response = sns_client.publish(
            TargetArn=topic_arn,
            Message=json.dumps({'default': json.dumps(message),
                                'sms': sms_message,
                                'email': email_message
                            }),
            Subject=os.environ.get('CZ_SNS_MSG_SUBJECT'),
            MessageStructure='json'
        )
    except ClientError as e:
        return_message = e.response['Error']['Message']
        return_status=500
    else:
        return_message = 'Success: SNS sent'
        return_status=200
    
    return {
        'statusCode': return_status,
        'body': return_message
    }