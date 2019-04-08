from pypokerengine.api.game import setup_config, start_poker
from randomplayer import RandomPlayer
from raise_player import RaisedPlayer
from testplayer import TestPlayer

#TODO:config the config as our wish
config = setup_config(max_round=10, initial_stack=1000, small_blind_amount=10)



config.register_player(name="FT1", algorithm=RandomPlayer())
config.register_player(name="FT2", algorithm=TestPlayer())


game_result = start_poker(config, verbose=1)
