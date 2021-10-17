# -*- coding: utf-8 -*-
"""
Created on Fri Sep 17 08:21:07 2021

@author: Jared
"""
# import modules
import sys
import os
import pymongo
from pymongo import MongoClient
import config
import certifi
import numpy as np
import math as m
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import pandas as pd
from matplotlib.path import Path
# add file to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

#%% ----- LOAD DATA FROM DB -----
# connect to mongodb database
uri = config.mongoDB_uri
client = MongoClient(uri, tlsCAFile=certifi.where())
db_cursor = client.game_events
plays_collection = db_cursor.rs_1920_plays
boxscores_collection = db_cursor.rs_1920_boxscores

pipeline = [{'$project': {
					'away': '$teams.away.skaters',
					'home': '$teams.home.skaters',
					'away_stats': {'$objectToArray': '$teams.away.players'},
					'home_stats': {'$objectToArray': '$teams.home.players'},
					}
				},
				{'$lookup': {
					'from': 'rs_1920_defencemen',
					'localField': 'away',
					'foreignField': 'player_id',
					'as': 'defencemen_away'
					}
				},
				{'$lookup': {
					'from': 'rs_1920_defencemen',
					'localField': 'home',
					'foreignField': 'player_id',
					'as': 'defencemen_home'
					}
				},
				{'$project': {
					'defencemen': {'$concatArrays': [ '$defencemen_home', '$defencemen_away' ]},
					'stats': {'$concatArrays': [ '$away_stats', '$home_stats' ]}
					}
				},
				{'$unwind': '$defencemen'},
				{'$unwind': '$stats'},
				{'$project': {
					'defencemen': 1,
					'stats': 1,
					'compare': {
						'$cmp': ['$defencemen._id', '$stats.v.person.fullName'] 
						}
					}
				},
				{'$match': {
					'compare': 0
					}
				},
				{'$project': {
					'defencemen': 1,
					'stats_name': '$stats.v.person.fullName',
					'stats_toi_min': {
                        '$minute': {
    						'$let': {
    							'vars': {'time': {'$split': ['$stats.v.stats.skaterStats.timeOnIce',':']}},
    							'in': {
    								'$dateFromParts': {
    									'year': 2019, 'month': 1, 'day': 1, 'hour': 0,
    									'minute': {'$toInt': {'$arrayElemAt': ['$$time', 0]}},
    									'second': {'$toInt': {'$arrayElemAt': ['$$time', 1]}}
    									}
    								}
    							}
                            }
						},
                    'stats_toi_sec': {
                        '$second': {
    						'$let': {
    							'vars': {'time': {'$split': ['$stats.v.stats.skaterStats.timeOnIce',':']}},
    							'in': {
    								'$dateFromParts': {
    									'year': 2019, 'month': 1, 'day': 1, 'hour': 0,
    									'minute': {'$toInt': {'$arrayElemAt': ['$$time', 0]}},
    									'second': {'$toInt': {'$arrayElemAt': ['$$time', 1]}}
    									}
    								}
    							}
                            }
						},
                    'stats_toi_pp': {
						'$let': {
							'vars': {'time_pp': {'$split': ['$stats.v.stats.skaterStats.powerPlayTimeOnIce',':']}},
							'in': {
								'$dateFromParts': {
									'year': 2019, 'month': 1, 'day': 1, 'hour': 0,
									'minute': {'$toInt': {'$arrayElemAt': ['$$time_pp', 0]}},
									'second': {'$toInt': {'$arrayElemAt': ['$$time_pp', 1]}}
									}
								}
							}
						},
					'stats_toi_sh': {
						'$let': {
							'vars': {'time_sh': {'$split': ['$stats.v.stats.skaterStats.shortHandedTimeOnIce',':']}},
							'in': {
								'$dateFromParts': {
									'year': 2019, 'month': 1, 'day': 1, 'hour': 0,
									'minute': {'$toInt': {'$arrayElemAt': ['$$time_sh', 0]}},
									'second': {'$toInt': {'$arrayElemAt': ['$$time_sh', 1]}}
									}
								}
							}
						}
					}
				},
				{'$group': {
					'_id': '$defencemen._id',
					'roster': {'$sum': 1},
					'toi_min': {'$sum': {'$toLong': '$stats_toi_min'}},
                    'toi_sec': {'$sum': {'$toLong': '$stats_toi_sec'}},
                    'toi_sh': {'$sum': {'$toLong': '$stats_toi_sh'}},
					'toi_pp': {'$sum': {'$toLong': '$stats_toi_pp'}}
					}
				},
				{'$set': {
					'toi': {'$dateToString': {
						'date': {
							'$dateFromParts': {
								'year': 2019, 'month': 1, 'day': 1, 'hour': 0, 'minute': '$toi_min', 'second': '$toi_sec', 'millisecond': 0
								}
							},
						'format': "%d:%H:%M:%S"
						}
					},
                    'toi_pk': {'$dateToString': {
						'date': {
							'$dateFromParts': {
								'year': 2019, 'month': 1, 'day': 1, 'hour': 0, 'millisecond': '$toi_sh'
								}
							},
						'format': "%H:%M:%S"
						}
					},
                    'toi_pp': {'$dateToString': {
						'date': {
							'$dateFromParts': {
								'year': 2019, 'month': 1, 'day': 1, 'hour': 0, 'millisecond': '$toi_pp'
								}
							},
						'format': "%H:%M:%S"
						}
					}
				}},
				{'$lookup': {
					'from': 'v_defencemen_scratch',
					'let': {'dman_name': "$_id" },
					'pipeline' : [
						{'$match': {
							'$expr': {'$eq': ["$_id", "$$dman_name" ]}
							},
						},
						{'$project' : {
							'_id': 0, 'scratch':1 
							}
						}],
					'as': 'scratched'
					}
				},
				{'$project': {
					'_id': 1,
					'gp': {'$subtract': ['$roster', {'$ifNull': [{'$arrayElemAt': ['$scratched.scratch', 0]}, 0]}]},
					'roster': 1, 
					'toi': 1,
                    'toi_pp': 1,
                    'toi_pk': 1,
					'scratch': {'$ifNull': [{'$arrayElemAt': ['$scratched.scratch', 0]}, 0]}
					}
				},
				{'$sort': {
					'gp': -1
					}
				}
				]

