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
data_dir = 'C:/Users/Jared/Documents/hockey_statistics/20192020_game_data/'

directory = os.path.dirname(data_dir)
if not os.path.exists(directory):
    os.makedirs(directory)
print('------------------------------------------------------')
print('Scraping all plays from games in 2019-2020 NHL season:')
print('------------------------------------------------------')
for game_id in range(2019020001, 2019021083, 1): # this is currently set up to process on game (current game to current game +1)
    url = 'https://statsapi.web.nhl.com/api/v1/game/{}/feed/live'.format(game_id)
    r = requests.get(url)
    game_data = r.json()
    
    player_names = []
    
    print('Game ID: '+ str(game_id))   
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
                 
    keys_game_data = game_data['liveData'].keys()
    all_plays = game_data['liveData']['plays']['allPlays']
    
    teams = [boxscore['teams']['home']['team']['name'],boxscore['teams']['away']['team']['name']]
    teams_abbrev = [boxscore['teams']['home']['team']['abbreviation'],boxscore['teams']['away']['team']['abbreviation']]
    date = game_data['gameData']['datetime']['dateTime'][0:10]
    season = game_data['gameData']['game']['season']
    fname = season+'_'+date+'_'+teams_abbrev[0]+'_v_'+teams_abbrev[1]+'.csv'
    
    fname = fname.replace('-','_')
    fname = fname.lower()
    fname = fname.replace(' ','_')
    # =========================================================================
    # save all plays to file
    filename = data_dir+fname
    with open(filename, 'w', newline='') as csvfile:
    
        header = ['Date_Time','Period','Period_Time','Period_Time_Remaining',
                  'Event_Type','Event_Type_Secondary','x','y',
                  'Player_1','Player_1_Type','Player_1_Team',
                  'Player_2','Player_2_Type','Player_2_Team',
                  'Player_3','Player_3_Type','Player_3_Team',
                  'Player_4','Player_4_Type','Player_4_Team']
        writer = csv.writer(csvfile)
        writer.writerow(header)
    
        for play in all_plays:
            eventInfo = []
            if play['coordinates'] and 'players' in play.keys():
                # -----------------------------------------------------------------
                # details (time, period, period time, period time remaining)
                eventType = play['result']['event']
                resultKeys = play['result'].keys()
                if 'secondaryType' in resultKeys:
                    eventSecondary = play['result']['secondaryType']
                else:
                    eventSecondary = 'n/a'
                dateTime = play['about']['dateTime']
                period = play['about']['period']
                periodTime = play['about']['periodTime']
                periodTimeRemaining = play['about']['periodTimeRemaining']
                
                eventInfo = [dateTime,period,periodTime,periodTimeRemaining,
                             eventType,eventSecondary]
                
                # -----------------------------------------------------------------
                # event coordinates
                coords = play['coordinates']
                if coords:
                    eventInfo.extend([coords['x'],coords['y']])
                else:
                    eventInfo.extend(['n/a','n/a'])
                
                # -----------------------------------------------------------------
                # players
                num_players = len(play['players'])
                
                for i in range(0,num_players):
                    player = play['players'][i]['player']['fullName']
                    playerType = play['players'][i]['playerType']

                    if i > 0 and i == num_players-1:
                        if play['team']['name'] == teams[1]:
                            playerTeam = teams[0]
                        else:
                            playerTeam = teams[1]
                    else:
                        playerTeam = play['team']['name']
                            
                    eventInfo.extend([player,playerType,playerTeam])
                    
                if num_players < 4:
                    num_blanks = (4-num_players)*3
                    
                    for i in range(0,num_blanks):
                        eventInfo.extend(['n/a'])
                    
                '''
                if len(play['players']) > 1:
                    player1 = play['players'][1]['player']['fullName']
                    player1Type = play['players'][1]['playerType']
                    if player0Team == teams[0]:
                        player1Team = teams[1]
                    else:
                        player1Team == teams[0]
                else:
                    player1 = 'n/a'
                    player1Type = 'n/a'
                    player1Team = 'n/a'
                    
                eventInfo.extend([player0, player0Type, player0Team, player1, player1Type, player1Team])
                '''
                writer = csv.writer(csvfile)
                writer.writerow(eventInfo)
        
    # =========================================================================
    # save boxscore information to file
            

        

    '''
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
              
            print(play.get('result').get('event'))
            print(play.get('players')[0]['player']['fullName'])
            print('Coordinates:')
            print('x:'+ str(play.get('coordinates').get('x')))
            print('y:'+str(play.get('coordinates').get('y')))
            
            
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
    '''