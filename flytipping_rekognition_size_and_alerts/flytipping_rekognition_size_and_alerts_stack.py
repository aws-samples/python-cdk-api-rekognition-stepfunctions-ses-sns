import hashlib
import json

from aws_cdk import (
    aws_s3 as s3_,
    aws_s3_deployment as s3_deployment_,
    aws_cloudfront as cloudfront_,
    aws_lambda_python as lambda_python_,
    aws_lambda as lambda_,
    aws_lambda_destinations as lambda_destinations_,
    aws_apigateway as apigateway_,
    aws_iam as iam_,
    aws_dynamodb as dynamodb_,
    aws_stepfunctions as stepfunctions_,
    aws_stepfunctions_tasks as stepfunctions_tasks_,
    aws_ses as ses_,
    aws_sns as sns_,
    aws_sns_subscriptions as sns_subscriptions_,
    custom_resources as cr_,
    core as cdk
)

# For consistency with other languages, `cdk` is the preferred import name for
# the CDK's core module.  The following line also imports it as `core` for use
# with examples from the CDK Developer's Guide, which are in the process of
# being updated to use `cdk`.  You may delete this import if you don't need it.
from aws_cdk import core


class FlytippingRekognitionSizeAndAlertsStack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        #Get default stack
        cdk_stack = cdk.Stack.of(self)

        #cors domain from config
        cors_internal_domain = self.node.try_get_context('cors_internal_domain')

        ### API GATEWAY ###
        ###
        api = apigateway_.RestApi(self, 'apiGateway',
            rest_api_name=cdk_stack.stack_name,
            deploy_options=apigateway_.StageOptions(
                throttling_rate_limit=10,
                throttling_burst_limit=20,
                tracing_enabled=True
            ),
            default_cors_preflight_options=apigateway_.CorsOptions(
                allow_origins=[cors_internal_domain],
                allow_methods=apigateway_.Cors.ALL_METHODS
            )
        )
        self.api = api
        ###
        ###
        ### END API GATEWAY  




        ### SES ###
        ###
        ###
        ##### Email template for new submission
        new_submission_template_data = self.node.try_get_context('new_submission_template')
        update_submission_template_data = self.node.try_get_context('update_submission_template')

        ses_default_email = self.node.try_get_context('default_ses_email')

        #pre populate ses_email_address
        #this uses a custom resouce, which inserts the email address into SES
        pre_populate_ses_email = cr_.AwsCustomResource(self, 'init_email',
            policy=cr_.AwsCustomResourcePolicy.from_statements([
                iam_.PolicyStatement(
                    effect=iam_.Effect.ALLOW,
                    resources=['*'],
                    actions=['ses:VerifyEmailIdentity','ses:DeleteIdentity']
                )
            ]),
            on_create=cr_.AwsSdkCall(
                service='SES',
                action='verifyEmailIdentity',
                parameters={
                  'EmailAddress': ses_default_email,
                },
                physical_resource_id=cr_.PhysicalResourceId.of('verified-email')
            ),
            on_delete=cr_.AwsSdkCall(
                service='SES',
                action='deleteIdentity',
                parameters={
                  'Identity': ses_default_email,
                }
            )
        )

        #Lambda to add ses email templates
        #This Lambda calls the AWS API to add email templates to SES 
        lambda_manage_ses_templates = lambda_python_.PythonFunction(self, 'manage_ses_templates',
            entry='lambda/custom_manage_ses_templates/',
            index='index.py',
            handler='lambda_handler',
            timeout=cdk.Duration.seconds(30),
            memory_size=128,
            architecture=lambda_.Architecture.ARM_64,
            runtime=lambda_.Runtime.PYTHON_3_9,
            tracing=lambda_.Tracing.ACTIVE,
        )
        #add permissions to add email templates from Lambda function
        lambda_manage_ses_templates_access = iam_.PolicyStatement(
            effect=iam_.Effect.ALLOW, 
            actions=['ses:CreateTemplate', 'ses:GetTemplate', 'ses:UpdateTemplate', 'ses:DeleteTemplate'],
            resources=['*']                  
        )
        lambda_manage_ses_templates.add_to_role_policy(lambda_manage_ses_templates_access)

        #This handler will monitor changes to CDK for the SES email templates
        cust_prov_manage_ses_templates = cr_.Provider(self, 'ManageCustomSESProvider',
            on_event_handler=lambda_manage_ses_templates
        )
        cust_prov_new_sub_template = cdk.CustomResource(self, 'NewSubCstmResrce',
            service_token=cust_prov_manage_ses_templates.service_token,
            properties={
                'HtmlPart':new_submission_template_data['html_part'],
                'SubjectPart':new_submission_template_data['subject_part'],
                'TemplateName':new_submission_template_data['template_name'],
                'TextPart':new_submission_template_data['text_part']
            }
        )
        cust_prov_new_sub_template2 = cdk.CustomResource(self, 'NewSubCstmResrce2',
            service_token=cust_prov_manage_ses_templates.service_token,
            properties={
                'HtmlPart':update_submission_template_data['html_part'],
                'SubjectPart':update_submission_template_data['subject_part'],
                'TemplateName':update_submission_template_data['template_name'],
                'TextPart':update_submission_template_data['text_part']
            }
        )
        ### END SES ###



        ### SNS ###
        ###
        ###
        ###Load default topics from cdk setup
        ###Loop through each topic and create default topic and subscription
        sns_default_topics = self.node.try_get_context('default_collection_teams')

        sns_topic_gen = {}
        sns_env_vars = {}

        if sns_default_topics is not None:
            for sns_topic in sns_default_topics:  
                sns_topic_gen[sns_topic['team']] = sns_.Topic(self, 'sns_topic_'+sns_topic['team'],
                    display_name=sns_topic['display_name']
                )
                #add SNS topics to env vars for Lambda
                sns_env_vars['CZ_TOPIC_'+sns_topic['team']] = sns_topic_gen[sns_topic['team']].topic_arn

                if(sns_topic['default_notification_type'] == 'email'):
                    sns_topic_gen[sns_topic['team']].add_subscription( sns_subscriptions_.EmailSubscription(sns_topic['default_to']) )
                elif(sns_topic['default_notification_type'] == 'https'):
                    sns_topic_gen[sns_topic['team']].add_subscription( sns_subscriptions_.UrlSubscription(sns_topic['default_to']) )
                elif(sns_topic['default_notification_type'] == 'sms'):
                    sns_topic_gen[sns_topic['team']].add_subscription( sns_subscriptions_.SmsSubscription(sns_topic['default_to']) )
        ###
        ###
        ### END SNS ###        

        ### S3 ###
        ###
        ###
        # Upload S3 bucket
        #
        # blocks all public S3 access
        # auto delete objects after 7 days
        # upload into /uploads folder
        # add CORS rules for internal domain and API gateway URL
        s3_source_bucket = s3_.Bucket(self, 'source_bucket',
            block_public_access=s3_.BlockPublicAccess(
                block_public_acls=True,
                block_public_policy=True,
                ignore_public_acls=True,
                restrict_public_buckets=True
            ),
            auto_delete_objects=True,
            removal_policy=cdk.RemovalPolicy.DESTROY,
            lifecycle_rules=[s3_.LifecycleRule(
                expiration=cdk.Duration.days(7),
                prefix='uploads/'
            )],
            cors=[s3_.CorsRule(
                allowed_headers=["*"],
                allowed_methods=[s3_.HttpMethods.PUT],
                allowed_origins=[cors_internal_domain, 'https://'+api.rest_api_id+'.execute-api.'+cdk_stack.region+'.amazonaws.com'])
            ]
        )
        self.s3_source_bucket = s3_source_bucket
        ###
        ###
        ### END S3



        ### DYNAMODB ###
        ###
        ###
        #DynamoDB submission table
        dynamodb_cz_sub_table = dynamodb_.Table(self, 'FlyTippingRekognitionSubmissions',
            partition_key= {'name':'uuid', 'type':dynamodb_.AttributeType.STRING},
            billing_mode=dynamodb_.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb_.TableEncryption.AWS_MANAGED,
        )

        #get defaults for table insert
        dynamo_default_sizes = self.node.try_get_context('dynamo_default_sizes')
        dynamo_default_sizes_string = json.dumps(dynamo_default_sizes)
        
        #hash the array of dynamo_default_sizes - this will give us a unique ID - if this changes, it will rebuild the index
        dynamo_db_insert_hash = hashlib.sha256(dynamo_default_sizes_string.encode("UTF-8")).hexdigest()

        #DynamoDB sizing table
        dynamodb_cz_size_table = dynamodb_.Table(self, 'FlyTippingRekognitionSizing_'+dynamo_db_insert_hash,
            partition_key= {'name':'item_label', 'type':dynamodb_.AttributeType.STRING},
            billing_mode=dynamodb_.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb_.TableEncryption.AWS_MANAGED,
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )

        #pre populate dynamodb table
        pre_populate_sizing = cr_.AwsCustomResource(self, 'init_dynamo_'+dynamo_db_insert_hash,
            policy=cr_.AwsCustomResourcePolicy.from_statements([
                iam_.PolicyStatement(
                    effect=iam_.Effect.ALLOW,
                    resources=['*'],
                    actions=['dynamodb:PutItem','dynamodb:batchWriteItem']
                )
            ]),
            on_create=cr_.AwsSdkCall(
                service='DynamoDB',
                action='batchWriteItem',
                parameters={
                    'RequestItems': {
                        dynamodb_cz_size_table.table_name : dynamo_default_sizes
                    }
                },
                physical_resource_id=cr_.PhysicalResourceId.of('init_dynamo_'+dynamo_db_insert_hash)
            )
        )
        ###
        ###
        ### END DYNAMODB


        ### LAMBDA ###
        ###
        ###
        ##### Generate pre signed URL Lambda #####
        lambda_generate_presigned_url = lambda_python_.PythonFunction(self, 'generate_pre_signed_url',
            entry='lambda/generate_pre_signed_url/',
            index='index.py',
            handler='lambda_handler',
            timeout=cdk.Duration.seconds(10),
            memory_size=128,
            architecture=lambda_.Architecture.ARM_64,
            runtime=lambda_.Runtime.PYTHON_3_9,
            tracing=lambda_.Tracing.ACTIVE,
            environment={
                'CZ_S3_BUCKET': s3_source_bucket.bucket_name,
            }
        )
        #permissions for s3 bucket
        s3_source_bucket.grant_read_write(lambda_generate_presigned_url)
        ###
        ##### Lambda to detect labels (for state machine) #####
        lambda_detect_labels = lambda_python_.PythonFunction(self, 'detect_labels',
            entry='lambda/detect_labels/',
            index='index.py',
            handler='lambda_handler',
            timeout=cdk.Duration.seconds(10),
            memory_size=128,
            architecture=lambda_.Architecture.ARM_64,
            runtime=lambda_.Runtime.PYTHON_3_9,
            tracing=lambda_.Tracing.ACTIVE,
            environment={
                'CZ_REKOG_MIN_CONFIDENCE': self.node.try_get_context('rekognition_min_confidence'),
                'CZ_S3_BUCKET': s3_source_bucket.bucket_name,
            }
        )
        #permissions for s3 bucket read
        s3_source_bucket.grant_read(lambda_detect_labels,'uploads/*')

        #permission for this Lambda to access rekognition
        lambda_rekognition_access = iam_.PolicyStatement(
            effect=iam_.Effect.ALLOW, 
            actions=['rekognition:DetectLabels'],
            resources=['*']                  
        )
        lambda_detect_labels.add_to_role_policy(lambda_rekognition_access)

        ##### Lambda to detect size objects #####
        lambda_detect_labels_size = lambda_python_.PythonFunction(self, 'detect_labels_size',
            entry='lambda/detect_labels_size/',
            index='index.py',
            handler='lambda_handler',
            timeout=cdk.Duration.seconds(10),
            memory_size=128,
            architecture=lambda_.Architecture.ARM_64,
            runtime=lambda_.Runtime.PYTHON_3_9,
            tracing=lambda_.Tracing.ACTIVE,
            environment={
                'CZ_SIZE_TABLE_NAME': dynamodb_cz_size_table.table_name,
            }
        )
        #permissions for dynamodb
        dynamodb_cz_size_table.grant_read_data(lambda_detect_labels_size)

        #lambda - save submission to database
        lambda_save_submission_to_db = lambda_python_.PythonFunction(self, 'citizen_submission_save_dynamo',
            entry='lambda/citizen_submission_save_dynamo/',
            index='index.py',
            handler='lambda_handler',
            timeout=cdk.Duration.seconds(10),
            memory_size=128,
            architecture=lambda_.Architecture.ARM_64,
            runtime=lambda_.Runtime.PYTHON_3_9,
            tracing=lambda_.Tracing.ACTIVE,
            environment={
                'CZ_SUBMISSION_TABLE_NAME': dynamodb_cz_sub_table.table_name,
            }
        )
        #permission for DynamoDB
        dynamodb_cz_sub_table.grant_read_write_data(lambda_save_submission_to_db)

        #lambda - get all submission
        lambda_citizen_submission_get_all = lambda_python_.PythonFunction(self, 'citizen_submission_get_all',
            entry='lambda/citizen_submission_get_all/',
            index='index.py',
            handler='lambda_handler',
            timeout=cdk.Duration.seconds(10),
            memory_size=128,
            architecture=lambda_.Architecture.ARM_64,
            runtime=lambda_.Runtime.PYTHON_3_9,
            tracing=lambda_.Tracing.ACTIVE,
            environment={
                'CZ_SUBMISSION_TABLE_NAME': dynamodb_cz_sub_table.table_name,
            }
        )
        #permission for DynamoDB
        dynamodb_cz_sub_table.grant_read_write_data(lambda_citizen_submission_get_all)

        #lambda for citizen email
        lambda_send_citizen_email = lambda_python_.PythonFunction(self, 'send_citizen_email',
            entry='lambda/send_citizen_email/',
            index='index.py',
            handler='lambda_handler',
            timeout=cdk.Duration.seconds(10),
            memory_size=128,
            architecture=lambda_.Architecture.ARM_64,
            runtime=lambda_.Runtime.PYTHON_3_9,
            tracing=lambda_.Tracing.ACTIVE,
            environment={
                'CZ_SENDER_TEMPLATE': new_submission_template_data['template_name'],
                'CZ_SENDER_TEMPLATE_STATUS_UPDATE': update_submission_template_data['template_name'],
                'CZ_SENDER_FROM': self.node.try_get_context('email_from_sender'),
                'CZ_SENDER_URL_LINK': self.node.try_get_context('citizen_get_url_link')
            }
        )
        #add permissions to send email from Lambda function
        lambda_send_citizen_email_access = iam_.PolicyStatement(
            effect=iam_.Effect.ALLOW, 
            actions=['ses:SendEmail', 'SES:SendTemplatedEmail'],
            resources=['*']                  
        )
        lambda_send_citizen_email.add_to_role_policy(lambda_send_citizen_email_access)


        #lambda - save submission to database
        lambda_update_submission_status = lambda_python_.PythonFunction(self, 'citizen_submission_update_status',
            entry='lambda/citizen_submission_update_status/',
            index='index.py',
            handler='lambda_handler',
            timeout=cdk.Duration.seconds(10),
            memory_size=128,
            architecture=lambda_.Architecture.ARM_64,
            runtime=lambda_.Runtime.PYTHON_3_9,
            tracing=lambda_.Tracing.ACTIVE,
            environment={
                'CZ_SUBMISSION_TABLE_NAME': dynamodb_cz_sub_table.table_name,
                'CZ_EMAIL_LAMBDA': lambda_send_citizen_email.function_name
            }
        )
        #permission for DynamoDB
        dynamodb_cz_sub_table.grant_read_write_data(lambda_update_submission_status)
        lambda_send_citizen_email.grant_invoke(lambda_update_submission_status)


        #lambda - exif
        lambda_citizen_submission_exif = lambda_python_.PythonFunction(self, 'lambda_citizen_submission_exif',
            entry='lambda/citizen_submission_exif/',
            index='index.py',
            handler='lambda_handler',
            timeout=cdk.Duration.seconds(30),
            memory_size=256,
            architecture=lambda_.Architecture.ARM_64,
            runtime=lambda_.Runtime.PYTHON_3_9,
            tracing=lambda_.Tracing.ACTIVE,
            environment={
                'CZ_S3_BUCKET': s3_source_bucket.bucket_name,
            }
        )
        #permissions for s3 bucket read
        s3_source_bucket.grant_read(lambda_citizen_submission_exif,'uploads/*')


        #lambda for SNS topic sending message
        #add to env vars (API gateway URL)
        sns_env_vars['CZ_SENDER_API_LINK'] = 'https://'+api.rest_api_id+'.execute-api.'+cdk_stack.region+'.amazonaws.com/prod'
        sns_env_vars['CZ_SNS_MSG_SUBJECT'] = self.node.try_get_context('sns_message_subject')

        lambda_send_internal_notification = lambda_python_.PythonFunction(self, 'send_internal_notification',
            entry='lambda/send_internal_notification/',
            index='index.py',
            handler='lambda_handler',
            timeout=cdk.Duration.seconds(10),
            memory_size=128,
            architecture=lambda_.Architecture.ARM_64,
            runtime=lambda_.Runtime.PYTHON_3_9,
            tracing=lambda_.Tracing.ACTIVE,
            environment=sns_env_vars
        )
        #add permissions to send sns from Lambda function
        lambda_send_internal_notification_policy = iam_.PolicyStatement(
            effect=iam_.Effect.ALLOW, 
            actions=['sns:Publish'],
            resources=['*']                  
        )
        lambda_send_internal_notification.add_to_role_policy(lambda_send_internal_notification_policy)

        ###
        ###
        ### END LAMBDA


        ### API GATEWAY ENDPOINTS ###
        ###
        ###
        api_pre_signed = api.root.add_resource('pre_signed_url')
        api_pre_signed_post_method = api_pre_signed.add_method(
            http_method='POST',
            integration=apigateway_.LambdaIntegration(
                handler=lambda_generate_presigned_url
            )
        )

        api_index = api.root.add_resource('get_all')
        api_index_method = api_index.add_method(
            http_method='GET',
            integration=apigateway_.LambdaIntegration(
                handler=lambda_citizen_submission_get_all
            )
        )

        api_index = api.root.add_resource('update_page')
        api_index_method = api_index.add_method(
            http_method='GET',
            integration=apigateway_.LambdaIntegration(
                handler=lambda_update_submission_status
            )
        )
        ###
        ###
        ### END API GATEWAY


        ### STEP FUNCTIONS ###
        ###
        ###
        #state machine - detect labels, validate size, update db, email citizen, publish sns topic?

        state_machine = stepfunctions_.StateMachine(
            self, 'FlyTippingStateMachine',
            definition=

                stepfunctions_.Parallel(self,'paralletStart',result_path='$.InitResult')
                .branch(
                    stepfunctions_tasks_.LambdaInvoke(
                            self, 'Image Rekognition (Detect Labels)',#
                            lambda_function=lambda_detect_labels,
                            payload=stepfunctions_.TaskInput.from_json_path_at('$'),
                            result_path='$.RekognitionResult'
                    ).next(
                        stepfunctions_tasks_.LambdaInvoke(
                            self, 'Image Rekognition (Search Label Size)',#
                            lambda_function=lambda_detect_labels_size,
                            payload=stepfunctions_.TaskInput.from_json_path_at('$'),
                            result_path='$.SizeFunctionResult'
                        )
                    )
                ).branch(
                    stepfunctions_tasks_.LambdaInvoke(
                        self, 'Image Rekognition (Image EXIF)',#
                        lambda_function=lambda_citizen_submission_exif,
                        payload=stepfunctions_.TaskInput.from_json_path_at('$'),
                        result_path='$.EXIFFunctionResult'
                    )
                ).next(
                    stepfunctions_tasks_.LambdaInvoke(
                        self, 'Image Rekognition (Save all to Dynamo DB)',#
                        lambda_function=lambda_save_submission_to_db,
                        payload=stepfunctions_.TaskInput.from_json_path_at('$'),
                        result_path='$.DBFunctionResult'
                    )
                ).next(
                    stepfunctions_.Parallel(self,'paralletParts').branch(
                        stepfunctions_tasks_.LambdaInvoke(
                            self, 'Image Rekognition (Send citizen email)',#
                            lambda_function=lambda_send_citizen_email,
                            payload=stepfunctions_.TaskInput.from_json_path_at('$'),
                            result_path='$.EmailFunctionResult'
                        )
                    ).branch(
                        stepfunctions_tasks_.LambdaInvoke(
                            self, 'Image Rekognition (Send SNS)',#
                            lambda_function=lambda_send_internal_notification,
                            payload=stepfunctions_.TaskInput.from_json_path_at('$'),
                            result_path='$.SNSFunctionResult'
                        )
                    )
                ),
            timeout=core.Duration.seconds(60),
        )

        self.state_machine = state_machine

        ## Lambda - submission citizen request
        lambda_citizen_submission = lambda_python_.PythonFunction(self, 'citizen_submission',
            entry='lambda/citizen_submission/',
            index='index.py',
            handler='lambda_handler',
            timeout=cdk.Duration.seconds(10),
            memory_size=128,
            architecture=lambda_.Architecture.ARM_64,
            runtime=lambda_.Runtime.PYTHON_3_9,
            tracing=lambda_.Tracing.ACTIVE,
            environment={
                'CZ_STATE_MACHINE': state_machine.state_machine_arn
            }
        )
        #permissions step function
        state_machine.grant_start_execution(lambda_citizen_submission)

        api_citizen_submission = api.root.add_resource('citizen_submission')
        api_citizen_submission_post_method = api_citizen_submission.add_method(
            http_method='POST',
            integration=apigateway_.LambdaIntegration(
                handler=lambda_citizen_submission
            )
        )
        ###
        ###
        ### END STEP FUNCTION

        #get some API variables
        cdk.CfnOutput(
            self, 'apiURL',
            value=api.url
        )
