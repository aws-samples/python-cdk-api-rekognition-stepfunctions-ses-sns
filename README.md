# Fly-tipping application Sample

This is a CDK deployment of an application to support with submissions of images, ran through rekognition, and alerts shared. Image rekognition will detect labels within a user submitted image.

The `cdk.json` file contains all of the settings required to setup and configure this application
Please review the default settings held within this application before deploying. (see CONFIG instructions below)

This application will be deployed from the command line, using AWS CLI
You will also need docker running on your system to allow any images to be generated during a build phase

All AWS Lambda functions are written in Python, and are set to use version 3.9
Most of the functions within this application can be customised to save/select based on your preference.


To deploy and run this application:

First - clone the repository to your local machine or Cloud9 environment - this is assuming you've logged into the command line via CLI
```
$ git clone REPOSITORY_URL
```

Next - Setup your Python virtual environment, this ensures all dependencies are restricted to this specific application

```
$ python3 -m venv .venv
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```
$ source .venv/bin/activate
```

If you are a Windows platform, you would activate the virtualenv like this:

```
% .venv\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies.

```
$ pip install -r requirements.txt
```

At this point you can now synthesize or deploy the CloudFormation template for this code.
You may also want to run AWS configuration to select the region

```
$ aws configure
```

Then
```
$ cdk synth
```
or
```
$ cdk deploy
```

If you have a specific CLI profile you wish to use, you can run the above commands with additional parameters, eg.
```
$ cdk deploy --profile YOURPROFILE
```


To add additional dependencies, for example other CDK libraries, just add
them to your `setup.py` file and rerun the `pip install -r requirements.txt`
command.




## Application Config Details

The `cdk.json` file contains all of the settings required to setup and configure this application

By editing this file, you will set the defaults when your AWS infrastructure deploys



cors_internal_domain: Your own domain name (either running locally or in AWS S3 or EC2) - This setting will allow your domain to pass any CORS rules

citizen_get_url_link: A URL for your citizens to view further information about a submission

rekognition_min_confidence: The confidence setting for Amazon Rekognition (See: https://aws.amazon.com/rekognition/faqs/#Object_and_Scene_Detection)

email_from_sender: Your "from" email address for Amazon SES

sns_message_subject: The email subject line when sending from SNS

default_ses_email: Your default "to" email address / email address for testing purposes in SES

default_collection_teams: An array of your internal teams (for example HR, IT and Accounts)

dynamo_default_sizes: An array of default objects with sizes, for example "Tyre" (Note English (US) for Rekognition service)

new_submission_template: Email template to the citizen when a submission is made

update_submission_template: Email template to the citizen when a submission is updated




## Usage
An example form has been provided to submit a "fly tipping" submission to the API gateway



You can host this locally on your developer machine or within S3/EC2 (note, the CORS domain above)

On first initialisation, the CDK script will setup a number of default email addresses (eg. SNS and SES) - These addresses will need to be validated before a citizen submission is made.



There are 4 endpoints available within the API gateway:

1: pre_signed_url - Generate a pre signed URL for submission

2: citizen_submission - Allows the citizen to submit the full form details to process

3: get_all - Endpoint to get all "new" status (returns subset of data from DynamoDB)

4: update_page - Endpoint to allow an update of a submission status from new to in progress or complete


## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.

