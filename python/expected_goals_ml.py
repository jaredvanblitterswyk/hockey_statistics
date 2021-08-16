# -*- coding: utf-8 -*-
"""
Created on Sat Jun  5 14:04:10 2021

@author: Jared
"""
import sys
import os
import pymongo
from pymongo import MongoClient
import numpy as np
import math as m
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import pandas as pd
import certifi
from matplotlib.path import Path
from zlib import crc32
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

def calc_distance(row):
    return np.sqrt((row['x']-coords_net[0])**2 + (row['y']-coords_net[1])**2)

def calc_angle(row):
    dx = row['x'] - coords_net[0]
    dy = abs(row['y'] - coords_net[1])
    return np.arctan2(dx,dy)*180/m.pi

#%% ----- LOAD DATA FROM DB -----
# connect to mongodb database
uri = config.mongoDB_uri
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
client.close()
#%% ----- PLOT SHOTS OVERLAID ON RINK -----
# -----------------------------------------------------------------------------
# convert shots to data frame for transformations
df_shots = pd.DataFrame(query_shots)

# transform coordinates to have all shots on same side for each team
df_shots.loc[df_shots.x <= 0, ['x','y']] *= -1

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

# plot shots overlaid on rink
f = plt.figure(figsize = (5,3))
ax_m = f.add_subplot(1,1,1)
ax_m.imshow(img_bg, extent = rink_bg_extents)
ax_m.scatter(df_shots['x'], df_shots['y'], s = 0.1, c = c_h[0], ec = ec_h[0], alpha = 0.1)
ax_m.set_aspect(1)
ax_m.set(xlim=(0, 100), ylim=(-42.5, 42.5))
ax_m.axis('off')

#%% ----- PREDICT GOALS WITH UNIVARIATE LOGISTIC REGRESSION -----
# -----------------------------------------------------------------------------
# ----- add features -----
# -----------------------------------------------------------------------------
# single var prediction: distance from net
coords_net = [89,0]
    
data_df = df_shots.copy()

data_df.dropna(subset = ['x', 'y'], inplace=True)
# remove shots below the goal line
data_df = data_df[data_df['x'] <= coords_net[0]]
# compute distance in feet to net for each shot
data_df['distance'] = data_df.apply(calc_distance, axis=1)
data_df['angle'] = data_df.apply(calc_angle, axis = 1)
# assign target (goal or not)
data_df['target'] = data_df['event'].apply(lambda x: 1 if x == 'Goal' else 0)

# define data sets for model training
features = ['distance']
target = ['target']

# -----------------------------------------------------------------------------
# ----- divide into train, test and validate sets -----
# -----------------------------------------------------------------------------
# use random_state to ensure same points assigned each time the data is loaded
from sklearn.model_selection import train_test_split
from sklearn.model_selection import KFold

train_df, test_df = train_test_split(data_df, test_size = 0.2, random_state = 1)

# define train features and target
X = train_df[features]
y = train_df[target].squeeze()

# create kFold object
num_folds = 10
kf = KFold(num_folds, shuffle  = True, random_state = 1)

# train and validate model for each train/validation split
for train_ind, val_ind in kf.split(train_df):
    X_train, y_train = X.iloc[train_ind], y.iloc[train_ind]
    X_val, y_val = X.iloc[val_ind], y.iloc[val_ind]

# -----------------------------------------------------------------------------
# ----- define model, train and predict -----
# -----------------------------------------------------------------------------
#plt.close('all')

# fit a basic logistic regression model
from sklearn.linear_model import LogisticRegression
log_reg = LogisticRegression()
log_reg.fit(X[features], y)

# predict probability for each training instance
y_prob = log_reg.predict_proba(X[features])
# predict class based on default 0.5 decision boundary
y_pred = log_reg.predict(X[features])
# predict socres for each training instance
y_scores = log_reg.decision_function(X[features])

