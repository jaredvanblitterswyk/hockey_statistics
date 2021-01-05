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
import requests
import json
import matplotlib.pyplot as plt

results = []
player_profile_folder = 'C:/Users/Jared/Documents/player_stats/'

for game_id in range(2019020613, 2019020614, 1): # this is currently set up to process on game (current game to current game +1)
    url = 'https://statsapi.web.nhl.com/api/v1/game/{}/feed/live'.format(game_id)
    r = requests.get(url)
    game_data = r.json()
    
    player_names = []
       
    boxscore = game_data['liveData']['boxscore']
    # create dictionaries for all players in the game to store info, stats, shots, goals
    for x in ['home','away']:
        player_dict = boxscore.get('teams').get(x).get('skaters')
        #player_id_game[x] = player_dict
        for i in player_dict:
            p_name = boxscore.get('teams').get(x).get('players').get('ID'+str(i)).get('person').get('fullName')
            p_name = p_name.replace(' ','_') # replace space in name - can then be used as file name
            p_name = p_name.replace('.','_') # replace space in name - can then be used as file name
            p_name = p_name.lower() # convert to all lower case - preference, not mandatory
            player_names.append(p_name)
            p_info = boxscore.get('teams').get(x).get('players').get('ID'+str(i)).get('person')
            p_stats_summary = boxscore.get('teams').get(x).get('players').get('ID'+str(i)).get('stats').get('skaterStats')
            
            # create dictionary with relevant information for each player from the given game
            indiv_dict = { 'info': p_info,
                'game': int(game_id),
                'stats_summary': p_stats_summary,
                'shots': {'x':[],'y':[]},
                'missed_shots': {'x':[],'y':[]},
                'goals': {'x':[],'y':[]}}
            locals()[p_name] = indiv_dict # rename the dictionary to the player name
    
    # -----------------------------------------------------
    # shortened code to extract shots and goals and player ids
    keys_game_data = game_data['liveData'].keys()
    all_plays = game_data['liveData']['plays']['allPlays']
    
    play_filter = ['Shot','Missed Shot','Goal']
    for play in all_plays:
        category = play.get('result').get('event')
        if category in play_filter:
            p_name_event = play.get('players')[0]['player']['fullName']
            # convert skater name to match dictionary names
            p_name_event = p_name_event.replace(' ','_')
            p_name_event = p_name_event.replace('.','_')
            p_name_event = p_name_event.lower() 
                    
            if category == 'Shot':
                vars()[p_name_event]['shots']['x'].append(np.abs(play.get('coordinates').get('x')))
                if play.get('coordinates').get('x') < 0:
                    vars()[p_name_event]['shots']['y'].append(-1*play.get('coordinates').get('y'))
                else:
                    vars()[p_name_event]['shots']['y'].append(play.get('coordinates').get('y'))
            elif category == 'goal':
                vars()[p_name_event]['goals']['x'].append(np.abs(play.get('coordinates').get('x')))
                if play.get('coordinates').get('x') < 0:
                    vars()[p_name_event]['goal']['y'].append(-1*play.get('coordinates').get('y'))
                else:
                    vars()[p_name_event]['goal']['y'].append(play.get('coordinates').get('y'))               
            elif category == 'Missed Shot':
                vars()[p_name_event]['missed_shots']['x'].append(np.abs(play.get('coordinates').get('x')))
                if play.get('coordinates').get('x') < 0:
                    vars()[p_name_event]['missed_shots']['y'].append(-1*play.get('coordinates').get('y'))
                else:
                    vars()[p_name_event]['missed_shots']['y'].append(play.get('coordinates').get('y')) 
            
            # print event, player, and coordinates for troubleshooting
            '''    
            print(play.get('result').get('event'))
            print(play.get('players')[0]['player']['fullName'])
            print('Coordinates:')
            print('x:'+ str(play.get('coordinates').get('x')))
            print('y:'+str(play.get('coordinates').get('y')))
            '''
            
    # write player profiles to file

    for player in player_names:
        profile_path = os.path.join(player_profile_folder,player)
        filename = str(game_id)+'_'+str(player)+'.csv'
        current_dict = locals()[player]
        if not os.path.exists(profile_path):
            os.makedirs(profile_path) 
        
        with open(profile_path+'/'+filename,'w', newline="") as f:
            writer = csv.writer(f,delimiter = ',')
            for key in current_dict:
                if key == 'game':
                    writer.writerow([key, "", current_dict[key]])
                elif key == 'shots' or key == 'goals' or key == 'missed_shots':
                    writer.writerow([key, "x", "y"])
                    for i in range(0,len(current_dict[key]['x'])):
                        writer.writerow(["",current_dict[key]['x'][i],current_dict[key]['y'][i]])
                else:
                    inst = 0
                    if current_dict.get(key):
                        for item in current_dict[key]:
                        # if empty, nothing listed - healthy scratch/injured
                            if inst == 0:
                                writer.writerow([key, item, current_dict[key][item]])
                            elif item == 'None':
                                writer.writerow([key, "", current_dict[key]])
                            else:
                                writer.writerow(["", item, current_dict[key][item]])
                            inst += 1
                            
                            # add functionality to print table of shots and goals rather than printing array to cell
                