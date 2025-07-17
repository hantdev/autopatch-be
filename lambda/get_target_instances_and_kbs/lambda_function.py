import boto3
import os
import logging
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
smm = boto3.client('ssm')
ec2 = boto3.client('ec2')

DDB_TABLE_NAME = os.environ.get("TABLE_NAME")

def lambda_handler(event, context):
    instance_ids = event.get("instance_ids", [])
    if not instance_ids:
        return {"status": "error", "message": "Missing instance_ids"}

    results = []

    for instance_id in instance_ids:
        try:
            os_product = get_os_from_instance(instance_id)
            if not os_product:
                results.append({
                    "instance_id": instance_id,
                    "error": f"OS not found in tags for {instance_id}"
                })
                continue

            table = dynamodb.Table(DDB_TABLE_NAME)
            response = table.query(
                KeyConditionExpression=Key('PK').eq(f"OS#{os_product}")
            )
            kb_list = list(set([item["kbArticle"] for item in response.get("Items", [])]))

            logger.info(f"[{instance_id}] Found {len(kb_list)} KBs from DynamoDB")

            # PowerShell script chuẩn hóa output
            script = """
if (-not (Get-Module -ListAvailable -Name PSWindowsUpdate)) {
    Install-PackageProvider -Name NuGet -Force -Scope CurrentUser
    Set-PSRepository -Name 'PSGallery' -InstallationPolicy Trusted
    Install-Module -Name PSWindowsUpdate -Force -AllowClobber -Scope CurrentUser
}
Import-Module PSWindowsUpdate

$installed = Get-HotFix | Select-Object -ExpandProperty HotFixID
$available = Get-WindowsUpdate -MicrosoftUpdate -AcceptAll -IgnoreReboot | ForEach-Object {
    $_.KBArticleIDs | ForEach-Object { 'KB' + $_ }
}

Write-Output "INSTALLED_KBS=$($installed -join ',')"
Write-Output "AVAILABLE_KBS=$($available -join ',')"
"""

            ssm_response = smm.send_command(
                InstanceIds=[instance_id],
                DocumentName="AWS-RunPowerShellScript",
                Parameters={'commands': [script]},
                TimeoutSeconds=180
            )

            command_id = ssm_response["Command"]["CommandId"]

            results.append({
                "status": "sent",
                "instance_id": instance_id,
                "command_id": command_id,
                "kb_list": kb_list
            })

        except Exception as e:
            logger.error(f"[{instance_id}] Error: {e}")
            results.append({
                "instance_id": instance_id,
                "error": str(e)
            })

    return {
        "status": "done",
        "results": results
    }

def get_os_from_instance(instance_id):
    try:
        response = ec2.describe_instances(InstanceIds=[instance_id])
        for res in response['Reservations']:
            for inst in res['Instances']:
                os_tag = next((tag['Value'] for tag in inst.get('Tags', []) if tag['Key'] == 'OS'), None)
                return os_tag
        return None
    except ClientError as e:
        logger.error(f"EC2 describe_instances error: {e}")
        return None
