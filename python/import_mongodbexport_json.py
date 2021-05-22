# -*- coding: utf-8 -*-
"""
Created on Sun Mar 28 19:25:17 2021

@author: Jared

This function loads in json files from mongodbexport. The default files consist
of a collection of json items, which cannot be read natively as a json object
in python. To do so, the files need to be wrapped as a json object - this
includes wrapping all results with [ ] and separating entries with a comma.
This creates a list of dictionaries that can be parsed as a list.
"""
import json
import os

dir_path = 'C:/Users/Jared/Documents/hockey_statistics/20192020_game_data_json'
filename = 'test_output.json'

with open(os.path.join(dir_path,filename)) as f:
    data = json.loads("[" + 
        f.read().replace("}\n{", "},\n{") + 
    "]")
    