# -----------------------------------------------------------------------------
# ----- plot results -----
# ----------------------------------------------------------------------------
params = dict()
params['figsize'] = (7,3)
params['s'] = 0.1
params['edge_colors'] = [ec_h[0], ec_a[0]]
params['face_colors'] = [ec_h[0], ec_a[0]]
params['xlabel'] = 'Distance to goal (ft)'
params['ylabel'] = 'Outcome'
params['tight_layout'] = True
params['labels'] = ['Goal', 'Non-goal']
params['tight_layout'] = True

def plot_two_series_scatter(x0, y0, x1, y1, params):
    # plot goal vs miss
    f = plt.figure(figsize = params['figsize'])
    ax = f.add_subplot(1,1,1)
    ax.scatter(x0, y0, s = params['s'], c = params['face_colors'][0],
               label = params['labels'][0])
    ax.scatter(x1, y1, s = params['s'], c = params['face_colors'][1],
               label = params['labels'][1])
    ax.grid(True, alpha = 0.5, linestyle = '--', linewidth = 0.5 )
    ax.set_xlabel(params['xlabel'])
    ax.set_ylabel(params['ylabel'])
    leg = plt.legend(fancybox=False, fontsize = 8)
    for lh in leg.legendHandles: 
        lh.set_alpha(1)
        lh._sizes = [6]
    if params['tight_layout']:    
        plt.tight_layout()

# plot shots outcome vs distance
plot_two_series_scatter(X[y == 1]['distance'], y[y == 1], X[y < 1]['distance'], y[y < 1], params)

# plot shots outcome vs probability
params['labels'] = ['Probability', 'Prediction']
params['ylabel'] = 'Probability of goal'
plot_two_series_scatter(X['distance'], y_prob[:,1], X['distance'], y_pred, params)

#%% ----- EVALUATE MODEL PERFORMANCE -----
# -----------------------------------------------------------------------------
#plt.close('all')
# lets add the predictions to the data frame for evaluating performance
train_df['predict'] = y_pred

true_positives = train_df[(train_df['predict'] == 1) & 
                          (train_df['target'] == 1)]['predict'].count()

true_negatives = train_df[(train_df['predict'] == 0) & 
                          (train_df['target'] == 0)]['predict'].count()

print('Decision boundary = 0.5: TN: {}, TP: {}'.format(true_negatives, true_positives))

# look at confusion matrix
# note: first row is negative class, second row is positive class
# Cij: observations known to be in class i, and predicted as class j
# format: TN, FP/FN, TP
from sklearn.metrics import confusion_matrix
print('Confusion matrix (default decision boundary)')
print(confusion_matrix(y,y_pred))

# with the default decision boundary, there are no positive predictions made
# to determine which threshold to use, consider precision, recall and threshold

from sklearn.metrics import precision_recall_curve, precision_score, recall_score
precisions, recalls, thresholds = precision_recall_curve(y,y_scores)

plt.figure(figsize = (3,3))
plt.plot(thresholds, precisions[:-1], linewidth = 1.5, c = ec_h[0], label = 'precision')
plt.plot(thresholds, recalls[:-1], linewidth = 1.5, c = ec_a[0],  label = 'recall')
plt.xlabel('Threshold')
plt.ylabel('')
plt.grid(True, alpha = 0.5, linestyle = '--', linewidth = 0.5 )
plt.legend(fancybox = False, fontsize = 8)
plt.tight_layout()

# say we want a classifier with a certain precision (TP/TP+FP), say 20%
threshold_75_precision = thresholds[np.argmax(precisions >=0.20)]

#now make predictions based on that threshold instead of the default value of 0
y_pred_75 = (y_scores >= threshold_75_precision).astype(int)

# now look at the confusion matrix, show precision and recall
print('Confusion matrix (20% precision threshold)')
print(confusion_matrix(y,y_pred_75))
print('Precision: {}'.format(precision_score(y,y_pred_75)))
print('Recall: {}'.format(recall_score(y,y_pred_75)))