query_gp_toi = list(boxscores_collection.aggregate(pipeline))

# lets now query points, goals, assists
pipeline_pts = [{'$unwind': '$allPlays'},
		{'$match': {
			'allPlays.result.event': 'Goal',
			'allPlays.players.seasonTotal': {'$gt': 0}
			}
		},
		{'$project': {
			'allPlays.players': 1,
			'allPlays.result': 1,		
			}
		},
		{'$unwind': '$allPlays.players'},
		{'$match' : {
			'allPlays.players.playerType': {'$in': ['Assist','Scorer']}
			}
		},
		{'$project': {
			'allPlays.players': 1,
			'strength': '$allPlays.result.strength.code',
			'gwg': '$allPlays.result.gameWinningGoal',
			'en': '$allPlays.result.emptyNet'
			}
		},
		{'$lookup': {
			'from': 'rs_1920_defencemen',
			'localField': 'allPlays.players.player.fullName',
			'foreignField': '_id',
			'as': 'defencemen'
			}
		},
		{'$match': {
			'defencemen': {'$exists':'true', '$ne':[]}
			}
		},
		{'$project': {
			'allPlays.players': 1,
			'allPlays.result': 1,
			'player_type': '$allPlays.players.playerType',
			'name': '$allPlays.players.player.fullName', 
			'assist': {'$cond': [ {'$eq': ['$allPlays.players.playerType', 'Assist'] }, 1, 0]},
			'goals': {'$cond': [ {'$eq': ['$allPlays.players.playerType', 'Scorer'] }, 1, 0]},
			'gwg': {'$cond': [{'$and':[{'$eq': ['$allPlays.players.playerType', 'Scorer'] }, {'$eq': ['$gwg', True] }]}, 1, 0]},
			'en_goals': {'$cond': [{'$and': [{ '$eq': ['$allPlays.players.playerType', 'Scorer'] }, {'$eq': ['$en', True] }]}, 1, 0]}
			}
		},
		{'$group': {
			'_id': '$allPlays.players.player.fullName',
            'goals': {'$sum': '$goals'},
			'gwgs': {'$sum': '$gwg'},
			'en_goals': {'$sum': '$en_goals'},
			'assists': {'$sum': '$assist'},
			'points': {'$sum': 1}
			}
		},
		{'$sort': {
			'points': -1
			}
		}
		]

