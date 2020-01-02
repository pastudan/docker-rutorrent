#!/usr/bin/env python

# first sudo pip install pyyaml
# then in rtorrent.rc:
#   method.set_key = event.download.finished,sort_finished,"execute={python3,/app/sort.py,$d.hash=}"
#   OPTIONALLY: (will produce large log files)
#   log.execute = /config/log/rtorrent/execute.log

import signal
import xmlrpc.client
import os
import sys
import shutil
import yaml
import re
import requests

base_location = '/downloads'

class timeout:
    def __init__(self, seconds=1, error_message='Timeout'):
        self.seconds = seconds
        self.error_message = error_message
    def handle_timeout(self, signum, frame):
        raise TimeoutError(self.error_message)
    def __enter__(self):
        signal.signal(signal.SIGALRM, self.handle_timeout)
        signal.alarm(self.seconds)
    def __exit__(self, type, value, traceback):
        signal.alarm(0)

with timeout(seconds=15):
    # Capturing output from this script with rtorrent seems impossible,
    # so we'll write to our own log file
    log_filepath = os.path.join(base_location, 'last_sort.log')
    log_file = open(log_filepath, "w")
    sys.stdout = log_file
    sys.stderr = log_file

    print('=== START SORT SCRIPT ===')

    # Load config file
    with open("/config/rtorrent/sort-config.yaml", "r") as stream:
        config = yaml.load(stream, Loader=yaml.BaseLoader)

    # Set base location

    # Add default location
    matches = []
    if config['trackers']['default']:
        matches.append(config['trackers']['default'])

    # Find hash from input
    hash = sys.argv[1]
    print('     Hash: %s' % hash)

    # rtorrent xmlrpc
    server_url = "http://localhost/RPC2";
    rtorrent = xmlrpc.client.Server(server_url);

    base_path = rtorrent.d.base_path(hash)
    print('basepath:' + base_path)

    # sanity check to make sure torrent actually exists
    if not os.path.exists(base_path):
        print('%s: Base path doesn\'t exist, quitting' % base_path)
        exit()

    # outputting some information
    (start_dir, start_name) = os.path.split(base_path)
    print('File name: %s' % start_name)
    print(' File dir: %s' % start_dir)

    # determine a match based on tracker
    trackers = rtorrent.t.multicall(hash, '', 't.url=')
    find_trackers = re.compile('^https?://(\w+\.)*(\w+\.\w+)(:\d+)?/').search(trackers[0][0])
    if find_trackers:
        tracker = find_trackers.group(2)
        print('  Tracker: %s' % tracker)
        if tracker in config['trackers']:
            matches.append(config['trackers'][tracker])

    print('  Matches: %s' % matches)

    # test matches in order of score
    print(matches)
    match = sorted(matches, key=lambda m: int(m['priority']), reverse=True)[0]
    final_dir = os.path.join(base_location, match['folder'])
    if not os.path.exists(final_dir):
        os.makedirs(final_dir)

    final_path = os.path.join(final_dir, start_name)
    print('  Move to: %s' % (final_dir))

    # some checks based on computer path
    if base_path == final_path:
        print('%s: File is already at target location' % start_name)
    elif os.path.exists(final_path):
        print('%s: Another file already exists at target location' % start_name)
    else:
        # move torrent to new location and inform rtorrent
        print('Moving and telling rtorrent to move %s to %s' % (hash, final_dir))
        rtorrent.d.directory(hash, final_dir)
        shutil.move(base_path, final_dir)
        rtorrent.d.resume(hash)

        # Tell plex to re-scan for media
        tv_lib_id = os.getenv('PLEX_TV_LIBRARY_ID', default=1)
        movie_lib_id = os.getenv('PLEX_MOVIE_LIBRARY_ID', default=2)
        plex_token = os.getenv('PLEX_TOKEN')
        if not plex_token:
            print('WARNING: No plex token defined, not attempting to update library')
        else:
            r = requests.get("http://{}:32400/library/sections/{}/refresh?X-Plex-Token={}".format(
                config['plex_hostname'], config['plex_tv_library_id'], config['plex_token']))
            r = requests.get("http://{}:32400/library/sections/{}/refresh?X-Plex-Token={}".format(
                config['plex_hostname'], config['plex_movie_library_id'], config['plex_token']))
    log_file.close()

