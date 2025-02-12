import os
import sqlite3
import json  # Added for proper JSON handling
from flask import Flask, jsonify, request, render_template
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

app = Flask(__name__)
API_KEY = os.getenv("OPENWEATHER_API_KEY")
BASE_URL = "http://api.openweathermap.org/data/2.5/weather"

def init_db():
    """Initialize SQLite database with proper JSON storage"""
    conn = sqlite3.connect('weather.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS weather_cache
                 (city TEXT PRIMARY KEY, data TEXT)''')
    conn.commit()
    conn.close()

init_db()

def get_cached_weather(city):
    """Retrieve cached weather data as JSON"""
    conn = sqlite3.connect('weather.db')
    c = conn.cursor()
    c.execute("SELECT data FROM weather_cache WHERE city=?", (city,))
    data = c.fetchone()
    conn.close()
    return json.loads(data[0]) if data else None

def cache_weather(city, data):
    """Store weather data as JSON"""
    conn = sqlite3.connect('weather.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO weather_cache VALUES (?, ?)",
              (city, json.dumps(data)))  # Proper JSON serialization
    conn.commit()
    conn.close()

@app.route('/weather', methods=['GET'])
def get_weather():
    """Weather API endpoint with enhanced error handling"""
    city = request.args.get('city')
    
    if not city:
        return jsonify({"error": "City parameter is required"}), 400
    
    # Try cache first
    cached_data = get_cached_weather(city)
    if cached_data:
        return jsonify({"source": "cache", "data": cached_data})
    
    # Fetch from OpenWeather API
    try:
        params = {
            'q': city,
            'appid': API_KEY,
            'units': 'metric'
        }
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        # Validate API response structure
        if not all(key in data for key in ('name', 'main', 'weather')):
            raise ValueError("Invalid API response format")
        
        # Cache valid response
        cache_weather(city, data)
        return jsonify({"source": "API", "data": data})
    
    except requests.exceptions.HTTPError as e:
        return jsonify({"error": f"City not found: {city}"}), 404
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid API response"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def home():
    """Serve the frontend interface"""
    return render_template('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
app = Flask(__name__)
