import boto3
import json
from botocore.exceptions import ClientError

ssm = boto3.client('ssm')

def lambda_handler(event, context):
    command_id = event.get('CommandId')
    instance_id = event.get('InstanceId')

    if not command_id or not instance_id:
        raise ValueError("Missing CommandId or InstanceId in input event")

    try:
        response = ssm.get_command_invocation(
            CommandId=command_id,
            InstanceId=instance_id
        )
        status = response.get('Status')
        output = response.get('StandardOutputContent', '').strip()

        return {
            'CommandId': command_id,
            'InstanceId': instance_id,
            'Status': status,
            'Output': output[:500]  # Truncate for logging/storage
        }

    except ClientError as e:
        print(f"Error getting command invocation: {e}")
        return {
            'CommandId': command_id,
            'InstanceId': instance_id,
            'Status': 'Error',
            'Error': str(e)
        }
