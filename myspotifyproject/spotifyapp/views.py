import random
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from django.shortcuts import render, redirect
from django.http import HttpResponse
from prettytable import PrettyTable
import pandas as pd
import plotly.express as px
from plotly.offline import plot
import requests
import datetime
import logging
import statistics
import time

logger = logging.getLogger(__name__)

# Set the timeout value (in seconds)
TIMEOUT = 5
MAX_RETRIES = 3

# Configure the Spotipy client to use a session with a timeout
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(max_retries=MAX_RETRIES)
session.mount('https://', adapter)
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id='YOUR CLIENT ID',
    client_secret='YOUR CLIENT SECRET',
    redirect_uri='http://localhost:8888/callback',
    scope='playlist-modify-private playlist-modify-public user-library-read user-top-read user-read-recently-played'
))



def extract_playlist_id(playlist_link):
    try:
        playlist_id = playlist_link.split('/')[-1].split('?')[0]
        return playlist_id
    except Exception as e:
        logger.error(f"Error extracting playlist ID: {e}")
        return None

def view_top_artists(request, time_range='short_term'):
    top_artists = sp.current_user_top_artists(limit=50, time_range=time_range)['items']
    recently_played_tracks = get_recently_played_tracks()

    artists = []
    for i, artist in enumerate(top_artists):
        artist_name = artist['name']
        artist_photo = artist['images'][0]['url'] if artist['images'] else ''
        popularity = artist['popularity']  # Fetch artist popularity from Spotify API
        artists.append((i + 1, artist_name, artist_photo, popularity))  # Include popularity in the tuple

    return render(request, 'spotifyapp/view_top_artists.html', {'artists': artists, 'time_range': time_range})

def view_top_genres(request, time_range='short_term'):
    top_artists = sp.current_user_top_artists(limit=50, time_range=time_range)['items']
    genres = {}
    for artist in top_artists:
        for genre in artist['genres']:
            if genre in genres:
                genres[genre] += 1
            else:
                genres[genre] = 1
    sorted_genres = sorted(genres.items(), key=lambda item: item[1], reverse=True)
    genre_list = [(i+1, genre, count) for i, (genre, count) in enumerate(sorted_genres)]
    return render(request, 'spotifyapp/view_top_genres.html', {'genres': genre_list, 'time_range': time_range})

def view_top_songs(request, time_range='short_term'):
    top_tracks = sp.current_user_top_tracks(limit=50, time_range=time_range)['items']
    recently_played_tracks = get_recently_played_tracks()

    songs = []
    for i, track in enumerate(top_tracks):
        time.sleep(0.5)
        track_name = track['name']
        artist_names = ', '.join([artist['name'] for artist in track['artists']])
        album_art = track['album']['images'][0]['url'] if track['album']['images'] else ''
        
        # Get track features (danceability, energy, valence)
        #features = sp.audio_features(track['id'])[0]
        #danceability = features['danceability']
        #energy = features['energy']
        #valence = features['valence']
        #popularity = track['popularity']

        # Determine vibe category
        #if danceability >= 0.7 and energy >= 0.7 and valence >= 0.7:
        #    vibe_category = 'Energetic'
        #elif danceability >= 0.4 and energy >= 0.4 and valence >= 0.4:
        #    vibe_category = 'Mild'
        #else:
        #    vibe_category = 'Chill'

        # Fetch genres from the track details
        genres = []
        for artist in track['artists']:
            artist_id = artist['id']
            artist_info = sp.artist(artist_id)

        # Append genres to a comma-separated string

        songs.append({
            'index': i + 1,
            'track_name': track_name,
            'artist_names': artist_names,
            'album_art': album_art,
            #'popularity': popularity,
            #'energy': energy,
            #'valence': valence,
            #'danceability': danceability
        })

    return render(request, 'spotifyapp/view_top_songs.html', {'songs': songs, 'time_range': time_range})


def get_all_user_tracks():
    try:
        all_tracks = set()

        playlists = sp.current_user_playlists()['items']
        for playlist in playlists:
            playlist_id = playlist['id']
            results = sp.playlist_tracks(playlist_id)
            tracks = results['items']
            while results['next']:
                results = sp.next(results)
                tracks.extend(results['items'])

            for track in tracks:
                if track['track'] is None:
                    continue
                all_tracks.add(track['track']['id'])

        results = sp.current_user_saved_tracks()
        for item in results['items']:
            track = item['track']
            if track is not None:
                all_tracks.add(track['id'])

        return all_tracks

    except requests.exceptions.RequestException as e:
        print(f"Error fetching user tracks: {e}")
        return set()

