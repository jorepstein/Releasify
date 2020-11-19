import argparse
import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials
import time
from typing import List

CLIENT_ID = "333893227b6343b1a4effa9d73fe51a8"
CLIENT_SECRET = "ee4804d37dfe4c4a8deb8db9076bcfaf"
REDIRECT_URI = "http://localhost"


class Releasify:
    def __init__(self):
        scope = "user-library-read playlist-modify-private playlist-modify-public"
        self._user_spotify = spotipy.Spotify(
            auth_manager=SpotifyOAuth(scope=scope,
                                      client_id=CLIENT_ID,
                                      client_secret=CLIENT_SECRET,
                                      redirect_uri=REDIRECT_URI))
        self._user_id = self._user_spotify.me()['id']

        self._client_spotify = spotipy.Spotify(
            auth_manager=SpotifyClientCredentials(
                client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET,
            ))

    @property
    def user_id(self):
        return self._user_id

    def run_playlist(self, playlist_id: str):
        new_playlist_id = self._create_new_playlist(
            self._get_playlist_name(playlist_id))
        all_tracks = set()

        artist_ids = self._get_artist_ids_from_playlist_id(playlist_id)
        print(f"Found {len(artist_ids)} artists on playlist.")
        for artist_id in list(artist_ids):
            album_ids = self._get_album_ids_from_artist_id(artist_id)
            for album_id in album_ids:
                track_ids = self._get_track_ids_from_album_id(album_id)
                track_ids = [
                    track_id for track_id in track_ids
                    if track_id not in all_tracks
                ]
                if track_ids:
                    self._user_spotify.user_playlist_add_tracks(
                        self.user_id, new_playlist_id, track_ids)
                all_tracks.update(track_ids)
        print(f"Found {len(all_tracks)} new tracks.")

    def _create_new_playlist(self, base_name: str) -> str:
        new_name = f'Releasify: {base_name}'
        new_playlist = self._user_spotify.user_playlist_create(
            self.user_id, new_name)
        print("Created new playlist:", new_name)
        print(new_playlist['external_urls']['spotify'])

        return new_playlist['id']

    def _get_playlist_name(self, playlist_id: str) -> str:
        playlist_name = self._user_spotify.playlist(playlist_id,
                                                    fields='name')['name']
        return playlist_name

    def _get_artist_ids_from_playlist_id(self, playlist_id: str) -> List[str]:
        limit = 100
        all_artist_ids = set()

        num_tracks = self._user_spotify.playlist_items(playlist_id,
                                                       limit=limit,
                                                       fields='total')['total']
        num_batches = num_tracks // limit + 1
        for i in range(num_batches):
            results = self._user_spotify.playlist_items(playlist_id,
                                                        limit=limit,
                                                        offset=i * limit)
            for item in results['items']:
                artists = item['track']['artists']
                for artist in artists:
                    all_artist_ids.add(artist['id'])
        return all_artist_ids

    def _get_album_ids_from_artist_id(self, artist_id: str) -> List[str]:
        limit = 50
        all_album_ids = set()

        num_albums = self._client_spotify.artist_albums(artist_id,
                                                        limit=limit)['total']
        num_batches = num_albums // limit + 1
        for i in range(num_batches):
            results = self._client_spotify.artist_albums(
                artist_id,
                limit=limit,
                offset=i * limit,
                album_type='album,single')
            for album in results['items']:
                release_time = get_release_time(
                    album['release_date'], album['release_date_precision'])
                if release_time and (get_current_time() - release_time <
                                     604800):
                    all_album_ids.add(album['id'])
        return all_album_ids

    def _get_track_ids_from_album_id(self, album_id: str) -> List[str]:
        limit = 50
        all_track_ids = set()

        num_tracks = self._client_spotify.album_tracks(album_id,
                                                       limit=limit)['total']
        num_batches = num_tracks // limit + 1
        for i in range(num_batches):
            results = self._client_spotify.album_tracks(album_id,
                                                        limit=limit,
                                                        offset=i * limit)
            for track in results['items']:
                all_track_ids.add(track['id'])
        return all_track_ids


def get_release_time(release_date: str, precision: str) -> int:
    if precision == 'day':
        pattern = '%Y-%m-%d'
    elif precision == 'month':
        pattern = '%Y-%m'
    else:
        pattern = '%Y'
    try:
        release_time = int(time.mktime(time.strptime(release_date, pattern)))
    except OverflowError:
        return None
    return release_time


def get_current_time() -> int:
    return int(time.time())


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("playlist_ids",
                        type=str,
                        nargs="+",
                        help="playlist ids to search")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    r = Releasify()
    for playlist_id in args.playlist_ids:
        r.run_playlist(playlist_id)
