import datetime
import requests 
import string
from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
from dotenv import load_dotenv 
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import mysql.connector
import bcrypt


load_dotenv()





OWM_ENDPOINT = "http://api.openweathermap.org/data/2.5/weather"
OWM_FORECAST_ENDPOINT = "http://api.openweathermap.org/data/2.5/forecast"
GEOCODING_API_ENDPOINT = "http://api.openweathermap.org/geo/1.0/direct"
api_key = "48bd621474806f24e7e0c13f309993f3"

app = Flask(__name__)

def get_db_connection(): 
    conn = mysql.connector.connect( 
    'host': 'localhost',
    'user': 'root',
    'password': 'Gae@2.0',
    'database': 'weather'
)
   

    return conn

app.secret_key = os.urandom(24)


@app.route("/", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        data = request.get_json()  # Get the JSON data from the request

        email = data.get('email')
        password = data.get('password').encode('utf-8')

        # Hash the password using bcrypt
        hashed_password = bcrypt.hashpw(password, bcrypt.gensalt())

        try:
            # Connect to the MySQL database
            conn = get_db_connection()
            cursor = conn.cursor()

            # Check if the user already exists
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
            if user:
                # Handle error, e.g., return a JSON response with an error message
                return jsonify({'success': False, 'error': 'User already exists'})

            # Insert the new user into the database
            cursor.execute("INSERT INTO users (email, password) VALUES (%s, %s)", (email, hashed_password))
            conn.commit()
            cursor.close()
            conn.close()

            return redirect(url_for('home'))  # Redirect to the home page
        except mysql.connector.Error as err:
            app.logger.error(f"Error connecting to database: {err}")
            return jsonify({'success': False, 'error': 'There was an error registering your account. Please try again later.'})
    return render_template("register.html")

# Display home page and get city name entered into search form
@app.route("/", methods=["GET", "POST"])

def home():
    if request.method == "POST":
        city = request.form.get("search")
        return redirect(url_for("get_weather", city=city))
    return render_template("index.html")


# Display weather forecast for specific city using data from OpenWeather API
@app.route("/<city>", methods=["GET", "POST"])
def get_weather(city):
    # Format city name and get current date to display on page
    city_name = string.capwords(city)
    today = datetime.datetime.now()
    current_date = today.strftime("%A, %B %d")

    # Get latitude and longitude for city
    location_params = {
        "q": city_name,
        "appid": api_key,
        "limit": 3,
    }

    location_response = requests.get(GEOCODING_API_ENDPOINT, params=location_params)
    location_data = location_response.json()

    # Prevent IndexError if user entered a city name with no coordinates by redirecting to error page
    if not location_data:
        return redirect(url_for("error"))
    else:
        lat = location_data[0]['lat']
        lon = location_data[0]['lon']

    # Get OpenWeather API data
    weather_params = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
        "units": "metric",
    }
    weather_response = requests.get(OWM_ENDPOINT, params=weather_params)
    weather_response.raise_for_status()
    weather_data = weather_response.json()

    # Get current weather data
    current_temp = round(weather_data['main']['temp'])
    current_weather = weather_data['weather'][0]['main']
    min_temp = round(weather_data['main']['temp_min'])
    max_temp = round(weather_data['main']['temp_max'])
    wind_speed = weather_data['wind']['speed']

    # Get five-day weather forecast data
    forecast_response = requests.get(OWM_FORECAST_ENDPOINT, params=weather_params)
    forecast_data = forecast_response.json()

    # Make lists of temperature and weather description data to show user
    five_day_temp_list = [round(item['main']['temp']) for item in forecast_data['list'] if '12:00:00' in item['dt_txt']]
    five_day_weather_list = [item['weather'][0]['main'] for item in forecast_data['list']
                             if '12:00:00' in item['dt_txt']]

    # Get next four weekdays to show user alongside weather data
    five_day_unformatted = [today, today + datetime.timedelta(days=1), today + datetime.timedelta(days=2),
                            today + datetime.timedelta(days=3), today + datetime.timedelta(days=4)]
    five_day_dates_list = [date.strftime("%a") for date in five_day_unformatted]

    return render_template("city.html", city_name=city_name, current_date=current_date, current_temp=current_temp,
                           current_weather=current_weather, min_temp=min_temp, max_temp=max_temp, wind_speed=wind_speed,
                           five_day_temp_list=five_day_temp_list, five_day_weather_list=five_day_weather_list,
                           five_day_dates_list=five_day_dates_list)


# Display error page for invalid input
@app.route("/error")
def error():
    return render_template("error.html")


if __name__ == "__main__":
    app.run(debug=True)