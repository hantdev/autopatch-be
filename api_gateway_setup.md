# API Gateway Setup Guide

## Bước 1: Tạo API Gateway

### 1.1 Tạo REST API
1. Vào AWS Console → API Gateway
2. Click "Create API"
3. Chọn "REST API" → "Build"
4. Đặt tên: `vpbank-api`
5. Description: `VPBank CVE Management API`
6. Click "Create API"

### 1.2 Tạo Resources và Methods

#### Resource: `/cve`
- Method: `GET` - Lấy danh sách CVE
- Method: `POST` - Tạo CVE mới

#### Resource: `/cve/{id}`
- Method: `GET` - Lấy chi tiết CVE
- Method: `PUT` - Cập nhật CVE
- Method: `DELETE` - Xóa CVE

#### Resource: `/scan`
- Method: `POST` - Scan servers và lấy OS info

#### Resource: `/update-cve`
- Method: `POST` - Update CVE data từ MSRC

## Bước 2: Tạo Lambda Functions

### 2.1 Lambda Function: `fetch-os-info`
```bash
# Tạo function
aws lambda create-function \
  --function-name fetch-os-info \
  --runtime python3.9 \
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/lambda-execution-role \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://vpbank-be/lambda/fetch_os_info/lambda_function.zip
```

### 2.2 Lambda Function: `update-cve-data`
```bash
# Tạo function
aws lambda create-function \
  --function-name update-cve-data \
  --runtime python3.9 \
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/lambda-execution-role \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://vpbank-be/lambda/update_cve_data/lambda_function.zip
```

### 2.3 Lambda Function: `update-full-cve-data`
```bash
# Tạo function
aws lambda create-function \
  --function-name update-full-cve-data \
  --runtime python3.9 \
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/lambda-execution-role \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://vpbank-be/lambda/update_full_cve_data/update_full_cve_data_v4.zip
```

## Bước 3: Kết nối Lambda với API Gateway

### 3.1 Tạo Integration
1. Chọn Resource `/scan`
2. Click "Actions" → "Create Method"
3. Chọn `POST`
4. Integration type: "Lambda Function"
5. Lambda Function: `fetch-os-info`
6. Click "Save"

### 3.2 Tạo Integration cho `/update-cve`
1. Chọn Resource `/update-cve`
2. Click "Actions" → "Create Method"
3. Chọn `POST`
4. Integration type: "Lambda Function"
5. Lambda Function: `update-cve-data`
6. Click "Save"

## Bước 4: Cấu hình CORS

### 4.1 Enable CORS cho tất cả resources
1. Chọn Resource
2. Click "Actions" → "Enable CORS"
3. Access-Control-Allow-Origin: `*`
4. Access-Control-Allow-Headers: `Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token`
5. Access-Control-Allow-Methods: `GET,POST,PUT,DELETE,OPTIONS`
6. Click "Enable CORS and replace existing CORS headers"

## Bước 5: Deploy API

### 5.1 Tạo Stage
1. Click "Actions" → "Deploy API"
2. Deployment stage: `prod`
3. Stage description: `Production`
4. Click "Deploy"

### 5.2 Lấy Invoke URL
- Invoke URL sẽ có dạng: `https://abc123.execute-api.us-east-1.amazonaws.com/prod`

## Bước 6: Cập nhật Frontend Configuration 