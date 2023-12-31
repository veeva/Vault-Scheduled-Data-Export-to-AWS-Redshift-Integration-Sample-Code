# Scheduled Data Export (SDE) to Redshift Integration Sample Code Guide

The SDE to Redshift Integration sample code extends the capabilities of Scheduled Data Exports (SDE). Its primary goal is to transform SDE-generated Vault data into a format that is accessible within your Amazon Redshift data store.

This guide describes how the sample code functions and how you can use it to enhance your data integration process.
![integration-block-diagram drawio (1)](https://github.com/mukul-hodarkar/template-integration-code/assets/54867444/4e242e90-3ce1-45cb-8ce0-6e133a93dab7)



## Integration Process

The process involves five steps:

1. **File Notification**: The sample code monitors the specified S3 bucket for incoming CSV files associated with Vault objects. S3 notifications trigger an event that informs an associated SNS topic.
2. **SQS Enqueue**: Upon SNS notification, metadata related to the uploaded files is dispatched to an SQS queue designed to receive such messages.
3. **Lambda Trigger**: The SQS queue invokes a Lambda function, enabling it to process messages. You can control the number of messages processed by a single Lambda invocation.
4. **Data Processing**: The Lambda function, in coordination with Vault metadata object APIs, retrieves object details. The sample code then assesses the need to create or update Redshift tables based on these details.
5. **Data Loading**: The sample code transfers the records from S3 files to corresponding Redshift tables using efficient copy commands. This streamlined approach optimizes performance and reduces processing time.
6. **Logging and Cleanup**: Thorough logs are maintained, documenting successful and erroneous file processing. After a successful processing cycle, the SQS message is removed from the queue.

## Setup Instructions

Before you can use the SDE to Redshift Integration sample code, you'll need to configure a variety of components in your AWS Management Console. See the [AWS Documentation](https://docs.aws.amazon.com/index.html) for help with creating an AWS account.

The sections below will guide you through setting up the following AWS components:

* S3 bucket
* SNS topics
* SQS queues
* Redshift database
* IAM policies
* Secrets Manager
* ECR repositories
* Lambda functions

All configuration details, such as passwords and IAM role names, are stored in the **`config.ini`** file in the AWS Secrets Manager.

The sample code requires an S3 bucket to store the exports generated by the scheduled data export process.

### The S3 Bucket
You must have an Amazon S3 bucket configured to receive scheduled data export files.
If you need assistance with creating an S3 bucket for Scheduled Data Export, please refer to - [Veeva Vault Documentation](https://platform.veevavault.help/en/gr/70128/#accessing-exported-data) for detailed instructions.

* **Bucket Name**: Create an S3 bucket with a suitable name, such as `sde-integration`.
* **Region**: Choose the appropriate region for your use case. The provided sample code is configured to work with the `us-east-1` (North Virginia) region by default. If you intend to use a different region, please make the necessary adjustments to the code to match your specific region.
* **SNS Topic and S3 Bucket Region Matching:** Please note that the SNS Topic and the S3 Bucket need to be in the same region. If they are not in the same region, you may encounter errors when configuring the integration. Ensure that you create both resources in the same region to avoid any issues.


### Setting Up the SNS Topic

The SNS (Simple Notification Service) topic listens to `PUT` actions within your designated S3 bucket and initiates the flow of events that drive the integration process.

To configure the SNS topic:
    
1. Create the SNS Topic and set the following values:
    - **Type**: Standard
    - **Name**: 'datastream-sde-integration'
2. Configure the Access Policy:
    - Adjust the sample access policy below with specific details related to your AWS account and resources.
    - The sample policy template grants permissions for various actions related to the SNS topic and its subscriptions. Please review and customize the policy for your use case.
    
    ```json
  
    {
      "Version": "2008-10-17",
      "Id": "__default_policy_ID",
      "Statement": [
        {
          "Sid": "__default_statement_ID",
          "Effect": "Allow",
          "Principal": {
            "AWS": "*"
          },
          "Action": [
            "SNS:Publish",
            "SNS:RemovePermission",
            "SNS:SetTopicAttributes",
            "SNS:DeleteTopic",
            "SNS:ListSubscriptionsByTopic",
            "SNS:GetTopicAttributes",
            "SNS:AddPermission",
            "SNS:Subscribe"
          ],
          "Resource": "<ARN for the SNS topic>",
          "Condition": {
            "StringEquals": {
              "AWS:SourceOwner": "<AWS Owner Account ID>"
            }
          }
        },
        {
          "Sid": "__console_pub_0",
          "Effect": "Allow",
          "Principal": {
            "AWS": "arn:aws:iam::<AWS Owner Account ID>:root"
          },
          "Action": "SNS:Publish",
          "Resource": "<ARN for the SNS topic>"
        },
        {
          "Sid": "__console_sub_0",
          "Effect": "Allow",
          "Principal": {
            "AWS": "arn:aws:iam::<AWS Owner Account ID>:root"
          },
          "Action": [
            "SNS:Subscribe",
            "SNS:Receive"
          ],
          "Resource": "<ARN for the SNS topic>"
        },
        {
          "Sid": "s3-call",
          "Effect": "Allow",
          "Principal": {
            "AWS": "*"
          },
          "Action": "SNS:Publish",
          "Resource": "<ARN for the SNS topic>",
          "Condition": {
            "StringEquals": {
              "aws:SourceAccount": "<AWS Owner Account ID>"
            },
            "ArnLike": {
              "aws:SourceArn": "<ARN for the S3 bucket>"
            }
          }
        }
      ]
    }
    
    ```
    
By establishing the SNS topic, you are establishing a vital communication channel that enables the seamless progression of your integration service. This topic will be the conduit through which S3 events initiate the data integration workflow.

## Setting Up SQS Queues

The sample code setup uses two SQS (Simple Queue Service) queues: the **Input Queue** and the **Error Queue**. The following steps show how to configure these queues.

### Setting Up the Error Queue
    
The Error Queue, referred to as `datastream-sde-integration-error-queue`, serves as a destination for messages that encounter errors during processing.

#### Configuration Details

In the Amazon SQS console, create a queue and set the following values:

  * **Type**: Standard
  * **Dead-letter queue**: -
  * **Visibility timeout**: 30 seconds
  * **Message retention period**: 4 days

#### Access Policy

  - In the sample access policy below, replace the placeholder `<AWS Owner Account ID>` with your specific AWS account ID.
  - Adjust the sample access policy below with specific details related to your AWS account and resources.
  - The sample policy template grants permissions for various actions. Please review and customize the policy for your use case.
    
  ```json
  {
    "Version": "2012-10-17",
    "Id": "__default_policy_ID",
    "Statement": [
      {
        "Sid": "__owner_statement",
        "Effect": "Allow",
        "Principal": {
          "AWS": "arn:aws:iam::<AWS Owner Account ID>:root"
        },
        "Action": "SQS:*",
        "Resource": "<ARN for datastream-sde-integration-error-queue>"
      }
    ]
  }
  
  ```


### Setting Up the Input Queue

  The Input Queue, referenced as `datastream-sde-integration-input-queue`, receives messages triggered by S3 events via the SNS topic.
    
#### Configuration Details

In the Amazon SQS console, create a queue and set the following values:

  * **Type**: Standard
  * **Dead-letter queue**: Enabled
  * **Visibility timeout**: 5 minutes
  * **Message retention period**: 1 day

 Leave the other settings as default.

### Adding a dead-letter queue details for input sqs queue

1. In the Amazon SQS console, navigate to SQS.
2. Locate and select your input SQS queue named datastream-sde-integration-input-queue. 
3. Click on Edit to modify the queue settings. 
4. Scroll down to the Dead-letter queue section. 
5. From the dropdown labeled "Choose queue," select datastream-sde-integration-error-queue, which will serve as the dead-letter queue for error handling. 
6. Save the configuration to apply the changes.
This setup ensures that any messages that encounter errors or issues while processing in the input queue will be moved to the designated dead-letter queue for further analysis and troubleshooting.

Setting up these SQS queues establishes communication between components in the integration process. The input queue receives messages from S3 events via the SNS topic, while the error queue serves as a safe destination for messages encountering processing errors.


### Add an SNS Topic Subscription
1. Specify the **Topic ARN** (Amazon Resource Name) for the SNS topic you created earlier.
2. Set the **Protocol** as **Amazon SQS**.
3. Provide the **Endpoint** as the **ARN for the input SQS queue** that will receive messages from the SNS topic.

### Setting Up the S3 Bucket Event Notification

#### Configuring the Event Notification

In the Amazon S3 console, navigate to the bucket you created in the previous step, create an event notification and set the following values:

* **Event Name**: Define a descriptive event name, such as `sde-inbound-data`.
* **Suffix**: Set the suffix to `.csv`, indicating that event notifications are triggered when CSV files are uploaded.
* **Event Types**: Choose the appropriate event types. In this case, you can include only the `Put` event (`s3:ObjectCreated:Put`) since you are interested in files being uploaded.
* **Destination**: Select **SNS topic** as the destination for the event notification.
* **Specify SNS topic**: Enter the ARN of the previously created SNS topic. This connects the event to the SNS topic.

With these steps, you have set up an S3 bucket named `sde-integration` and configured event notifications to trigger when CSV files are uploaded to the bucket. These notifications are sent to the SNS topic you previously created.

At this point, you have successfully set up the initial components required for the SDE to Redshift Integration sample code to function: **S3 bucket** → **SNS topic** → **SQS queues**.

In the following sections, you will set up the data warehouse by configuring Amazon Redshift, IAM policies, Lambda, and more to make your SDE to Redshift Integration sample code fully operational.

## Setting Up Amazon Redshift

To enable the sample code to funtion, you need an Amazon Redshift cluster to store and manage the integrated data.

### Creating a Redshift Cluster

In the Amazon Redshift console, create a cluster and set the following values:

1. **Cluster Identifier**: Choose an appropriate identifier for your cluster, like `integration-redshift-cluster`.
2. **Node Type**: Select `dc2.large` as the node type.
3. **Number of Nodes**: Set the number of nodes to `1`.
4. **Automated Snapshot Retention Period**: Set this to `1` day.
5. **Manual Snapshot Retention Period**: Choose `Indefinitely` to retain manual snapshots.
6. **Database Configurations**:
    - **Database Name**: Specify a name for your database, such as `dev`.
    - **Port**: Use the default port `5439`.
    - **Admin User Name**: Choose a suitable admin username.
    - **Admin Password**: Set a secure password for the admin user.

### Associate IAM Roles

To enable necessary permissions for your Redshift cluster, you need to create two IAM roles and assign specific policies to them. Follow these steps:

#### Create and Assign Policies to IAM Roles

1. **AWSServiceRoleForRedshift**: Create an IAM role named `AWSServiceRoleForRedshift` and attach the `AmazonRedshiftServiceLinkedRolePolicy` policy to it. This policy allows Amazon Redshift to assume the service-linked role.

2. **RedshiftS3Read**: Create another IAM role named `RedshiftS3Read` and attach the `AmazonS3ReadOnlyAccess` policy to it. This policy grants read-only access to Amazon S3 resources.

#### Associate IAM Roles with Your Redshift Cluster

After creating and assigning policies to the IAM roles, associate these roles with your Redshift cluster. Here's how:

- Access your Redshift cluster settings or configuration.

- Navigate to the section where you can manage IAM roles associated with your cluster.

- Associate the `AWSServiceRoleForRedshift` with the appropriate permissions for Amazon Redshift.

- Similarly, associate the `RedshiftS3Read` role to provide read-only access to Amazon S3.

By following these steps, your Redshift cluster will have the necessary IAM roles and permissions configured for smooth operation.

#### Create Database and Schema

Inside your Redshift cluster, create a database where your integrated data will reside. Also, create a schema within the database where the code will generate Redshift tables.

#### Obtain Connection Details

You will need the following details to connect to your Redshift cluster:

- **Cluster Endpoint**: This is the endpoint URL you'll use to connect to the cluster.
- **Port**: Use the default port `5439`.
- **Database Name**: The name of the database you created.
- **Admin User Name**: The admin user name you specified.
- **Admin Password**: The admin user's password.

With these steps, you have successfully set up Amazon Redshift to store and manage the integrated data generated by the SDE to Redshift Integration sample code. We will refer to the Redshift cluster as `integration-redshift-cluster` in the integration process.

#### Create IAM role for redshift clusters
Now, you need to create an IAM role `iam_redshift_s3_read` and attach the `AmazonS3ReadOnlyAccess` policy to it. 
This role is referenced in the config.ini file. It is used by the sample code for running copy and update commands on Redshift tables.


## Configuring AWS Secrets Manager

The SDE to Redshift Integration sample code relies on a configuration file named `config.ini` to manage various settings. To ensure security and maintainability, we recommended storing this configuration file in AWS Secrets Manager. For smooth execution of the code, all configuration information should be accurate and updated at all the times.

### Creating the config.ini File

Create a config.ini file with the following structure:
```text

[system]
year=Current-Year-in-yyyy-format

[vault]
username=username@domain.com
password=password
dns=https://domain.vaultdev.com
version=vault-version

[redshift]
host=redshift-host-details
port=port
user=username
password=password
dbname=redshift-database-name
schema=redshift-schema-name
iam_redshift_s3_read=arn-for-the-iam-role-to-access-S3-and-redshift

[s3]
bucket_name=s3-bucket-name-for-scheduled-data-exports-are-stored

[sqs]
input_queue=https-link-to-the-input-sqs-queue
error_queue=https-link-to-the-sqs-queue-error-queue
max_number_of_messages=integer-value-for-messages-to-handle-per-request
visibility_timeout=interger-value-for-the-visibility-timeout
```

#### Explanation:

```text
year=2023: Represents the current year, which should be set according to the current year.
```

```text
[vault] Section: This section holds information for connecting to your Veeva Vault instance. For instance:
username: Your Vault username.
password: Your Vault password.
dns: The URL of your Vault instance, usually in the format https://<domain>.vaultdev.com.
version: The version of your Veeva Vault, for example, v22.3.

**The code uses your vault credentials to query vault metadata API to fetch some information. For this purpose, you will need to provide vault credentials username, password, vault DNS and version**
```

```text
[redshift] Section: Contains details about your Amazon Redshift cluster, including the IAM role required for access. For example:
host: The endpoint of your Redshift cluster.
port: The port number for Redshift (default is 5439).
user: Your Redshift username.
password: Your Redshift password.
dbname: The name of your Redshift database.
schema: The Redshift schema name.
iam_redshift_s3_read: The ARN (Amazon Resource Name) for the IAM role used to access both S3 and Redshift.

**Details about redshift cluster including IAM role, the database name, the schema in it.** 
```

```text
[s3] Section: This section specifies the name of the Amazon S3 bucket where your scheduled data exports are stored. 
You only need to input the name of the bucket, not the full S3 URL. For example, if your S3 bucket URL is s3://sde-integration/, you should input sde-integration in this section.
```

```text
[sqs] Section: Provides configuration details for Amazon SQS, including input and error queues:
input_queue: The URL for the input SQS queue.
error_queue: The URL for the SQS queue designated for handling errors.
max_number_of_messages: An integer value representing the number of messages a Lambda function should read per run (e.g., 10).
visibility_timeout: An integer value representing the visibility timeout for SQS messages (e.g., 30 seconds).
```
    

In the AWS Secrets Manager console, store this file under the name `config.ini`. The code will fetch these details during runtime.

The ARN should have the following structure:

```
 arn:aws:secretsmanager:<aws-region>:<<AWS Owner Account ID>>:secret:config.ini-
```

With the configuration stored securely in AWS Secrets Manager, your SDE to Redshift Integration sample code can fetch these details during runtime without exposing sensitive information. This ensures the safety and accuracy of your integration process.

## Creating a Docker Image and Uploading it to Amazon Elastic Container Registry (ECR)

The sample code leverages a Docker image that encapsulates all the necessary code files and installed requirements. This image serves as the foundation for the entire integration process. Subsequent steps will use this image as the base for the Lambda functions.
This image forms the backbone of the SDE to Redshift Integration sample code, ensuring consistent and optimized execution of the integration workflows.

You can build your own Docker image and upload it to AWS ECR using the following script:

```bash
#!/bin/bash

# Set the image name as a command parameter
image_name=$1

# Build the Docker image
docker build -t $image_name:test .

# Authenticate Docker CLI to Amazon ECR
aws ecr get-login-password --region <AWS region> | docker login --username AWS --password-stdin <AWS Account ID>.dkr.ecr.us-east-1.amazonaws.com

# Create the ECR repository
aws ecr create-repository --repository-name $image_name --image-scanning-configuration scanOnPush=true --image-tag-mutability MUTABLE

# Tag the Docker image
docker tag $image_name:test <AWS Account ID>.dkr.ecr.us-east-1.amazonaws.com/$image_name:latest

# Push the Docker image to ECR
docker push <AWS Account ID>.dkr.ecr.us-east-1.amazonaws.com/$image_name:latest
```

Run the script in a command-line terminal. (Following instructions are from macOS environment)
1. Open the terminal
2. Navigate to the directory where the script is saved using the **`cd`** command. For example, if the script is saved in the **`~/scripts`** directory, you would use:
```bash
cd ~/scripts
```
3. Make the script executable using the **`chmod`** command:
```bash
chmod +x your_script_name.sh
```
Replace **`your_script_name.sh`** with the actual name of your script.

4. Run the script by typing its name and providing the necessary parameters. For example:
```bash
./your_script_name.sh my_image_name
```
Replace **`your_script_name.sh`** with the actual name of your script and **`my_image_name`** with the image name you want to use.

Make sure you have the AWS CLI and Docker installed and properly configured on your machine. Also, ensure that you have the necessary AWS permissions to perform the actions described in the script, such as creating ECR repositories and pushing Docker images to ECR.

## Creating the Lambda Function

The SDE to Redshift Integration sample code Lambda function serves as the compute engine for processing scheduled data export files. It is triggered by messages in an SQS input queue, and it executes the container image code upon new file uploads to the specified S3 bucket.

## Lambda IAM role - Configuring an IAM role to allow lambda funtion to interact with AWS services

When configuring your IAM role to grant Lambda access to AWS resources, it's important to strike a balance between convenience and security.
The lambda needs to have access to follwoing services -
1. Amazon Redshift: For seamless integration with Redshift data warehousing.
2. Amazon S3: To interact with S3 storage, facilitating data transfer and storage.
3. Amazon SQS: Enabling efficient communication through Simple Queue Service.
4. AWS Lambda: Specifically for queue execution using the AWS Lambda SQS Queue Execution Role.
5. AWS Secrets Manager: To manage secrets and sensitive information securely.


To streamline the setup, we are using a set of AWS managed policies to attach to the IAM role:
1. AmazonRedshiftFullAccess
2. AmazonS3FullAccess
3. AmazonSQSFullAccess
4. AWSLambdaSQSQueueExecutionRole
5. SecretsManagerReadWrite

These policies offer maximum access to the respective services, ensuring a smooth integration process. However, it's crucial to assess your specific requirements and consider whether you need to dial down on the full access policies for security reasons.
We encourage you to evaluate your project's needs carefully and adjust the attached policies accordingly. This allows you to maintain a balance between functionality and security, ensuring your IAM role grants precisely the access required for your use case.
Your security and compliance are paramount, and tailoring permissions to your specific needs is a critical step in achieving that balance.


#### To create the Lambda:
1. From the AWS Lambda console, open the Functions page and select **Create Function**.
2. Select **Container image**.
3. Set the following values:
- **Function Name**: <Name-for-lambda-funtion>
- **Container image URI**: Container image URI should be the AWS ECR URI for the docker image created above.
- **Execution Role**: An IAM role with permissions to access the following:
    - SQS queue
    - S3 bucket
    - Secrets manager
    - Execute Lambda functions
    - Redshift
- Click `Create Function`
4. Please change the Timeout for the lambda from 3 seconds to 5 minutes. 

#### Configure Trigger for Lambda:
- Go to the above created lambda funtion.
- Under `Configuration` Tab, you will see `Triggers` on the lsft hand menu pane.
- Select 'Add trigger'. Use following configuration details to set it up.
- **Trigger Configuration**:
    - Source: Amazon SQS
    - SQS Queue: Specify the SQS queue - input queue that receives messages whenever new scheduled data export files are uploaded.
    - Activate trigger: YES
    - Batch window: *None*
    - Maximum concurrency: Set an appropriate concurrency for processing efficiency.
    - On-failure destination: *None*
    - Report batch item failures: Yes
    - Batch Size: Set an appropriate batch size for processing efficiency.


## Configure SQS policies

### Access Policy for the Input Queue 
The Input Queue, referenced as `datastream-sde-integration-input-queue`, receives messages triggered by S3 events via the SNS topic.
Customize the sample access policy below.
  - Adjust the placeholders (for example, `<AWS Owner Account ID>`, `<ARN for Lambda IAM role>`, `<ARN for the S3 bucket>`, `<ARN for the SNS topic>`) with your specific information.
  - This policy template defines permissions for various actions on the input queue and specifies conditions based on your environment.
  - Adjust the sample access policy below with specific details related to your AWS account and resources.
  - The sample policy template grants permissions for various actions related to the SQS. Please review and customize the policy for your use case.
    
    ```json
    {
      "Version": "2012-10-17",
      "Id": "__default_policy_ID",
      "Statement": [
        {
          "Sid": "__owner_statement",
          "Effect": "Allow",
          "Principal": {
            "AWS": "arn:aws:iam::<AWS Owner Account ID>:root"
          },
          "Action": "SQS:*",
          "Resource": "<ARN for datastream-sde-integration-input-queue>"
        },
        {
          "Sid": "__receiver_statement",
          "Effect": "Allow",
          "Principal": {
            "AWS": "<ARN for Lambda IAM role>"
          },
          "Action": [
            "SQS:ChangeMessageVisibility",
            "SQS:DeleteMessage",
            "SQS:ReceiveMessage"
          ],
          "Resource": "<ARN for datastream-sde-integration-input-queue>"
        },
        {
          "Sid": "__default_policy_ID",
          "Effect": "Allow",
          "Principal": {
            "AWS": "*"
          },
          "Action": "SQS:SendMessage",
          "Resource": "<ARN for datastream-sde-integration-input-queue>",
          "Condition": {
            "StringEquals": {
              "aws:SourceAccount": "<AWS Owner Account ID>"
            },
            "ArnLike": {
              "aws:SourceArn": "<ARN for the S3 bucket>"
            }
          }
        },
        {
          "Sid": "topic-subscription-<ARN for the SNS topic>",
          "Effect": "Allow",
          "Principal": {
            "AWS": "*"
          },
          "Action": "SQS:SendMessage",
          "Resource": "<ARN for datastream-sde-integration-input-queue>",
          "Condition": {
            "ArnLike": {
              "aws:SourceArn": "<ARN for the SNS topic>"
            }
          }
        }
      ]
    }
    ```

## SQS messages getting stuck in flight mode?
You are facing long-polling issue associated with SQS-Lambda integrtation. Its a well known issue in AWS community. Following are two alternatives to work around the long-polling issue.
1. Try this - https://aws.amazon.com/blogs/compute/introducing-maximum-concurrency-of-aws-lambda-functions-when-using-amazon-sqs-as-an-event-source/
2. Use of EventBridge Scheduler - This method provides an effective alternative. This approach allows you to schedule your Lambda function to run at specified intervals, eliminating the need for continuous polling and conserving resources.

**Setting Up EventBridge Schedule**
- Configuring EventBridge to trigger your Lambda function on a schedule is straightforward: 
- Navigate to AWS Eventbridge - Scheduler. Under Scheduler, you will find Schedules.
- Define the Schedule: In the configuration, specify the schedule at which you want your Lambda function to run. For this scenario, a recurring schedule would be ideal. You can set a rate-based schedule that runs at pre-defined, regular intervals. A fixed-rate expression consists of two required fields: value and unit. For Unit, choose from minutes, hours, and days. such as every 5 hours, daily, or as needed for your workflow.
- Select the Lambda Function: Attach your Lambda function as the target for this scheduler. This ensures that your function executes according to the defined schedule.
- Save and Activate: Save the configuration, and activate to put it into effect.
- Important Note: When using Eventbridge, remember to remove the SQS trigger that you previously set up in your Lambda function.
For detailed instructions on setting up EventBridge rules, refer to the AWS EventBridge documentation - https://docs.aws.amazon.com/scheduler/latest/UserGuide/getting-started.html?icmpid=docs_console_unmapped.
    
## Important Note: Column Naming Restrictions

The integration code requires special attention to column naming conventions in your input files. The code does not support column names in the format of `columnname.field`, which can be generated by Scheduled Data Export e.g. `status__c.label`

**Why?** 

Amazon Redshift, the target database, does not allow column names with periods (`.`) in them. These periods can conflict with schema and table qualifiers. To ensure seamless data integration, please make sure that the column names in your input files adhere to Redshift's naming rules. 

If your Scheduled Data Export generates column names in the `columnname.field` format, consider removing these columns to comply with Redshift's naming conventions before using the files with the integration code. This ensures smooth data processing and prevents any naming conflicts that may arise during data transfer and loading.

By following this guideline, you can avoid potential issues and make the integration process more efficient.


## Conclusion

After you've completed the steps above, the sample code should function automatically.
