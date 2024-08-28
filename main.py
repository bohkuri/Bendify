from flask import Flask, redirect, request, jsonify, session, render_template
import requests
import urllib.parse
from datetime import datetime, timedelta
import math

from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('app_secret_key')

CLIENT_ID = os.getenv('CL_ID')
CLIENT_SECRET = os.getenv('CL_SC')
REDIRECT_URI = 'http://localhost:5000/callback'

AUTH_URL = 'https://accounts.spotify.com/authorize'
TOKEN_URL = 'https://accounts.spotify.com/api/token'
API_BASE_URL = 'https://api.spotify.com/v1/'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    scope = 'user-read-private user-read-email user-top-read'

    params = {
        'client_id': CLIENT_ID,
        'response_type': 'code',
        'scope': scope,
        'redirect_uri': REDIRECT_URI,
        'show_dialog': True             # set to false later. set to True now for testing purposes (user logs in everytime for testing)
    }


    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"

    return redirect(auth_url)


@app.route('/callback')
def callback():
    if 'error' in request.args:
        return jsonify({"error": request.args['error']})
    
    if 'code' in request.args:
        req_body = {
            'code': request.args['code'],
            'grant_type': 'authorization_code',
            'redirect_uri': REDIRECT_URI,
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET
        }

        response = requests.post(TOKEN_URL, data=req_body)
        token_info = response.json()

        session['access_token'] = token_info['access_token']
        session['refresh_token'] = token_info['refresh_token']
        session['expires_at'] = datetime.now().timestamp() + token_info['expires_in']

        return redirect('/userArtists')
    
@app.route('/userArtists')
def get_artists():
    if 'access_token' not in session:
        return redirect('/login')
    
    if datetime.now().timestamp() > session['expires_at']:
        return redirect('/refresh_token')

    headers = {
        'Authorization': f"Bearer {session['access_token']}"
    }

    response = requests.get(API_BASE_URL + 'me/top/artists?offset=0&limit=10&time_range=short_term', headers=headers)
    data = response.json()
    artists_names = [artist['name'] for artist in data['items']]

    response = requests.get(API_BASE_URL + 'me/top/tracks?offset=0&limit=30&time_range=short_term', headers=headers)
    top_tracks = response.json()
    track_ids = [track['id'] for track in top_tracks['items']]

    total_dance = 0.0
    total_acoustic = 0.0
    total_instrumental = 0.0
    total_energy = 0.0


    idString = ','.join(track_ids)
    response = requests.get(f"{API_BASE_URL}audio-features?ids={idString}", headers=headers)
    total_features = response.json()

    for feature in total_features['audio_features']:
        if feature:  # Check if the feature is not None
            total_dance += feature.get('danceability', 0)
            total_acoustic += feature.get('acousticness', 0)
            total_instrumental += feature.get('instrumentalness', 0)
            total_energy += feature.get('energy', 0)
        

    if total_instrumental > 2.6 and total_acoustic > 8.0:
        element = "earth"
        style = "Earthbender"
    elif (total_instrumental > 5.0) or (total_energy > 13 and total_acoustic > 9.0):
        element = "air"
        style = "Airbender"
    elif total_acoustic > 10 and total_dance > 10:
        element = "water"
        style = "Waterbender"
    elif total_energy > 13 and total_dance > 13:
        element = "fire"
        style = "Firebender"
    else:
        element = "earth"
        style = "Earthbender"

    total_acoustic = math.trunc(total_acoustic)
    total_dance = math.trunc(total_dance)
    total_energy = math.trunc(total_energy)
    total_instrumental = math.trunc(total_instrumental)

    response = requests.get(API_BASE_URL + 'me', headers=headers)
    data = response.json()
    user_name = data["display_name"]
    
    

    return render_template("bending.html", dance=total_dance, instrumental=total_instrumental, acoustic=total_acoustic, energy=total_energy, element=element, artists=artists_names, user_name=user_name, style=style)


@app.route('/refresh_token')
def refresh_token():
    if 'refresh_token' not in session:
        return redirect('/login')
    
    if datetime.now().timestamp() > session['expires_at']:
        req_body = {
            'grant_type': 'refresh_token',
            'refresh_token': session['refresh_token'],
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET
        }

        response = requests.post(TOKEN_URL, data=req_body)
        new_token_info = response.json()

        session['access_token'] = new_token_info['access_token']
        session['expires_at'] = datetime.now().timestamp() + new_token_info['expires_in']

        return redirect('/userArtists')
        

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)