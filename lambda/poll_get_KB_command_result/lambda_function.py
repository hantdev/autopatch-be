import boto3
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ssm = boto3.client('ssm')

def lambda_handler(event, context):
    results = event.get("results", [])
    final_results = []

    for item in results:
        instance_id = item.get("instance_id")
        command_id = item.get("command_id")
        kb_list = item.get("kb_list", [])

        if not instance_id or not command_id:
            final_results.append({
                "InstanceId": instance_id,
                "Error": "Missing instance_id or command_id"
            })
            continue

        try:
            # Gọi kết quả từ SSM
            invocation = ssm.get_command_invocation(
                CommandId=command_id,
                InstanceId=instance_id,
                PluginName='aws:runPowerShellScript'
            )

            output_lines = invocation.get("StandardOutputContent", "").splitlines()

            if len(output_lines) < 2:
                raise Exception("Unexpected command output format")

            installed_kbs = [kb.strip() for kb in output_lines[0].split(',') if kb.strip()]
            available_kbs = [kb.strip() for kb in output_lines[1].split(',') if kb.strip()]

            logger.info(f"[{instance_id}] Installed KBs: {installed_kbs}")
            logger.info(f"[{instance_id}] Available KBs: {available_kbs}")

            kb_list = [kb if kb.startswith("KB") else f"KB{kb}" for kb in kb_list]

            result_available = []
            result_skipped = []
            result_installed = []

            for kb in kb_list:
                if kb in installed_kbs:
                    result_installed.append(kb.replace("KB", ""))
                elif kb in available_kbs:
                    result_available.append(kb.replace("KB", ""))
                else:
                    result_skipped.append({
                        "KB": kb.replace("KB", ""),
                        "status": "Not Available"
                    })

            final_results.append({
                "InstanceId": instance_id,
                "installedKBs": result_installed,
                "availableKBs": result_available,
                "skippedKBs": result_skipped
            })

        except ClientError as e:
            logger.error(f"[{instance_id}] ClientError: {str(e)}")
            final_results.append({
                "InstanceId": instance_id,
                "Error": str(e)
            })
        except Exception as e:
            logger.error(f"[{instance_id}] Error: {str(e)}")
            final_results.append({
                "InstanceId": instance_id,
                "Error": str(e)
            })

    return {
        "status": "done",
        "results": final_results
    }