import boto3
import json
import time
import logging
import os
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Boto3 clients
ssm = boto3.client('ssm')
ec2 = boto3.client('ec2')
dynamodb = boto3.resource('dynamodb')

# DynamoDB table
DDB_TABLE_NAME = os.environ['TABLE_NAME']
table = dynamodb.Table(DDB_TABLE_NAME)

# PowerShell patch script
POWERSHELL_PATCH_SCRIPT = """
$kb = '{kb}'
Write-Host "Installing patch: $kb"
Install-WindowsUpdate -KBArticleID $kb -AcceptAll -AutoReboot

# Check if reboot required
$pendingReboot = (Get-ItemProperty "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Component Based Servicing\\RebootPending" -ErrorAction SilentlyContinue) -ne $null

# Output structured JSON
$result = @{
    KB = $kb
    RebootRequired = $pendingReboot
}
$result | ConvertTo-Json
"""

def lambda_handler(event, context):
    logger.info("Started patching process with event: %s", json.dumps(event))
    
    os_versions = event.get('os_versions')
    if not os_versions:
        logger.warning("No os_versions provided.")
        return {"status": "No os_versions provided"}

    results = []

    for os_name_raw in os_versions:
        os_name = f"OS#{os_name_raw}" if not os_name_raw.startswith("OS#") else os_name_raw

        # Step 1: Fetch KBs from DynamoDB for OS
        kb_list = get_kbs_from_dynamodb(os_name)
        kb_list = list(set(kb_list))

        if not kb_list:
            logger.warning(f"No matching KBs found in DynamoDB for {os_name}.")
            continue

        # Step 2: Find matching EC2 instances
        instances = get_target_instances(os_name)
        
        if not instances:
            logger.warning(f"No matching EC2 instances found for {os_name}.")
            continue

        # Step 3: Send patch command
        for instance_id in instances:
            for kb in kb_list:
                logger.info(f"Sending patch command for {kb} to instance {instance_id}")
                command = POWERSHELL_PATCH_SCRIPT.format(kb=kb)
                result = send_patch_command(instance_id, command)
                result['OS'] = os_name
                result['KB'] = kb
                results.append(result)

    return {
        "status": "Patch commands sent",
        "results": results
    }

def get_kbs_from_dynamodb(os_name):
    kb_list = []
    try:
        response = table.query(
            KeyConditionExpression=Key('PK').eq(os_name)
        )
        items = response.get('Items', [])
        for item in items:
            kb = item.get('kb')
            if kb:
                kb_list.append(kb)
                logger.info(f"Found KB {kb} for {os_name}")
    except ClientError as e:
        logger.error(f"DynamoDB query error for {os_name}: {e}")
    return kb_list

def get_target_instances(os_name):
    try:
        os_name_clean = os_name.replace("OS#", "").strip()  # Remove prefix and trim spaces

        response = ec2.describe_instances(
            Filters=[
                {'Name': 'instance-state-name', 'Values': ['running']}
            ]
        )
        instance_ids = []
        for res in response['Reservations']:
            for inst in res['Instances']:
                os_tag = next((tag['Value'] for tag in inst.get('Tags', []) if tag['Key'] == 'OS'), None)
                logger.info(f"Instance {inst['InstanceId']} OS tag: '{os_tag}' | comparing with '{os_name_clean}'")
                if os_tag == os_name_clean:
                    instance_ids.append(inst['InstanceId'])
        logger.info(f"Found EC2 instances: {instance_ids}")
        return instance_ids
    except ClientError as e:
        logger.error(f"EC2 describe_instances error: {e}")
        return []

def send_patch_command(instance_id, script):
    try:
        response = ssm.send_command(
            InstanceIds=[instance_id],
            DocumentName='AWS-RunPowerShellScript',
            Parameters={'commands': [script]},
            TimeoutSeconds=600
        )
        command_id = response['Command']['CommandId']
        logger.info(f"Command {command_id} sent to {instance_id}")

        # Wait briefly before checking result (or use Wait + Poll pattern)
        time.sleep(5)

        invocation = ssm.get_command_invocation(
            CommandId=command_id,
            InstanceId=instance_id
        )
        output = invocation.get('StandardOutputContent', '').strip()

        # Try parse JSON output
        reboot_required = None
        kb_installed = None
        try:
            parsed = json.loads(output)
            reboot_required = parsed.get('RebootRequired')
            kb_installed = parsed.get('KB')
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON output: {output}")

        return {
            "InstanceId": instance_id,
            "CommandId": command_id,
            "Status": invocation.get('Status'),
            "KB": kb_installed,
            "RebootRequired": reboot_required,
            "Output": output[:500]  # truncate for logging
        }

    except ClientError as e:
        logger.error(f"SSM send_command error for {instance_id}: {e}")
        return {
            "InstanceId": instance_id,
            "Error": str(e)
        }

