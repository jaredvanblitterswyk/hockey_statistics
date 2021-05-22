# -*- coding: utf-8 -*-
"""
Query mongodb data base and plot map of shots for a given game

"""

import pymongo
from pymongo import MongoClient
import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import pandas as pd

# connect to mongodb database
uri = "mongodb+srv://jvb_admin:jvb_mdb_admin@cluster0.w1jp0.mongodb.net/game_events"
client = MongoClient(uri)
events = client.game_events
rs1920_plays = events.rs_1920_plays
rs1920_boxscores = events.rs_1920_boxscores

# define game to extract
game = 2019020005

pipeline = [{'$unwind': '$allPlays'},
            {'$project': {
                'event': '$allPlays.result.event',
                'primary_player': { '$arrayElemAt': [ '$allPlays.players.player.fullName' , 0 ] },
                'x': '$allPlays.coordinates.x',
                'y': '$allPlays.coordinates.y',
                'team': '$allPlays.team.triCode',
                'period': '$allPlays.about.period'
                }
            },
            {'$match': {
                '$and': [
                    {
                    '$or': [
                        {'event': 'Shot'},
                        {'event': 'Missed Shot'},
                        {'event': 'Goal'}
                        ]
                    },
                    {'_id': game}
                    ]
                }
            }
            ]

query_shots = list(rs1920_plays.aggregate(pipeline))

pipeline = [{'$match': {'_id': game}},
            {'$lookup':
                 {
                     'from': 'rs_1920_info',
                     'let': {'curr_game': "$_id"},
                     'pipeline': [
                         {'$match': {
                             '$expr': {'$eq': ['$_id', '$$curr_game']}
                             }
                         },
                         {'$project': {
                             'home': '$teams.home.triCode',
                             'away': '$teams.away.triCode',
                             'date': '$datetime.dateTime',
                             'venue': '$venue.name'
                             }
                         }
                     ],
                     'as': 'info'
                 }
             },
            {'$project': {
                '_id': 1,
                'home': '$info.home',
                'away': '$info.away',
                'date': '$info.date',
                'venue': '$info.venue',
                'home_stats': '$teams.home.teamStats.teamSkaterStats',
                'away_stats': '$teams.away.teamStats.teamSkaterStats'
                }
            },
            {'$limit': 3}
            ]
    
query_info = list(rs1920_boxscores.aggregate(pipeline))

# convert shots to data frame for transformations
df_shots = pd.DataFrame(query_shots)
#%% transform data to show home and away shots on different ends of ice
'''
NOTES:
    home: shooting on right first, away: shooting on left first
    - show shots from first period orientation (shots taken not conceeded)
    - flip coordinates:
        - home: P2
        - away: P2
'''
# transform coordinates to have all shots on same side for each team
df_shots.loc[df_shots.period == 2, ['x','y']] *= -1

home_team = query_info[0]['home'][0]
away_team = query_info[0]['away'][0]

# separate shots on target, goals and missed shots for each 
# ----- home -----
home_goals = df_shots.loc[
    ((df_shots['team'] ==  home_team) & 
     (df_shots['event'] == 'Goal')), 
    ['x','y']
    ]

home_missed = df_shots.loc[
    ((df_shots['team'] ==  home_team) & 
     (df_shots['event'] == 'Missed Shot')), 
    ['x','y']
    ]

home_shots = df_shots.loc[
    ((df_shots['team'] ==  home_team) & 
     (df_shots['event'] == 'Shot')), 
    ['x','y']
    ]
# ----- away -----
away_goals = df_shots.loc[
    ((df_shots['team'] ==  away_team) & 
     (df_shots['event'] == 'Goal')), 
    ['x','y']
    ]

away_missed = df_shots.loc[
    ((df_shots['team'] ==  away_team) & 
     (df_shots['event'] == 'Missed Shot')), 
    ['x','y']
    ]

away_shots = df_shots.loc[
    ((df_shots['team'] ==  away_team) & 
     (df_shots['event'] == 'Shot')), 
    ['x','y']
    ]


