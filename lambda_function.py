import json
import urllib.request
import boto3
import time

# DynamoDB
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('ecoweather-weather-data')

# SNS (added safely)
sns = boto3.client('sns')

# Your OpenWeather API Key
API_KEY = "9fc7992d087451bf6829760c513b5453"

def fetch_weather(city):
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
    with urllib.request.urlopen(url) as response:
        return json.loads(response.read())

def lambda_handler(event, context):

    print("Lambda started")  # CloudWatch log

    # Default city
    city = "London"

    # Get city from API request
    if event.get("queryStringParameters") and event["queryStringParameters"]:
        city = event["queryStringParameters"].get("city", "London")

    try:
        data = fetch_weather(city)

        print(f"Weather fetched for {city}")  # CloudWatch log

        # Handle invalid city or API issues
        if str(data.get("cod")) != "200":
            return {
                "statusCode": 200,
                "headers": {"Access-Control-Allow-Origin": "*"},
                "body": json.dumps({
                    "error": data.get("message", "City not found")
                })
            }

        temperature = data["main"]["temp"]

        # Save to DynamoDB
        table.put_item(Item={
            "city": city,
            "timestamp": str(int(time.time())),
            "temperature": str(temperature)
        })

        print("Saved to DynamoDB")  # CloudWatch log

        # SNS notification (SAFE)
        try:
            sns.publish(
                TopicArn='arn:aws:sns:us-east-1:891377078916:ecoweather-topic',
                Message=f"Weather for {city}: {temperature}°C"
            )
            print("SNS sent")
        except Exception as e:
            print("SNS failed:", str(e))

        # Return response to frontend
        return {
            "statusCode": 200,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({
                "city": data["name"],
                "temperature": temperature
            })
        }

    except Exception as e:
        print("Error:", str(e))  # CloudWatch log
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({
                "error": str(e)
            })
        }