# check performance vs a random guess
y_pred_random = np.random.randint(2, size=len(y))
# now look at the confusion matrix, show precision and recall
print('Confusion matrix (random guess)')
print(confusion_matrix(y,y_pred_random))
print('Precision: {}'.format(precision_score(y,y_pred_random)))
print('Recall: {}'.format(recall_score(y,y_pred_random)))

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
ax.grid(True, alpha = 0.5, linestyle = '--', linewidth = 0.5 )
plt.tight_layout()

f = plt.figure(figsize = (3,3))
ax = f.add_subplot(1,1,1)
sp = ax.scatter(fpr, tpr, linewidth = 1.5, c = thresholds, s = 1, label = None)
ax.plot([0,1], [0,1], linestyle = '--', c = '#151b24', linewidth = 1)
ax.grid(True, alpha = 0.5, linestyle = '--', linewidth = 0.5 )
ax.set_xlabel('False positive rate')
ax.set_ylabel('True positive rate')
f.colorbar(sp, ax = ax)
ax.grid(True, alpha = 0.5, linestyle = '--', linewidth = 0.5 )
plt.tight_layout()

# get logistic regression auc score
from sklearn.metrics import roc_auc_score
auc_score = roc_auc_score(y, y_scores)
print('AUC score: {}'.format(auc_score))

#%% ----- GENERATE XG VS LOCATION -----
# ----------------------------------------------------------------------------
x_eval_vec = np.linspace(0,89,179)
y_eval_vec = np.linspace(-41.5,41.5, 167)

x_eval, y_eval = np.meshgrid(x_eval_vec, y_eval_vec)

rows, cols = x_eval.shape

eval_df = pd.DataFrame()
eval_df['x'] = np.reshape(x_eval, (-1,))
eval_df['y'] = np.reshape(y_eval, (-1,))
eval_df['distance'] = eval_df.apply(calc_distance, axis=1)
eval_df['angle'] = eval_df.apply(calc_angle, axis = 1)

y_prob_eval = log_reg.predict_proba(eval_df[features])

# mask corners of rink
verts = [
   (74, -41.5),  
   (84, -38.5), 
   (89.1, -35.4),  
   (89.1, 35.4),  
   (84, 38.5),
   (74,41.5),
   (70, 43),
   (90,43),
   (90,-43),
   (74,-42)
]

codes = [
    Path.MOVETO,
    Path.LINETO,
    Path.LINETO,
    Path.LINETO,
    Path.LINETO,
    Path.LINETO,
    Path.LINETO,
    Path.LINETO,
    Path.LINETO,
    Path.CLOSEPOLY,
]

path = Path(verts, codes)

eval_df['xG_score'] = y_prob_eval[:,1]
eval_df = eval_df.apply(lambda r: np.nan if path.contains_point((np.abs(r.x), r.y)) else r, axis= 1)

xG_score = np.array(eval_df['xG_score']).reshape((rows,cols))

import matplotlib.patches as patches

# show mask for prediction grid
fig, ax = plt.subplots()
patch = patches.PathPatch(path, facecolor='orange', lw=2)
ax.add_patch(patch)
ax.set_xlim(0, 100)
ax.set_ylim(-44, 44)
plt.show()

# plot xGscore overlaid on rink
f = plt.figure(figsize = (5,3))
ax_m = f.add_subplot(1,1,1)
ax_m.imshow(img_bg, extent = rink_bg_extents)
pm = ax_m.pcolormesh(x_eval, y_eval, xG_score, cmap='Reds', vmin=0, vmax=0.25, alpha = 0.45)
ax_m.set(xlim=(0, 100), ylim=(-42.5, 42.5))
ax_m.set_aspect(1)
cbar = f.colorbar(pm, ax = ax_m)
cbar.ax.set_title('xG_score', fontsize = 10)
ax_m.axis('off')