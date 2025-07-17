# EC2 Windows Server Test Instance Setup

## Mục tiêu
Tạo EC2 Windows Server test để chạy AutoPatch pipeline.

## Các bước

1. **Tạo IAM Role**
   - Trusted entity: EC2
   - Attach policy: AmazonSSMManagedInstanceCore
   - Name: AutoPatch-EC2-SSM-Role

2. **Launch EC2 (2 instances)**
   - Name tag: Windows Server 2019 / Windows Server 2022
   - OS tag: Windows Server 2019 / Windows Server 2022
   - AMI: Windows Server 2019 Base / Windows Server 2022 Base
   - Instance type: t3.micro
   - Network: Default VPC
   - IAM Role: AutoPatch-EC2-SSM-Role
   - Key pair: tạo một key 
   - Security group: không mở port, vì đã có SSM (trong giai đoạn dev có thể mở port RDP để kiểm tra script có hoạt động không)

3. **Verify SSM Agent**
   - Systems Manager → Managed Nodes → Check instance status is 'Managed'

## Kết quả
✔️ EC2 Windows test server xuất hiện trong Managed Nodes  
✔️ SSM Agent hoạt động → sẵn sàng RunCommand