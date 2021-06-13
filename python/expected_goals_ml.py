# -*- coding: utf-8 -*-
"""
Created on Sat Jun  5 14:04:10 2021

@author: Jared
"""

import pymongo
from pymongo import MongoClient
import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import pandas as pd
import certifi
from matplotlib.path import Path
from zlib import crc32

def calc_distance(row):
    return np.sqrt((row['x']-coords_net[0])**2 + (row['y']-coords_net[1])**2)

#%% ----- LOAD DATA FROM DB -----
# connect to mongodb database
uri = "mongodb+srv://jvb_admin:jvb_mdb_admin@cluster0.w1jp0.mongodb.net/game_events"
client = MongoClient(uri, tlsCAFile=certifi.where())
db_cursor = client.game_events
plays_collection = db_cursor.rs_1920_plays
boxscores_collection = db_cursor.rs_1920_boxscores

# start with basic query to collect goals, shots and missed shots regardless of 
# strength - exclude empty net goals
pipeline = [{'$unwind': '$allPlays'},
		{'$project': {
			'event': '$allPlays.result.event',
			'shooter': { '$arrayElemAt': [ '$allPlays.players.player.fullName' , 0 ] },
			'team': '$allPlays.team.triCode',
			'x': '$allPlays.coordinates.x',
			'y': '$allPlays.coordinates.y',
			'period': '$allPlays.about.period',
            'empty_net': '$allPlays.result.emptyNet'
			}
		},
		{'$match': {
			'$and': [{
				'$or': [
					{'event': 'Shot'},
					{'event': 'Missed Shot'},
					{'event': 'Goal'}
				]},
			{'empty_net': {'$ne': 'true'}}
			]}
		}
		]

query_shots = list(plays_collection.aggregate(pipeline))
#%% ----- PLOT SHOTS OVERLAID ON RINK -----

# convert shots to data frame for transformations
df_shots = pd.DataFrame(query_shots)

# transform coordinates to have all shots on same side for each team
df_shots.loc[df_shots.x <= 0, ['x','y']] *= -1

f = plt.figure(figsize = (5,3))
ax = f.add_subplot(1,1,1)
ax.scatter(df_shots['x'], df_shots['y'], s = 0.1, c = 'r', alpha = 0.1)

#%% show all shots overlaid on rink
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

# load rink image
img_bg = plt.imread(bg_path)

# rink extents
rink_bg_extents = [-100, 100, -42.5, 42.5]

marker = 's'
shot_ms = 45 # shot marker size

home_plate_coords = {'x': [54, 54, 68, 89, 89, 68],
                     'y': [-24, 24, 24, 9.5, -9.5, -24]}

# list of hex colors for shots, missed shots and goals in that order
# ----- home -----
c_h = ['#4E6587', '#EDECF1', '#324157']
ec_h = ['#4E6587', '#4E6587', '#324157']
# ---- away -----
c_a = ['#87704E', '#F0F1EC', '#64412B']
ec_a = ['#87704E','#87704E', '#64412B']

f = plt.figure(figsize = (5,3))
ax_m = f.add_subplot(1,1,1)
ax_m.imshow(img_bg, extent = rink_bg_extents)
ax_m.scatter(df_shots['x'], df_shots['y'], s = 0.1, c = c_h[0], ec = ec_h[0], alpha = 0.1)
ax_m.set_aspect(1)
ax_m.set(xlim=(-0, 100), ylim=(-42.5, 42.5))
ax_m.axis('off')

#%% transform data for ml
# single var prediction: distance from net
coords_net = [90.5 ,0]
    
data_df = df_shots.copy()
data_df.dropna(subset = ['x', 'y'], inplace=True)
# compute distance in feet to net for each shot
data_df['distance'] = data_df.apply(calc_distance, axis=1)
# assign target (goal or not)
data_df['target'] = data_df['event'].apply(lambda x: 1 if x == 'Goal' else 0)

# define data sets for model training
features = ['distance']
target = ['target']


# y = data_df[target].squeeze()

# divide data set into train, validate and test sets
# create hash of each instances identifier and use that to assign train/test
# ensures same points are assigned each time the data is loaded

from sklearn.model_selection import train_test_split
from sklearn.model_selection import KFold

train_df, test_df = train_test_split(data_df, test_size = 0.2, random_state = 1)

# define train features and target
X = train_df[features]
y = train_df[target]

# create kFold object
num_folds = 10
kf = KFold(num_folds, shuffle  = True, random_state = 1)

# train and validate model for each train/validation split
for train_ind, val_ind in kf.split(train_df):
    X_train, y_train = X.iloc[train_ind], y.iloc[train_ind]
    X_val, y_val = X.iloc[val_ind], y.iloc[val_ind]
#%%
# fit a basic logistic regression model
from sklearn.linear_model import LogisticRegression
plt.close('all')

# reshape to 1D arrays for Logistic Regressio
y = np.array(y).reshape((y.shape[0],))

# define and fit logistic regression model
log_reg = LogisticRegression()
log_reg.fit(X[['distance']], y)

# predict probability for each training instance
y_prob = log_reg.predict_proba(X[['distance']])
# predict class based on default 0.5 decision boundary
y_pred = log_reg.predict(X[['distance']])
# predict socres for each training instance
y_scores = log_reg.decision_function(X[['distance']])


# plot goal vs miss
f = plt.figure(figsize = (7,3))
ax = f.add_subplot(1,1,1)
ax.scatter(X[y == 1],y[y == 1],s = 0.1, c = ec_h[0])
ax.scatter(X[y < 1],y[y < 1],s = 0.1, c = ec_a[0])
ax.grid(True, alpha = 0.5, linestyle = '--', linewidth = 0.5 )
ax.set_xlabel('Distance to goal (ft)')
ax.set_ylabel('Outcome')
plt.tight_layout()

# plot goal vs miss
f = plt.figure(figsize = (7,3))
ax = f.add_subplot(1,1,1)
ax.scatter(X['distance'], y_prob[:,1], s = 0.5, c = ec_a[0])
ax.scatter(X['distance'], y_pred, s = 0.5, c = ec_h[0])
ax.grid(True, alpha = 0.5, linestyle = '--', linewidth = 0.5 )
ax.set_xlabel('Distance to goal (ft)')
ax.set_ylabel('Outcome')
plt.tight_layout()

# plot roc curve
from sklearn.metrics import roc_curve

fpr, tpr, thresholds  = roc_curve(y, y_scores)

f = plt.figure(figsize = (3,3))
ax = f.add_subplot(1,1,1)
ax.plot(fpr, tpr, linewidth = 1.5, c = ec_h[0], label = None)
ax.plot([0,1], [0,1], linestyle = '--', c = '#151b24', linewidth = 1)
ax.grid(True, alpha = 0.5, linestyle = '--', linewidth = 0.5 )
ax.set_xlabel('False positive rate')
ax.set_ylabel('True positive rate')
plt.tight_layout()

# get logistic regression auc score
from sklearn.metrics import roc_auc_score
auc_score = roc_auc_score(y, y_scores)
print('AUC score: {}'.format(auc_score))