query_pts = list(plays_collection.aggregate(pipeline_pts))

# lets now query shot attempts, hits given and received, giveaways and takeaways
pipeline_shot_hit_gv_tk = [{'$unwind': '$allPlays'},
		{'$match': {'$or': [
			{'allPlays.result.event': 'Shot'},
			{'allPlays.result.event': 'Goal'},
			{'allPlays.result.event': 'Blocked Shot'},
			{'allPlays.result.event': 'Missed Shot'},
			{'allPlays.result.event': 'Giveaway'},
			{'allPlays.result.event': 'Takeaway'},
			{'allPlays.result.event': 'Hit'}
			]
			}
		},
		{'$project': {
			'allPlays.players': 1,
			'allPlays.result': 1,		
			}
		},
		{'$unwind': '$allPlays.players'},
		{'$lookup': {
			'from': 'rs_1920_defencemen',
			'localField': 'allPlays.players.player.fullName',
			'foreignField': '_id',
			'as': 'defencemen'
			}
		},
		{'$match': {
			'defencemen': {'$exists':'true', '$ne':[]}
			}
		},
		{'$project': {
			'allPlays.players': 1,
			'allPlays.result': 1,
			'player_type': '$allPlays.players.playerType',
			'name': '$allPlays.players.player.fullName', 
			'hits': {'$cond': [{'$eq': ['$allPlays.players.playerType', 'Hitter']}, 1, 0]},
			'hits_taken': {'$cond': [{'$eq': ['$allPlays.players.playerType', 'Hittee']}, 1, 0]},
			'giveaways': {'$cond': [{'$eq': ['$allPlays.result.event', 'Giveaway']}, 1, 0]},
			'takeaways': {'$cond': [{'$eq': ['$allPlays.result.event', 'Takeaway']}, 1, 0]},
			'shots': {'$cond': [
                {'$or': [
                    {'$and': [
                        {'$eq': ['$allPlays.players.playerType', 'Shooter']}, 
                        {'$eq': ['$allPlays.result.event', 'Shot']}
                        ]
                    }, 
                    {'$eq': ['$allPlays.players.playerType', 'Scorer']}
                    ]
                }, 1, 0]},
			'missed_shots': {'$cond': [
                {'$and': [
                    {'$eq': ['$allPlays.players.playerType', 'Shooter']}, 
                    {'$eq': ['$allPlays.result.event', 'Missed Shot']}
                    ]
                }, 1, 0]
                },
            'blocks': {'$cond': [{'$eq': ['$allPlays.players.playerType', 'Blocker']}, 1, 0]},
			'shots_blocked': {'$cond': [{'$and': [{'$eq': ['$allPlays.players.playerType', 'Shooter']}, {'$eq': ['$allPlays.result.event', 'Blocked Shot']}]}, 1, 0]},
			}
		},
		{'$group': {
			'_id': '$allPlays.players.player.fullName',
			's': {'$sum': '$shots'},
			's_miss': {'$sum': '$missed_shots'},
            's_block': {'$sum': '$shots_blocked'},
            'blocks': {'$sum': '$blocks'},
			'h': {'$sum': '$hits'},
			'h_take': {'$sum': '$hits_taken'},
			'gv': {'$sum': '$giveaways'},
			'tk': {'$sum': '$takeaways'}
			}
		},
		{'$sort': {
			's': -1
			}
		}
        ]

