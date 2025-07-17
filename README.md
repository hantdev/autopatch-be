# ⚙️ AutoPatch Backend

This repository contains the complete backend setup for the **AutoPatch** system — an automated patching solution for Windows EC2 instances. It leverages various AWS services such as **Lambda**, **Step Functions**, **SSM**, **DynamoDB**, and **API Gateway** to orchestrate, monitor, and execute patching workflows efficiently.

---

## 📁 Folder Structure

```
autopatch-backend/
├── api_gateway/                     # API Gateway configurations
│   └── api_gateway_setup.md         # Setup guide for API Gateway
│
├── dynamodb/                        # Sample data for DynamoDB
│   ├── patchprogress.json           # Example patch progress record
│   └── vpbank-cve-data.json         # CVE-to-KB mapping data specific to VPBank
│
├── lambda/                          # AWS Lambda functions (Python)
│   ├── fetch_os_info/              # Get OS version from SSM
│   ├── get_patch_status/           # Query patch status from DB
│   ├── get_target_instances_and_kbs/ # Retrieve target EC2s and missing KBs
│   ├── parse_cve/                  # Map CVEs to KBs
│   ├── poll_command_status/        # Poll patch command execution status
│   ├── poll_get_KB_command_result/ # Poll results of each KB command
│   ├── reboot_EC2/                 # Trigger EC2 reboot
│   ├── run_patch/                  # Run patch via SSM RunCommand
│   ├── start_patch/                # Start full patch workflow (Step Function)
│   ├── start_patch_single_KB/      # Retry single KB patch via Step Function
│   ├── summarize_SNS/              # Send patch summary via SNS
│   ├── update_full_cve_data/       # Call Microsoft API, update CVE→KB mapping in DB
│   └── update_patch_status/        # Update patch result to DB
│
├── ssm_ec2/
│   └── ec2_test_server_setup.md     # EC2 setup & SSM requirements
│
├── stepfunctions/                   # Step Function workflows
│   ├── Runpatch-Sequential-KB-install-per-server.json   # Full patching process
│   └── RetrySingleKBPatch.json                         # Retry single KB patch
```

---

## ✅ Key AWS Services Used

- **Lambda**: Core logic and backend processing  
- **Step Functions**: Orchestration of patching workflows  
- **DynamoDB**: Storage of patching status and CVE-KB mappings  
- **SSM (Inventory & RunCommand)**: Collect OS info and execute patch scripts  
- **SNS**: Notify patch summary (e.g. via email)  
- **CloudWatch**: Logging and monitoring for debugging  
- **API Gateway**: Expose backend endpoints to the frontend  
- **Amplify**: Hosts the frontend and connects it with backend APIs  
