import setuptools


with open("README.md") as fp:
    long_description = fp.read()


setuptools.setup(
    name="flytipping_rekognition_size_and_alerts",
    version="0.0.1",

    description="Quick start to deliver fly tipping rekognition and sizing information via S3 upload",
    long_description=long_description,
    long_description_content_type="text/markdown",

    author="hello@example.com",

    package_dir={"": "flytipping_rekognition_size_and_alerts"},
    packages=setuptools.find_packages(where="flytipping_rekognition_size_and_alerts"),

    install_requires=[
        "aws-cdk.core==1.134.0",
        "aws-cdk.aws_s3==1.134.0",
        "aws-cdk.aws_s3_deployment==1.134.0",
        "aws-cdk.aws_cloudfront==1.134.0",
        "aws-cdk.aws_lambda_python==1.134.0",
        "aws-cdk.aws_lambda==1.134.0",
        "aws-cdk.aws_lambda_destinations==1.134.0",
        "aws-cdk.aws_apigateway==1.134.0",
        "aws-cdk.aws_iam==1.134.0",
        "aws-cdk.aws_dynamodb==1.134.0",
        "aws-cdk.aws_stepfunctions==1.134.0",
        "aws-cdk.aws_stepfunctions_tasks==1.134.0",
        "aws-cdk.aws_ses==1.134.0",
        "aws-cdk.aws_sns==1.134.0",
        "aws-cdk.aws_sns_subscriptions==1.134.0",
        "aws-cdk.custom_resources==1.134.0"
    ],

    python_requires=">=3.6",

    classifiers=[
        "Development Status :: 4 - Beta",

        "Intended Audience :: Developers",

        "Programming Language :: JavaScript",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",

        "Topic :: Software Development :: Code Generators",
        "Topic :: Utilities",

        "Typing :: Typed",
    ],
)