query_shgt = list(plays_collection.aggregate(pipeline_shot_hit_gv_tk))

client.close()

#%% TRANSFORM DATA
# convert to pandas dataframe and concatenate data queries
df_gptoi = pd.DataFrame(query_gp_toi).set_index('_id')
df_pts = pd.DataFrame(query_pts).set_index('_id')
df_shgt = pd.DataFrame(query_shgt).set_index('_id')

df = df_gptoi.join(df_pts, on = '_id', how = 'left')
df = df.join(df_shgt, on = '_id', how = 'left')

# convert toi to integer (minutes)
# days need to be adjusted - date time used to create assigns day = 9 by default
df['toi_adj'] = df['toi'].apply(lambda x: [int(x.split(':')[0]) - 1, int(x.split(':')[1]), int(x.split(':')[2]), int(x.split(':')[3])])
df['toi_min'] = df['toi_adj'].apply(lambda x: sum([x[0]*86400, x[1]*3600, x[2]*60, x[3]])/60)
df['toi_min_pk'] = df['toi_pk'].apply(lambda x: sum([int(x.split(':')[0])*3600, int(x.split(':')[1])*60, int(x.split(':')[2])])/60)
df['toi_min_pp'] = df['toi_pp'].apply(lambda x: sum([int(x.split(':')[0])*3600, int(x.split(':')[1])*60, int(x.split(':')[2])])/60)

df['gv_per_60'] = df['gv']/(df['toi_min']/60)
df['tk_per_60'] = df['tk']/(df['toi_min']/60)
df['hit_per_60'] = df['h']/(df['toi_min']/60)
df['blk_per_60'] = df['blocks']/(df['toi_min']/60)
df['shots_per_blk'] = df['s']/(df['s_block'])

df.drop(columns = ['toi', 'toi_adj'], inplace = True)

#%% Plot results
import matplotlib.patches as patches
f = plt.figure(figsize = (4,4))
ax = f.add_subplot(111)
ax.scatter(df['gv_per_60'], df['tk_per_60'], s = 8, marker = 'o',
           c = '#4E6587', edgecolors = '#4E6587', alpha = 0.6) 
ax.grid(True, alpha = 0.5, linestyle = '--', linewidth = 0.5 )
ax.set_xlabel('Giveaways per 60 mins')
ax.set_ylabel('Takeaways per 60 mins')

f = plt.figure(figsize = (4,4))
ax = f.add_subplot(111)
ax.scatter(df['hit_per_60'], df['blk_per_60'], s = 8, marker = 'o',
           c = '#4E6587', edgecolors = '#4E6587', alpha = 0.6) 
ax.grid(True, alpha = 0.5, linestyle = '--', linewidth = 0.5 )
ax.set_xlabel('Hits per 60 mins')
ax.set_ylabel('Blocks per 60 mins')

f = plt.figure(figsize = (4,4))
ax = f.add_subplot(111)
ax.scatter(df['goals'], df['shots_per_blk'], s = 8, marker = 'o',
           c = '#4E6587', edgecolors = '#4E6587', alpha = 0.6) 
ax.grid(True, alpha = 0.5, linestyle = '--', linewidth = 0.5 )
ax.set_xlabel('Goals')
ax.set_ylabel('Shots per block')

f = plt.figure(figsize = (4,4))
ax = f.add_subplot(111)
ax.scatter(df['toi_min'], df['toi_min_pk'], s = 8, marker = 'o',
           c = '#4E6587', edgecolors = '#4E6587', alpha = 0.6) 
ax.grid(True, alpha = 0.5, linestyle = '--', linewidth = 0.5 )
rect = patches.Rectangle((1400, 0), 500, 50, linewidth=1, edgecolor='r', facecolor='none')
# Add the patch to the Axes
ax.add_patch(rect)
ax.set_xlabel('toi (min)')
ax.set_ylabel('toi pk (min)')



