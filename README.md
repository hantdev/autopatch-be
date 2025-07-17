# ⚙️ AutoPatch Backend

This repository contains the complete backend setup for the **AutoPatch** system. It automates patching for Windows EC2 instances using AWS services such as Lambda, Step Functions, Systems Manager (SSM), DynamoDB, and API Gateway.

---

## 📁 Folder Structure

autopatch-backend/
├── api_gateway/ # API Gateway configurations
│ └── api_gateway_setup.md # Setup guide for API Gateway
│
├── dynamodb/ # DynamoDB data files
│ ├── patchprogress.json # Sample patch progress record
│ └── vpbank-cve-data.json # Sample CVE data specific to VPBank
│
├── lambda/ # AWS Lambda functions (Python)
│ ├── fetch_os_info/ # Get OS info from EC2 instance
│ ├── get_patch_status/ # Query patch status from DynamoDB
│ ├── get_target_instances_and_kbs/ # Fetch list of instances + missing KBs
│ ├── parse_cve/ # Process CVE to KB mapping
│ ├── poll_command_status/ # Poll status from SSM RunCommand
│ ├── poll_get_KB_command_result/ # Poll results of each KB command
│ ├── reboot_EC2/ # Trigger reboot for EC2 instance
│ ├── run_patch/ # Execute patch command on target EC2
│ ├── start_patch/ # Start full patching Step Function
│ ├── start_patch_single_KB/ # Retry single KB via Step Function
│ ├── summarize_SNS/ # Summarize and notify via SNS
│ ├── update_full_cve_data/ # Query Microsoft API and update DB
│ └── update_patch_status/ # Save final patch status to DB
│
├── ssm_ec2/
│ └── ec2_test_server_setup.md # EC2 config & SSM pre-requirements
│
├── stepfunctions/ # AWS Step Functions workflows
│ ├── Runpatch-Sequential-KB-install-per-server.json # Full patching process workflow
│ └── RetrySingleKBPatch.json # Retry a single KB patch workflow

## ✅ Key AWS Services Used
Lambda: Core logic and orchestration
Step Functions: Patch workflows
DynamoDB: Patch data store
SSM (Inventory, RunCommand): Get OS info, Execute PowerShell on EC2
SNS: Notify patch results
CloudWatch: Logs & monitoring
API Gateway: Public-facing REST API
Amplify: Hosts frontend app and connects to backend APIs