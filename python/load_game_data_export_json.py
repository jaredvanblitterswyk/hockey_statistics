# -*- coding: utf-8 -*-
"""
Created on Thu Jan  2 14:27:25 2020

@author: Jared Van Blitterswyk

This code reads in full game data from the nhl api
01.02.2020: This code extracts shots on target and missed shots and plots them 
            on a rink schematic (categorised by home and away teams on separate ends of the rink)
"""
# ----------------------------------------------------------------------------
# import relevant libraries
# ----------------------------------------------------------------------------
import numpy as np
import pandas as pd
import os
import csv
from csv import reader, writer
import requests
import json
import matplotlib.pyplot as plt

results = []
# ----------------------------------------------------------------------------
# initialize folders
# ----------------------------------------------------------------------------
root = 'C:/Users/Jared/Documents/hockey_statistics/game_data/2021_2022'
team_games_filename = 'team_games_ids.json'
path_teams_games = os.path.join(root, team_games_filename)
data_dir_evnt = os.path.join(root, 'events')
data_dir_info = os.path.join(root, 'info')
data_dir_bxs = os.path.join(root, 'boxscores')
game_range = [2021020001, 2021020038]

# check if directories and files exist - if not create
if not os.path.exists(root):
    os.mkdir(root)

if not os.path.exists(data_dir_evnt):
    os.mkdir(data_dir_evnt)
    
if not os.path.exists(data_dir_info):
    os.mkdir(data_dir_info)
    
if not os.path.exists(data_dir_bxs):
    os.mkdir(data_dir_bxs)
    
if os.path.isfile(os.path.join(root,team_games_filename)):
    with open(os.path.join(root,team_games_filename), 'r') as infile:
        team_games_ids = json.load(infile)
else:
    team_games_ids = {}
# ----------------------------------------------------------------------------
#%% extract game data from NHL api
# ----------------------------------------------------------------------------    
print('------------------------------------------------------')
print('Scraping all plays from games in specified NHL season:')
print('------------------------------------------------------')
data_files = [f for f in os.listdir(data_dir_bxs)]

# loop through games and pull down data from api
for game_id in range(game_range[0], game_range[1]+1, 1):
    # check if game data already loaded
    current_game = str(game_id) + '.json'
    if not os.path.exists(os.path.join(data_dir_bxs,current_game)):
        # create url for game data (nhl api)
        try:          
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
            teams_abbrev = [boxscore['teams']['home']['team']['abbreviation'],
                            boxscore['teams']['away']['team']['abbreviation']]
            
            # add game id to team dictionary
            if teams_abbrev[0] in team_games_ids.keys():
                team_games_ids[teams_abbrev[0]].append(game_id)
            else:
                team_games_ids[teams_abbrev[0]] = [game_id]
            if teams_abbrev[1] in team_games_ids.keys():
                team_games_ids[teams_abbrev[1]].append(game_id)
            else:
                team_games_ids[teams_abbrev[1]] = [game_id]    
            
            # ------------------------------------------------------------------------
            # generate filenames and save data
            # ------------------------------------------------------------------------
            path_boxscore = os.path.join(data_dir_bxs,current_game)
            path_events = os.path.join(data_dir_evnt,current_game)
            path_info = os.path.join(data_dir_info,current_game)
            
            # write each event as a separate document (json) file
            with open(path_events, 'w') as outfile1:
                json.dump(events, outfile1)
                    
            with open(path_boxscore, 'w') as outfile2:
                json.dump(boxscore, outfile2)  
               
            with open(path_info, 'w') as outfile3:
                json.dump(game_info, outfile3)  
                    
            # save updated dictionary with game ids for each team
            with open(path_teams_games, 'w') as outfile4:                
                json.dump(team_games_ids, outfile4)
            
        except:
            print(f'Stopped game data import early - game not played yet. \nLast game played was {game_id-1}')
            break
        
