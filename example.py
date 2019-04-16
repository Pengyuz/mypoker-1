from pypokerengine.api.game import setup_config, start_poker
from randomplayer import RandomPlayer
from raise_player import RaisedPlayer
from testplayer import TestPlayer as T1
from testplayer1 import TestPlayer1 as T2
import json
import pprint
from random import uniform

#TODO:config the config as our wish
config = setup_config(max_round=100, initial_stack=1000, small_blind_amount=10)

Te1 = T1()
Te2 = T2()

config.register_player(name="FT1", algorithm=Te1)
config.register_player(name="FT2", algorithm=Te2)

# with open('file.txt', 'w') as file:
#     pass
    # file.write(json.dumps(exDict))
file  =  open('dataset.txt','w')

count = 0
for ele in range(10):
    pp = pprint.PrettyPrinter(indent=2)
    pp.pprint(Te1.weights)
    pp.pprint(Te2.weights)
    game_result = start_poker(config, verbose=1)
    a=0
    b=0
    for player in game_result['players']:
        if player['name'] == 'FT1':
            a = player['stack']
        elif player['name'] == 'FT2':
            b = player['stack']
    if a < b:
        count += 1
    # if a < b:
    #     base_weights = Te2.weights
    #     new_weights = {'strength':base_weights['strength']+0.1, 'ps':1, 'raiseNo':1}
    #
    #     Te1.setWeights(new_weights)
    #     file.write(json.dumps((Te2.weights)))
    # else:
    #     base_weights = Te1.weights
    #     new_weights = {'strength': base_weights['strength'] + 0.1, 'ps': 1, 'raiseNo': 1}
    #
    #     Te2.setWeights(new_weights)
    #     file.write(json.dumps((Te1.weights)))
file.close()
print(count)
# pp = pprint.PrettyPrinter(indent=2)
# pp.pprint(game_result)
