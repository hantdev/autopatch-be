# EC2 Windows Server Test Instance Setup

## Mục tiêu
Tạo EC2 Windows Server test để chạy AutoPatch pipeline.

## Các bước

1. **Tạo IAM Role**
   - Trusted entity: EC2
   - Attach policy: AmazonSSMManagedInstanceCore
   - Name: AutoPatch-EC2-SSM-Role

2. **Launch EC2 (2 instances)**
   - AMI: Windows Server 2019 Core Base/ Windows Server 2016 Core Base
   - Instance type: t3.micro
   - Network: Default VPC
   - IAM Role: AutoPatch-EC2-SSM-Role
   - Key pair: tạo một key 
   - Security group: không mở port, vì đã có SSM

3. **Verify SSM Agent**
   - Systems Manager → Managed Nodes → Check instance status is 'Managed'

## Kết quả
✔️ EC2 Windows test server xuất hiện trong Managed Nodes  
✔️ SSM Agent hoạt động → sẵn sàng RunCommand