# EcoWeather Serverless Application

## Overview
This project is a serverless weather application built using AWS services. It retrieves real-time weather data, processes it using AWS Lambda, and stores it in DynamoDB.

## Architecture
The system uses the following AWS services:

- API Gateway: Handles incoming HTTP requests
- Lambda: Processes weather data
- DynamoDB: Stores weather records
- SNS: Sends notifications
- CloudWatch: Logs monitoring

## CI/CD Pipeline
CI/CD is implemented using GitHub Actions. Whenever code is pushed to the repository, the pipeline automatically:

- Validates the Lambda function
- Installs dependencies
- Simulates deployment

## Features
- Real-time weather data retrieval
- Serverless and scalable architecture
- Energy-efficient design
- Automated CI/CD pipeline

## Repository Structure
- lambda_function.py → Backend logic
- index.html → Frontend UI
- template.yaml → Infrastructure template
- architecture diagram → System design

## Author
Sreehari Sreekumar
