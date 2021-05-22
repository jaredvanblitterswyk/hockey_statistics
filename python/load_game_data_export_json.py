# -*- coding: utf-8 -*-
"""
Created on Thu Jan  2 14:27:25 2020

@author: Jared Van Blitterswyk

This code reads in full game data from the nhl api
01.02.2020: This code extracts shots on target and missed shots and plots them 
            on a rink schematic (categorised by home and away teams on separate ends of the rink)
"""

import numpy as np
import pandas as pd
import os
import csv
from csv import reader, writer
import requests
import json
import matplotlib.pyplot as plt

results = []
player_profile_folder = 'C:/Users/Jared/Documents/player_stats/'
data_dir_evnt = 'C:/Users/Jared/Documents/hockey_statistics/20192020_game_data_json/events'
data_dir_info = 'C:/Users/Jared/Documents/hockey_statistics/20192020_game_data_json/info'
data_dir_bxs = 'C:/Users/Jared/Documents/hockey_statistics/20192020_game_data_json/boxscore'

if not os.path.exists(data_dir_evnt):
    os.mkdir(data_dir_evnt)
    
if not os.path.exists(data_dir_info):
    os.mkdir(data_dir_info)
    
if not os.path.exists(data_dir_bxs):
    os.mkdir(data_dir_bxs)

print('------------------------------------------------------')
print('Scraping all plays from games in 2019-2020 NHL season:')
print('------------------------------------------------------')
for game_id in range(2019020001, 2019021083, 1): # 2019021083 - last game this is currently set up to process on game (current game to current game +1)
    # create url for game data (nhl api)
    url = 'https://statsapi.web.nhl.com/api/v1/game/{}/feed/live'.format(game_id)
    
    # use requests library to load in json data
    r = requests.get(url)
    game_data = r.json()
    
    # extract all plays and boxscore from dictionary
    events = game_data['liveData']['plays']
    boxscore = game_data['liveData']['boxscore']
    game_info = game_data['gameData']
    
    # convert player information to list - imported to mongodb as array
    players = game_info['players']
    game_info['players'] = [players[player_id] for player_id in players]
    
    # remove unnecessary fields
    del game_info['status']
    del events['currentPlay']
    
    # add _id field for mongodb
    events['_id'] = game_id
    boxscore['_id'] = game_id
    game_info['_id'] = game_id
    
    # extract relevant information to generate descriptive filename
    teams_abbrev = [boxscore['teams']['home']['team']['abbreviation'],boxscore['teams']['away']['team']['abbreviation']]
    fname = str(game_id)+'_'+teams_abbrev[0]+'_v_'+teams_abbrev[1]
    # filename formating
    fname = fname.replace('-','_')
    fname = fname.lower()
    fname = fname.replace(' ','_')
    # =========================================================================
    # generate filenames to save data
    path_boxscore = os.path.join(data_dir_bxs,fname+'_boxscore.json')
    path_events = os.path.join(data_dir_evnt,fname+'_plays.json')
    path_info = os.path.join(data_dir_info,fname+'_info.json')
        
    # write each event as a separate document (json) file
    with open(path_events, 'w') as outfile:
        json.dump(events, outfile)
            
    with open(path_boxscore, 'w') as outfile:
            json.dump(boxscore, outfile)  
       
    with open(path_info, 'w') as outfile:
            json.dump(game_info, outfile)  
