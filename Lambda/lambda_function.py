import json
import time
import urllib.parse
import urllib.request
import urllib.error
from decimal import Decimal
from datetime import datetime, timezone

import boto3


# AWS clients/resources
secrets_client = boto3.client("secretsmanager")
dynamodb = boto3.resource("dynamodb")

# Configuration
TABLE_NAME = "ecoweather-weather-data"
SECRET_NAME = "ecoweather/weather-api"


def build_response(status_code, body):
    """
    Returns a standard API Gateway response with CORS enabled.
    """
    return {
        "statusCode": status_code,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Methods": "GET,OPTIONS",
            "Content-Type": "application/json"
        },
        "body": json.dumps(body, default=str)
    }


def get_api_key():
    """
    Reads OpenWeather API key from AWS Secrets Manager.
    Secret name: ecoweather/weather-api
    Required key inside secret: API_KEY
    """
    print("Reading OpenWeather API key from Secrets Manager")

    secret = secrets_client.get_secret_value(SecretId=SECRET_NAME)
    secret_value = json.loads(secret["SecretString"])

    if "API_KEY" not in secret_value:
        raise KeyError("API_KEY not found inside secret ecoweather/weather-api")

    print("OpenWeather API key loaded successfully")
    return secret_value["API_KEY"]


def fetch_weather(city, api_key):
    """
    Calls OpenWeather current weather API.
    """
    city_encoded = urllib.parse.quote(city)

    url = (
        "https://api.openweathermap.org/data/2.5/weather"
        f"?q={city_encoded}&appid={api_key}&units=metric"
    )

    print(f"Calling OpenWeather API for city: {city}")

    try:
        with urllib.request.urlopen(url, timeout=10) as api_response:
            data = json.loads(api_response.read())
            print("OpenWeather API response received successfully")
            return data

    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8")

        try:
            error_json = json.loads(error_body)
            message = error_json.get("message", "Weather API error")
        except Exception:
            message = "Weather API request failed"

        print(f"OpenWeather API HTTP error: {message}")

        return {
            "error": message,
            "status": error.code
        }

    except urllib.error.URLError as error:
        print(f"Network error calling OpenWeather API: {str(error)}")
        return {
            "error": "Could not connect to OpenWeather API",
            "status": 503
        }


def get_city_from_event(event):
    """
    Extracts city from API Gateway query string.
    Supports API Gateway HTTP API payload.
    """
    city = "London"

    query_params = event.get("queryStringParameters")

    if query_params and query_params.get("city"):
        city = query_params.get("city").strip()

    if not city:
        city = "London"

    print(f"Requested city: {city}")
    return city


def save_weather_to_dynamodb(weather_item):
    """
    Saves weather result to DynamoDB.
    """
    print("Saving weather data to DynamoDB")

    table = dynamodb.Table(TABLE_NAME)
    table.put_item(Item=weather_item)

    print("Weather data saved successfully to DynamoDB")


def lambda_handler(event, context):
    """
    Main Lambda handler.
    Flow:
    1. Read city from API request
    2. Get OpenWeather API key from Secrets Manager
    3. Fetch weather
    4. Store result in DynamoDB
    5. Return JSON response to frontend
    """
    print("Lambda execution started")

    try:
        city = get_city_from_event(event)
        api_key = get_api_key()
        data = fetch_weather(city, api_key)

        if data.get("error"):
            print(f"Weather request failed: {data.get('error')}")
            return build_response(400, {
                "success": False,
                "error": data.get("error"),
                "city": city
            })

        timestamp = str(int(time.time()))
        readable_time = datetime.now(timezone.utc).isoformat()

        temperature = Decimal(str(data["main"]["temp"]))
        feels_like = Decimal(str(data["main"].get("feels_like", data["main"]["temp"])))
        humidity = int(data["main"].get("humidity", 0))
        pressure = int(data["main"].get("pressure", 0))
        wind_speed = Decimal(str(data.get("wind", {}).get("speed", 0)))
        visibility_m = int(data.get("visibility", 0))
        visibility_km = Decimal(str(round(visibility_m / 1000, 1))) if visibility_m else Decimal("0")

        condition = data["weather"][0].get("description", "No condition available")
        icon = data["weather"][0].get("icon", "")
        country = data.get("sys", {}).get("country", "")

        weather_item = {
            "city": data.get("name", city),
            "timestamp": timestamp,
            "datetime_utc": readable_time,
            "temperature": temperature,
            "feels_like": feels_like,
            "humidity": humidity,
            "pressure": pressure,
            "wind_speed": wind_speed,
            "visibility_km": visibility_km,
            "condition": condition,
            "icon": icon,
            "country": country
        }

        save_weather_to_dynamodb(weather_item)

        print("Lambda execution completed successfully")

        return build_response(200, {
            "success": True,
            "city": weather_item["city"],
            "country": weather_item["country"],
            "timestamp": weather_item["timestamp"],
            "datetime_utc": weather_item["datetime_utc"],
            "temperature": str(weather_item["temperature"]),
            "feels_like": str(weather_item["feels_like"]),
            "humidity": f"{weather_item['humidity']}%",
            "pressure": str(weather_item["pressure"]),
            "wind": str(weather_item["wind_speed"]),
            "visibility": f"{weather_item['visibility_km']}km",
            "condition": weather_item["condition"],
            "icon": weather_item["icon"]
        })

    except Exception as error:
        print(f"Lambda execution failed: {str(error)}")

        return build_response(500, {
            "success": False,
            "error": str(error)
        })