#%% GENERATE FIG
plt.close('all')

# define path to background images
fig_dir = 'C:/Users/Jared/Documents/hockey_statistics/figures'
bg_filename = 'full_ice_scale_mm.png'
bg_path = os.path.join(fig_dir,bg_filename)

#plt.style.use('C:/Users/Jared/Documents/hockey_statistics/python/stg_plot_style_1.mplstyle')
plt.rcParams['font.family'] = 'Avenir LT Std'
plt.rcParams['font.style'] = 'normal'
plt.rcParams['font.variant'] = 'normal'
plt.rcParams['font.weight'] = 'light'
plt.rcParams['font.stretch'] = 'normal'
plt.rcParams['font.size'] = 12

# define paths to logo
logo_home_filename = home_team.lower()+'_logo_nhl.png'
logo_away_filename = away_team.lower()+'_logo_nhl.png'

logo_home_path = os.path.join(fig_dir,logo_home_filename)
logo_away_path = os.path.join(fig_dir,logo_away_filename)

# load images
img_bg = plt.imread(bg_path)
home_logo = plt.imread(logo_home_path)
away_logo = plt.imread(logo_away_path)

# calculate logo extents for plotting
if np.argmax(home_logo.shape) == 0:
    scale = home_logo.shape[0]/56
    t, b = 28,-28
    l, r = -55 - home_logo.shape[1]/scale/2, -55 + home_logo.shape[1]/scale/2
else:
    scale = home_logo.shape[1]/56
    l, r = -85, -29
    t, b = home_logo.shape[0]/scale/2, -home_logo.shape[0]/scale/2
    
extent_home_logo = [l,r,b,t]

if np.argmax(away_logo.shape) == 0:
    scale = away_logo.shape[0]/56
    t, b = 28,-28
    l, r = 55 - away_logo.shape[1]/scale/2, 55 + away_logo.shape[1]/scale/2
else:
    scale = away_logo.shape[1]/56
    r, l = 85, 29
    t, b = away_logo.shape[0]/scale/2, - away_logo.shape[0]/scale/2
    
extent_away_logo = [l,r,b,t]
marker = 's'

# ----- generate 'dshboard-style' figure -----
f = plt.figure(figsize = (10,7), constrained_layout=False)
gs = f.add_gridspec(4, 7)

# add logo
'''
f_ax1 = f.add_subplot(gs[2, 0])
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
'''

# list of hex colors for shots, missed shots and goals in that order
# ----- home -----
c_h = ['#4E6587', '#EDECF1', '#2B4E64']
ec_h = ['#4E6587', '#4E6587', '#2B4E64']
# ---- away -----
c_a = ['#87704E', '#F0F1EC', '#64412B']
ec_a = ['#87704E','#87704E', '#64412B']

# plot goals overlaid on rink
f_ax1 = f.add_subplot(1,1,1)
f_ax1.imshow(img_bg,extent=[-100, 100, -42.5, 42.5])

f_ax1.scatter(
    home_shots['x'], home_shots['y'], marker = marker, s= 45,
    c = c_h[0], edgecolors = ec_h[0], alpha = 1, label = 'Shots'
    )
f_ax1.scatter(
    home_missed['x'], home_missed['y'], marker = marker, s= 45,
    c = c_h[1], edgecolors = ec_h[1], alpha = 1, label = 'Missed Shots'
    )
f_ax1.scatter(
    home_goals['x'], home_goals['y'], marker = marker, s= 45,
    c = c_h[2], edgecolors = ec_h[2], alpha = 1, label = 'Goals'
    )
f_ax1.scatter(
    away_shots['x'], away_shots['y'], marker = marker, s= 45,
    c = c_a[0], edgecolors = ec_a[0], alpha = 1, label = 'Shots'
    )
f_ax1.scatter(
    away_missed['x'], away_missed['y'], marker = marker, s= 45,
    c = c_a[1], edgecolors = ec_a[1], alpha = 1, label = 'Missed Shots'
    )
