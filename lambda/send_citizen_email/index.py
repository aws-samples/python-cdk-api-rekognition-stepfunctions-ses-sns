import simplejson as json
import boto3
import os
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):

    #check email can be contacted
    email_contact = event['main_form']['can_contact']

    #only send email if the citizen has said it is ok to (can_contact true)
    if(email_contact.lower()=="true"):

        #load SES client
        ses = boto3.client('ses')

        #Email sent from address (from config)
        email_sender = os.environ.get('CZ_SENDER_FROM')

        #Email recipient (citizen submission)
        #Need to ensure in production SES is configred to notify bounces
        email_recipent = event['main_form']['contact_email']
        email_forename = event['main_form']['forename']

        #will have uuid if we've reached this point as its the only data returned from previous step.
        email_uuid = event['DBFunctionResult']['Payload']['body']['uuid']

        #get the API URL parameter
        api_gateway_url = os.environ.get('CZ_SENDER_URL_LINK')

        #default email template
        email_template = os.environ.get('CZ_SENDER_TEMPLATE')

        #check to see if there is an alternative template to send (eg STATUS UPDATE)
        try:
            template_key = event['template']
            email_template = os.environ.get('CZ_SENDER_TEMPLATE'+template_key)
        except:
          logger.info('No template present in event')

        # Try to send the email.
        try:
            response = ses.send_templated_email(
                Source=email_sender,
                Destination={'ToAddresses': [email_recipent]},
                Template=email_template,
                TemplateData='{ "forename":"'+email_forename+'", "link":"'+api_gateway_url+'?uuid='+email_uuid+'" }'
            )
       
        except ClientError as e:
            return_message = e.response['Error']['Message']
            return_status=500
        else:
            return_message = {'message':'Success: email sent'}
            return_status=200
    else:
        return_message = {'message':'Success: No email sent (no user permission)'}
        return_status=200
    
    return {
        'statusCode': return_status,
        'body': return_message
    }