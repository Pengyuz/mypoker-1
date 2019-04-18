from pypokerengine.api.game import setup_config, start_poker
from randomplayer import RandomPlayer
from raise_player import RaisedPlayer
from testplayer import TestPlayer as T1
from testplayer1 import TestPlayer1 as T2
from testplayer2 import TestPlayer2 as T3
from testplayer3 import TestPlayer3 as T4

import json
import pprint
from random import uniform

#TODO:config the config as our wish
config = setup_config(max_round=50, initial_stack=1000, small_blind_amount=10)

Te1 = T1()
Te2 = T2()
Te3 = T3()
Te4 = T4()

config.register_player(name="FT1", algorithm=Te2)
config.register_player(name="FT2", algorithm=Te4)

# with open('file.txt', 'w') as file:
#     pass
    # file.write(json.dumps(exDict))
file  =  open('dataset.txt','w')

for i in range(0,10):
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
    print('count: ' + str(count))
    if count >= 7:
        base_weights = Te4.weights
        new_weights = {'strength':base_weights['strength']+uniform(-0.2, 0.2), 'ps':base_weights['ps']+uniform(-4,4), 'raiseNo':base_weights['raiseNo']+uniform(-4, 4),
                       'p': base_weights['p']+uniform(-0.2,0.2)}
        Te2.setWeights(new_weights)
        file.write(json.dumps((Te4.weights)))
        file.write('\n')
    elif count <= 3:
        base_weights = Te2.weights
        new_weights = {'strength':base_weights['strength']+uniform(-0.2, 0.2), 'ps':base_weights['ps']+uniform(-4,4), 'raiseNo':base_weights['raiseNo']+uniform(-4, 4),
                       'p': base_weights['p']+uniform(-0.2,0.2)}
        Te4.setWeights(new_weights)
        file.write(json.dumps((Te2.weights)))
        file.write('\n')

file.close()
# pp = pprint.PrettyPrinter(indent=2)
# pp.pprint(game_result)