f_ax1.scatter(
    away_goals['x'], away_goals['y'], marker = marker, s= 45,
    c = c_a[2], edgecolors = ec_a[2], alpha = 1, label = 'Goals'
    )
f_ax1.imshow(home_logo, extent = extent_home_logo, alpha = 0.15)
f_ax1.imshow(away_logo, extent = extent_away_logo, alpha = 0.15)
f_ax1.set_aspect(1)
f_ax1.set(xlim=(-100, 100), ylim=(-42.5, 42.5))
f_ax1.axis('off')

# legend for home and away
children = f_ax1.get_children()
legend1 = plt.legend([children[i] for i in [0,1,2]], ['Shot', 'Missed Shot', 'Goal'], loc=3, bbox_to_anchor=(0.05, -0.1), frameon = False, fancybox = False, ncol = 3)
legend2 = plt.legend([children[i] for i in [3,4,5]], 
                     ['Shot', 'Missed Shot', 'Goal'], 
                     loc=4, bbox_to_anchor=(0.95, -0.1), 
                     frameon = False, fancybox = False, ncol = 3,
                     prop={'family':'Avenir LT Std', 'style': 'normal', 'weight':'light'})
f_ax1.add_artist(legend1)
#plt.setp(legend2.texts, family='Avenir LT Std')
f_ax1.add_artist(legend2)

#Add text to figure:
f_ax1.text(-12, 55, home_team + ' vs. ' + away_team, fontsize=16)
f_ax1.text(-10, 48, query_info[0]['date'][0][0:10], fontsize=12)
f_ax1.text(-10, 44, query_info[0]['venue'][0], fontsize=12)
#f_ax2.text(0, 0.6, player['team'], fontsize=10)
'''
f_ax3 = f.add_subplot(gs[2,1:3])
f_ax3.barh(['Goals', 'Shots', 'Hits'],
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
    
#f_ax1.legend(loc = 'lower left', frameon = True, fancybox = False)
'''

# add author and data source text
plt.tight_layout()
plt.show()

#%%

# assign queries to home and away stats to variable for easier calls
home_query = query_info[0]['home_stats']
away_query = query_info[0]['away_stats']

# define summary stats
game_summary = {'goals': home_query['goals'] + away_query['goals'],
                'shots': home_query['shots'] + away_query['shots'],
                'hits': home_query['hits'] + away_query['hits']}

h_stats = [home_query['goals']/game_summary['goals'],
           home_query['shots']/game_summary['shots'],
           home_query['hits']/game_summary['hits']]

a_stats = [away_query['goals']/game_summary['goals'],
           away_query['shots']/game_summary['shots'],
           away_query['hits']/game_summary['hits']]

# define plot parameters/variables
labels = [0, 0.7, 1.4]
index = np.arange(len(labels))
width = 0.08 # bar width

#plt.close('all')
f = plt.figure(figsize = (5,3), constrained_layout=False)

ax = f.add_subplot(1,1,1)
ax.barh(labels, h_stats, width, color = ec_h[1], ec = '#FFFFFF', linewidth = 1.5, label = 'HOME')
ax.barh(labels, a_stats, width, color = ec_a[1], ec = '#FFFFFF', linewidth = 1.5, left = h_stats, label = 'AWAY')
ax.axes.xaxis.set_visible(False)
ax.axes.yaxis.set_visible(False)
ax.set_ylim([-0.5,2.5])
ax.spines['right'].set_visible(False)
ax.spines['top'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.spines['bottom'].set_visible(False)

# ----- annotate -----
ax.annotate(str(home_query['goals']),(0.0, 0.2))
ax.annotate(str(away_query['goals']),(0.97, 0.2))
ax.annotate(str(home_query['shots']),(0.0, 0.9))
ax.annotate(str(away_query['shots']),(0.95, 0.9))
ax.annotate(str(home_query['hits']),(0.0, 1.6))
ax.annotate(str(away_query['hits']),(0.95, 1.6))
ax.annotate('Goals', (0.43, 0.2))
ax.annotate('Shots', (0.43, 0.9))
ax.annotate('Hits', (0.435, 1.6))
