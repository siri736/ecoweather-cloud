import json
import boto3
import urllib.request
import time

secrets_client = boto3.client('secretsmanager')
dynamodb = boto3.resource('dynamodb')

def get_api_key():
    secret = secrets_client.get_secret_value(SecretId='ecoweather/weather-api')
    return json.loads(secret['SecretString'])['API_KEY']

def fetch_weather(city, api_key):
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    with urllib.request.urlopen(url) as response:
        return json.loads(response.read())

def lambda_handler(event, context):
    city = "London"
    if event.get("queryStringParameters"):
        city = event["queryStringParameters"].get("city", "London")

    api_key = get_api_key()
    data = fetch_weather(city, api_key)

    table = dynamodb.Table('ecoweather-weather-data')

    item = {
        'city': city,
        'timestamp': int(time.time()),
        'temperature': data['main']['temp'],
        'condition': data['weather'][0]['description']
    }

    table.put_item(Item=item)

    return {
        'statusCode': 200,
        'headers': {"Access-Control-Allow-Origin": "*"},
        'body': json.dumps(item)
    }