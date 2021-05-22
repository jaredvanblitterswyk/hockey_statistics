# -*- coding: utf-8 -*-
"""
Query mongodb data base and plot maps of goals for a given player

TO DO:
    - Automate information extraction from the database - many fields hardcoded
"""

import pymongo
from pymongo import MongoClient
import sys
import os
import pandas
import numpy as np
import json
import matplotlib.pyplot as plt

# connect to mongodb database
uri = "mongodb+srv://jvb_admin:jvb_mdb_admin@cluster0.w1jp0.mongodb.net/game_events"
client = MongoClient(uri)
events = client.game_events
rs1920 = events.rs_1920_plays

print(events.list_collection_names())
pipeline = [{'$unwind': '$allPlays'},
				{'$match': {
					'allPlays.result.event': 'Goal',
					'allPlays.players.0.player.fullName': {'$in' : ['Alex Ovechkin']},
					'allPlays.players.seasonTotal': {'$gt': 0}
					}
				},
				{'$project': {
					'_id': 1, 
					'allPlays.coordinates': 1
					}
				},
				{'$project': {
					'coords': {
						'$reduce': {
							'input': [['$allPlays.coordinates.x'],['$allPlays.coordinates.y']],
							'initialValue': [] ,
							'in': { '$concatArrays' : ["$$value", "$$this"] }
							}
						}
					}
				}
				]

query_return = list(rs1920.aggregate(pipeline))

goal_coords = []
for doc in query_return:
    goal_coords.append(doc['coords'])

# convert goals to one side of ice

for row in goal_coords:
    y = row[1]
    if row[0] < 0:
        x = -1*row[0]
    else:    
        x = row[0]


    
    # flip axes for plotting over rink
    row[0] = y
    row[1] = x
# convert to np array for plotting
goal_coords = np.array(goal_coords)

# general stats
# TO DO - get this info from mongodb query
gen_stats = {}
gen_stats['goals'] = 48
gen_stats['assists'] = 19
gen_stats['points'] = 67
gen_stats['shots'] = 311
gen_stats['shot_pct'] = 15.4
gen_stats['ppg'] = 13
gen_stats['ppp'] = 18

# player information
# TO DO - get this info from mongodb query
player = {}
player['name'] = 'Alex Ovechkin'
player['team'] = 'Washington Capitals'
player['age'] = 35
player['number'] = 8
player['height'] = '''6' 3"'''
player['weight'] = 236
player['position'] = 'Left Wing'
player['shoots'] = 'R'
#%% GENERATE FIG
# define path to background images
fig_dir = 'C:/Users/Jared/Documents/hockey_statistics/figures'
bg_filename = 'half_ice_w_home_plate_scale_mm.png'
bg_path = os.path.join(fig_dir,bg_filename)

# define path to logo
logo_filename = 'wsh_logo_nhl.png'
logo_path = os.path.join(fig_dir,logo_filename)

# load images
img_bg = plt.imread(bg_path)
img_logo = plt.imread(logo_path)

# ----- generate 'dshboard-style' figure -----
f = plt.figure(figsize = (10,5), constrained_layout=False)
gs = f.add_gridspec(4, 4)

# add logo
f_ax1 = f.add_subplot(gs[0, 1])
f_ax1.imshow(img_logo)
f_ax1.set_aspect(1)
f_ax1.axis('off')

# add player information
f_ax2 = f.add_subplot(gs[0, 0])
f_ax2.set(xlim=(0, 5), ylim=(0, 1))
f_ax2.text(0, 0.8, player['name'], fontsize=18)
f_ax2.text(0, 0.6, player['team'], fontsize=10)
f_ax2.text(0, 0.4, '#'+str(player['number'])+', '+ player['position'], fontsize=10)
f_ax2.text(0, 0.2, 'Age: '+ str(player['age'])+', Height: '+ str(player['height'])+', Weight: '+str(player['weight']),  fontsize=10)
f_ax2.axis('off')

f_ax3 = f.add_subplot(gs[1,0:2])
f_ax3.barh(['Goals', 'Assists', 'Points'],
           [gen_stats['goals'],gen_stats['assists'], gen_stats['points']], 
           color = '#5D6D7E', height = 0.75)
f_ax3.set(xlim=(0, 80))
#f_ax3.set(ylim=(0.25, 1.75))
#f_ax3.set_yticklabels(['Goals'])
f_ax3.annotate(str(gen_stats['goals']),(gen_stats['goals']+3,-0.1))
f_ax3.annotate(str(gen_stats['assists']),(gen_stats['assists']+3,0.9))
f_ax3.annotate(str(gen_stats['points']),(gen_stats['points']+3,1.9))
# hide axes and spines
f_ax3.axes.xaxis.set_visible(False)
f_ax3.spines['right'].set_visible(False)
f_ax3.spines['top'].set_visible(False)
f_ax3.spines['left'].set_visible(False)
f_ax3.spines['bottom'].set_visible(False)


# plot goals overlaid on rink
f_ax6 = f.add_subplot(gs[0:4, 2:4])
f_ax6.imshow(img_bg,extent=[-42.5, 42.5, 0, 100])
f_ax6.scatter(
    goal_coords[:,0], goal_coords[:,1], marker = 'o', s= 25,
    c = '#2E4053', edgecolors = '#2E4053', alpha = 0.7, label = 'Goals'
    )
f_ax6.set_aspect(1)
f_ax6.set(xlim=(-42.5, 42.5), ylim=(0, 100))
f_ax6.axis('off')
f_ax6.legend(loc = 'lower left', frameon = True, fancybox = False)


# add author and data source text
plt.tight_layout()
plt.show()


