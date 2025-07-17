## ☁️ API Gateway Configuration

This project uses AWS API Gateway to expose a set of RESTful endpoints that trigger AWS Lambda functions for Windows patch management and CVE processing.

### 🌐 Base URL
https://xioac2avy5.execute-api.us-east-1.amazonaws.com/prod


### 📍 Endpoints Overview

| Endpoint                 | Method | Description                                     | Lambda Function         |
| ------------------------ | ------ | ----------------------------------------------- | ----------------------- |
| `/fetch-os-info`         | POST   | Retrieve the OS name from EC2 instance tags     | `fetch_os_info`         |
| `/parse-cve`             | POST   | Parse installed/available KBs from SSM result   | `parse_cve`             |
| `/start-patch`           | POST   | Trigger Step Function to patch all required KBs | `start_patch`           |
| `/get-patch-status`      | POST   | Get patch status summary from DynamoDB          | `get_patch_status`      |
| `/update-cve`            | POST   | Fetch CVEs from MSRC API and update DynamoDB    | `update_full_cve_data`  |
| `/reboot-server`         | POST   | Reboot target EC2 instances                     | `reboot_EC2`            |
| `/start-patch-single-kb` | POST   | Patch a specific KB on a single EC2 instance    | `start_patch_single_KB` |

> All endpoints accept JSON payloads and return standard HTTP JSON responses.

### 🧠 Integration

Each endpoint is integrated with a corresponding Lambda function. These functions handle patch analysis, execution, and reporting.

### 🚀 Deployment Note

The API Gateway was deployed via AWS Console or automation tools. You can update `BASE_URL` in the frontend via:

```js
export const API_CONFIG = {
  BASE_URL: 'https://xioac2avy5.execute-api.us-east-1.amazonaws.com/prod',
  ...
};
