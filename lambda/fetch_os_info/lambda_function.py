import boto3
import json
import logging
from datetime import datetime

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Create clients
ssm_client = boto3.client('ssm')
ec2_client = boto3.client('ec2')

def lambda_handler(event, context):
    try:
        # Step 1. Describe instance information from SSM
        ssm_response = ssm_client.describe_instance_information()
        instance_info_list = ssm_response.get('InstanceInformationList', [])
        results = []

        # Step 2. For each instance, call EC2 DescribeInstances to get AMI info
        for instance in instance_info_list:
            instance_id = instance.get('InstanceId')
            platform_name = instance.get('PlatformName')
            platform_version = instance.get('PlatformVersion')
            ip_address = instance.get('IPAddress')

            # Describe EC2 instance to get ImageId
            ec2_response = ec2_client.describe_instances(InstanceIds=[instance_id])
            reservations = ec2_response.get('Reservations', [])
            if reservations:
                ec2_instance = reservations[0]['Instances'][0]
                image_id = ec2_instance.get('ImageId')
                # Get AMI name from DescribeImages
                ami_response = ec2_client.describe_images(ImageIds=[image_id])
                ami_name = ami_response['Images'][0].get('Name') if ami_response['Images'] else "Unknown"
            else:
                image_id = "Unknown"
                ami_name = "Unknown"

            # Determine edition normalization
            if '2016' in ami_name:
                os_version = 'Windows Server 2016'
            elif '2019' in ami_name:
                os_version = 'Windows Server 2019'
            elif '2022' in ami_name:
                os_version = 'Windows Server 2022'
            else:
                os_version = platform_name  # fallback

            if 'Core' in ami_name:
                normalized = f"{os_version} (Server Core installation)"
            else:
                normalized = os_version

            info = {
                'InstanceId': instance_id,
                'PlatformName': platform_name,
                'PlatformVersion': platform_version,
                'IPAddress': ip_address,
                'ImageId': image_id,
                'AmiName': ami_name,
                'NormalizedOS': normalized,
                'FetchedAt': datetime.utcnow().isoformat() + 'Z'
            }

            logger.info(json.dumps(info))
            results.append(info)

        return {
            'statusCode': 200,
            'body': json.dumps(results)
        }

    except Exception as e:
        logger.error("Error fetching OS info: %s", str(e))
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