def get_recommendations(seed_tracks, num_recommendations, user_track_ids):
    try:
        recommended_tracks = []
        while len(recommended_tracks) < num_recommendations:
            limit = min(50, num_recommendations - len(recommended_tracks))
            recommendations = sp.recommendations(seed_tracks=seed_tracks, limit=limit)
            for rec_track in recommendations['tracks']:
                if rec_track['id'] not in user_track_ids and rec_track['id'] not in [track['id'] for track in recommended_tracks]:
                    recommended_tracks.append(rec_track)
                    if len(recommended_tracks) == num_recommendations:
                        break
            if len(recommended_tracks) < num_recommendations:
                seed_tracks = random.sample(seed_tracks, min(5, len(seed_tracks)))

        return recommended_tracks

    except spotipy.SpotifyException as e:
        print(f"Spotify API Error: {e}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return []
    except Exception as e:
        print(f"Error fetching recommendations: {e}")
        return []

def create_playlist(name):
    try:
        playlist = sp.user_playlist_create(sp.current_user()['id'], name, public=False)
        return playlist['id']
    except Exception as e:
        print(f"Error creating playlist: {e}")
        return None

def add_tracks_to_playlist(playlist_id, track_ids):
    try:
        sp.user_playlist_add_tracks(sp.current_user()['id'], playlist_id, track_ids)
    except Exception as e:
        print(f"Error adding tracks to playlist: {e}")

def index(request):
    return render(request, 'spotifyapp/index.html')

def create_genre_playlist(request):
    if request.method == 'POST':
        genre = request.POST.get('explore_a_genre')
        logger.debug("Debug message: 1")
        user_track_ids = get_all_user_tracks()

        genre_tracks = []
        offset = 0
        logger.debug("Debug message: 2")
        while len(genre_tracks) < 50 and offset < 1000:  # Limit search to first 1000 tracks
            results = sp.search(q=f'genre:"{genre}"', type='track', limit=50, offset=offset)
            logger.debug("Debug message: 3")
            tracks = results['tracks']['items']
            for track in tracks:
                logger.debug("Debug message: 4")
                if track['id'] not in user_track_ids:
                    genre_tracks.append(track)
                logger.debug("Debug message: 5")
                if len(genre_tracks) >= 50:
                    break
            offset += 50

        if not genre_tracks:
            # Handle case where no tracks were found for the genre
            print(f"No tracks found for genre: {genre}")
            return HttpResponse("No tracks found for the specified genre.")

        logger.debug("Debug message: 6")
        genre_track_ids = [track['id'] for track in genre_tracks]
        random.shuffle(genre_track_ids)
        logger.debug("Debug message: 7")
        playlist_name = f"{genre} Playlist"
        new_playlist_id = create_playlist(playlist_name)
        logger.debug("Debug message: 8")
        if new_playlist_id:
            add_tracks_to_playlist(new_playlist_id, genre_track_ids[:50])  # Add up to 50 tracks
            return redirect('index')
        else:
            return HttpResponse("Failed to create playlist.")

    return render(request, 'spotifyapp/view_top_genres.html')

def create_recommendation_playlist_from_playlist(request):
    if request.method == 'POST':
        playlist_link = request.POST.get('playlist_link')
        playlist_id = extract_playlist_id(playlist_link)

        user_track_ids = get_all_user_tracks()
        tracks = sp.playlist_tracks(playlist_id)['items']
        track_ids = [track['track']['id'] for track in tracks if track['track'] is not None]

        num_recommendations = int(request.POST.get('num_recommendations'))
        rec_track_ids = []
        for i in range(0, num_recommendations, 5):
            seed_tracks = random.sample(track_ids, 5)
            recommendations = get_recommendations(seed_tracks, 5, user_track_ids)
            for rec_track in recommendations:
                rec_track_ids.append(rec_track['id'])

        playlist_name = request.POST.get('playlist_name')
        new_playlist_id = create_playlist(playlist_name)
        add_tracks_to_playlist(new_playlist_id, rec_track_ids)
        return redirect('index')

    return render(request, 'spotifyapp/create_recommendation_playlist.html')

def get_recently_played_tracks():
    try:
        results = sp.current_user_recently_played(limit=50)
        tracks = results['items']
        while results['next']:
            results = sp.next(results)
            tracks.extend(results['items'])
        return tracks
    except spotipy.SpotifyException as e:
        print(f"Spotify API Error: {e}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return []
    except Exception as e:
        print(f"Error fetching recently played tracks: {e}")
        return []
