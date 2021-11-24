from __future__ import print_function

import boto3
import os
import json
import pprint
import urllib3

SUCCESS = "SUCCESS"
FAILED = "FAILED"

http = urllib3.PoolManager()

def lambda_handler(event, context):
    print("Testing submission:")
    print(event)
    responseData = {}
    try:
        client = boto3.client('ses')
        if event['RequestType'] == "Create":
            print("request type create")
            print("temaplte name:"+event['ResourceProperties']['TemplateName'])
            pprint.pprint(client.create_template(
                Template={
                    'TemplateName': event['ResourceProperties']['TemplateName'],
                    'SubjectPart': event['ResourceProperties']['SubjectPart'],
                    'TextPart': event['ResourceProperties']['TextPart'],
                    'HtmlPart': event['ResourceProperties']['HtmlPart']
                }
            ))
        elif event['RequestType'] == "Update":
            print("request type update")
            pprint.pprint(client.update_template(
                Template={
                    'TemplateName': event['ResourceProperties']['TemplateName'],
                    'SubjectPart': event['ResourceProperties']['SubjectPart'],
                    'TextPart': event['ResourceProperties']['TextPart'],
                    'HtmlPart': event['ResourceProperties']['HtmlPart']
                }
            ))
        elif event['RequestType'] == "Delete":
            print("request type delete")
            pprint.pprint(client.delete_template(
                TemplateName=event['ResourceProperties']['TemplateName']
            ))
        send(event, context, SUCCESS, responseData, "GenericPhysicalResourceId")
    except:
        print("request type failed")
        send(event, context, FAILED, responseData, "GenericPhysicalResourceId")


def send(event, context, responseStatus, responseData, physicalResourceId=None, noEcho=False, reason=None):
    responseUrl = event['ResponseURL']

    print(responseUrl)

    responseBody = {
        'Status' : responseStatus,
        'Reason' : reason or "See the details in CloudWatch Log Stream: {}".format(context.log_stream_name),
        'PhysicalResourceId' : physicalResourceId or context.log_stream_name,
        'StackId' : event['StackId'],
        'RequestId' : event['RequestId'],
        'LogicalResourceId' : event['LogicalResourceId'],
        'NoEcho' : noEcho,
        'Data' : responseData
    }

    json_responseBody = json.dumps(responseBody)

    print("Response body:")
    print(json_responseBody)

    headers = {
        'content-type' : '',
        'content-length' : str(len(json_responseBody))
    }

    try:
        response = http.request('PUT', responseUrl, headers=headers, body=json_responseBody)
        print("Status code:", response.status)


    except Exception as e:

        print("send(..) failed executing http.request(..):", e)