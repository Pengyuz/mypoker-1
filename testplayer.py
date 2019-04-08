from pypokerengine.players import BasePokerPlayer
from pypokerengine.utils.card_utils import gen_cards, estimate_hole_card_win_rate
import random as rand

import pprint

class TestPlayer(BasePokerPlayer):

    def __init__(self):
        self.my_stack = 1000
   
    def build_game_state(self, valid_actions, hole_card, round_state):

        game_state = {}

        game_state["turn"] = "me"
        game_state["street"] = round_state["street"]
        game_state["community_card"] = round_state["community_card"]
        game_state["my_hole_card"] = hole_card
       
        pot = round_state["pot"]["main"]["amount"]
        game_state["pot"] = pot
       
        b = 0
        player_uuids_stacks = [(player_info['uuid'], player_info["stack"]) for player_info in round_state["seats"]]
        for (uuid, stack) in player_uuids_stacks:

            if uuid == self.uuid:

                b = self.my_stack - stack
       
        game_state["my_bet"] = b
        game_state["oppo_bet"] = pot - b
        game_state["valid_actions"] = valid_actions
        game_state['action_histories'] = round_state['action_histories']
        return game_state
   
    def expectiminimax(self, node):
        MAX_INT = 1e20
        if node.is_terminal():  # fold node or nature_child
            return node.value
        if node.type == 'self':
            q = -MAX_INT
            for child in node.children:
                q = max(q, self.expectiminimax(child))
        elif node.type == 'oppo':
            q_list = []
            proba_distri = [0.33, 0.33, 0.33] # oppo model
            for child in node.children:
                q_list.append(self.expectiminimax(child))
            q = sum([i*j for i,j in zip(q_list, proba_distri)])
        elif node.type == 'nature':
            q = 0
            for child in node.children:
                # All children are equally probable
                q += len(node.children)**-1 * self.expectiminimax(child)
        node.set_value(q)
        return q
   
    def add_nature_node_children(self, nature_node, depth):
        '''
        append chldren of this nature_node
        '''
        game_state = nature_node.game_state
        all_cards = ['C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'C9', 'CT', 'CJ', 'CQ', 'CK', 'CA',
                     'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'DT', 'DJ', 'DQ', 'DK', 'DA',
                     'H2', 'H3', 'H4', 'H5', 'H6', 'H7', 'H8', 'H9', 'HT', 'HJ', 'HQ', 'HK', 'HA',
                     'S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'S8', 'S9', 'ST', 'SJ', 'SQ', 'SK', 'SA']
        visible_cards = []
        for c1 in game_state['my_hole_card']:
            visible_cards.append(c1)
        for c2 in game_state['community_card']:
            visible_cards.append(c2)

        # simulate new added community card, append all to nature_node
        for card in all_cards:
            if card not in visible_cards:
                nature_node.add_child(TreeNode([], self.evaluate(game_state), "self", None))
   
    def evaluate(self, game_state):
        '''
        evaluation function for cut off nodes
        '''
        hole_card = gen_cards(game_state['my_hole_card'])
        community_card = gen_cards(game_state['community_card'])
        pot = game_state['pot']
        winrate = estimate_hole_card_win_rate(nb_simulation=1, nb_player=2, hole_card=hole_card, community_card=community_card)
        return winrate * pot

    def construct_tree(self, game_state, depth, raise_time):
       
        if game_state["turn"] == "me":
           
            node = TreeNode([], 0, "self", game_state)
            if depth == 10:
                node.set_value(self.evaluate(game_state))
                return node

            my_bet = game_state["my_bet"]
            oppo_bet = game_state["oppo_bet"]
            for action in game_state["valid_actions"]:

                if action["action"] == "fold":

                    node.add_child(TreeNode([], -game_state["my_bet"], "fold", None))

                elif action["action"] == "raise":

                    new_game_state = game_state.copy()
                    new_game_state["turn"] = "oppo"
                    new_game_state["pot"] = new_game_state["pot"] + oppo_bet+10-my_bet
                    new_game_state["my_bet"] = new_game_state["my_bet"] + oppo_bet+10-my_bet
                    
                    if raise_time == 4:
                        new_valid_actions = [{ "action" : "fold"  },{ "action" : "call" }]
                    else:
                        new_valid_actions = [{ "action" : "fold"  },{ "action" : "call" },{ "action" : "raise" }]
                    
                    new_game_state["valid_actions"] = new_valid_actions
                    node.add_child(self.construct_tree(new_game_state, depth+1, raise_time+1))
               
                elif action["action"] == "call":
                   
                    if my_bet == oppo_bet:
                        nature_node = TreeNode([], 0, "nature", game_state)
                        node.add_child(nature_node)
                        self.add_nature_node_children(nature_node, depth)
                    else:
                        new_game_state = game_state.copy()
                        new_game_state["turn"] = "oppo"
                        new_game_state["pot"] = new_game_state["pot"] + 10
                        new_game_state["my_bet"] = new_game_state["my_bet"] + 10

                        if raise_time == 4:
                            new_valid_actions = [{ "action" : "fold"  },{ "action" : "call" }]
                        else:
                            new_valid_actions = [{ "action" : "fold"  },{ "action" : "call" },{ "action" : "raise" }]

                        new_game_state["valid_actions"] = new_valid_actions
                        node.add_child(self.construct_tree(new_game_state, depth+1, raise_time))
               
            return node
       
        else:
            node = TreeNode([], 0, "oppo", game_state)
            if depth == 10:
                node.set_value(self.evaluate(game_state))
                return node
           
            my_bet = game_state["my_bet"]
            oppo_bet = game_state["oppo_bet"]
            for action in game_state["valid_actions"]:

                if action["action"] == "fold":

                    node.add_child(TreeNode([], game_state["oppo_bet"], "fold", None))

                elif action["action"] == "raise":

                    new_game_state = game_state.copy()
                    new_game_state["turn"] = "me"
                    new_game_state["pot"] = new_game_state["pot"] + my_bet+10-oppo_bet
                    new_game_state["oppo_bet"] = new_game_state["oppo_bet"] + my_bet+10-oppo_bet

                    if raise_time == 4:
                        new_valid_actions = [{ "action" : "fold"  },{ "action" : "call" }]
                    else:
                        new_valid_actions = [{ "action" : "fold"  },{ "action" : "call" },{ "action" : "raise" }]

                    new_game_state["valid_actions"] = new_valid_actions
                    node.add_child(self.construct_tree(new_game_state, depth+1, raise_time+1))
               
                elif action["action"] == "call":
                   
                    if my_bet == oppo_bet:
                        nature_node = TreeNode([], 0, "nature", game_state)
                        node.add_child(nature_node)
                        self.add_nature_node_children(nature_node, depth)
                    else:
                        new_game_state = game_state.copy()
                        new_game_state["turn"] = "me"
                        new_game_state["pot"] = new_game_state["pot"] + 10
                        new_game_state["oppo_bet"] = new_game_state["oppo_bet"] + 10

                        if raise_time == 4:
                            new_valid_actions = [{"action": "fold"}, {"action": "call"}]
                        else:
                            new_valid_actions = [{"action": "fold"}, {"action": "call"}, {"action": "raise"}]

                        new_game_state["valid_actions"] = new_valid_actions
                        node.add_child(self.construct_tree(new_game_state, depth+1, raise_time))
               
            return node
   
    #  we define the logic to make an action through this method. (so this method would be the core of your AI)
    def declare_action(self, valid_actions, hole_card, round_state):
        
        game_state = self.build_game_state(valid_actions, hole_card, round_state)
        pp = pprint.PrettyPrinter(indent=2)
        #pp.pprint(hole_card)
        #pp.pprint(valid_actions)
        #print("------------ROUND_STATE(testpalyer)--------")
        #pp.pprint(round_state)
        #print("------------GAME_STATE(testpalyer)--------")
        #pp.pprint(game_state)
        #print("my stack:" + str(self.my_stack))

        if round_state['street'] == 'preflop':
            winrate = PreFlopWinTable().get_winrate(hole_card)
            if winrate <= 0.35:  # fold
                call_action_info = valid_actions[0]
            elif winrate >= 0.6 and len(valid_actions) == 3:  # raise
                call_action_info = valid_actions[2]
            else:  # call
                call_action_info = valid_actions[1]
            action = call_action_info["action"]
            return action
        else:
            start_node = self.construct_tree(game_state, 1, 0)
            self.expectiminimax(start_node)
            res = []
            for child in start_node.children:
                res.append(child.value)
            print(res)
            index = res.index(max(res))
            action = valid_actions[index]["action"]
            return action
        

    def receive_game_start_message(self, game_info):
        pass

    def receive_round_start_message(self, round_count, hole_card, seats):
        pass

    def receive_street_start_message(self, street, round_state):
        pass

    def receive_game_update_message(self, action, round_state):
        pass

    def receive_round_result_message(self, winners, hand_info, round_state):
        player_uuids_stacks = [(player_info['uuid'], player_info["stack"]) for player_info in round_state["seats"]]
        for (uuid, stack) in player_uuids_stacks:
            
            if uuid == self.uuid:
                
                self.my_stack = stack
   
class TreeNode(object):
    def __init__(self, children=None, value=None, type=None, game_state=None):
        self.children = []
        self.value = value
        self.type = type  # either 'self', 'oppo', 'nature', 'nature_child' or 'fold'
        self.game_state = game_state
        if children is not None:
            for child in children:
                self.add_child(child)

    def add_child(self, node):
        self.children.append(node)

    def is_terminal(self):
        return len(self.children) == 0
   
    def set_value(self, value):
        self.value = value


class PreFlopWinTable(object):
    def __init__(self):
        self.wintable = {}
        self.wintable['AA'] = 0.853
        self.wintable['AKs'] = 0.67
        self.wintable['AKo'] = 0.654
        self.wintable['AQs'] = 0.661
        self.wintable['AQo'] = 0.645
        self.wintable['AJs'] = 0.654
        self.wintable['AJo'] = 0.636
        self.wintable['ATs'] = 0.647
        self.wintable['ATo'] = 0.629
        self.wintable['A9s'] = 0.63
        self.wintable['A9o'] = 0.609
        self.wintable['A8s'] = 0.621
        self.wintable['A8o'] = 0.601
        self.wintable['A7s'] = 0.611
        self.wintable['A7o'] = 0.591
        self.wintable['A6s'] = 0.6
        self.wintable['A6o'] = 0.578
        self.wintable['A5s'] = 0.599
        self.wintable['A5o'] = 0.577
        self.wintable['A4s'] = 0.589
        self.wintable['A4o'] = 0.564
        self.wintable['A3s'] = 0.58
        self.wintable['A3o'] = 0.556
        self.wintable['A2s'] = 0.57
        self.wintable['A2o'] = 0.546
        self.wintable['KK'] = 0.824
        self.wintable['KQs'] = 0.634
        self.wintable['KQo'] = 0.614
        self.wintable['KJs'] = 0.626
        self.wintable['KJo'] = 0.606
        self.wintable['KTs'] = 0.619
        self.wintable['KTo'] = 0.599
        self.wintable['K9s'] = 0.6
        self.wintable['K9o'] = 0.58
        self.wintable['K8s'] = 0.585
        self.wintable['K8o'] = 0.563
        self.wintable['K7s'] = 0.578
        self.wintable['K7o'] = 0.554
        self.wintable['K6s'] = 0.568
        self.wintable['K6o'] = 0.543
        self.wintable['K5s'] = 0.558
        self.wintable['K5o'] = 0.533
        self.wintable['K4s'] = 0.547
        self.wintable['K4o'] = 0.521
        self.wintable['K3s'] = 0.538
        self.wintable['K3o'] = 0.512
        self.wintable['K2s'] = 0.529
        self.wintable['K2o'] = 0.502
        self.wintable['QQ'] = 0.799
        self.wintable['QJs'] = 0.603
        self.wintable['QJo'] = 0.582
        self.wintable['QTs'] = 0.595
        self.wintable['QTo'] = 0.574
        self.wintable['Q9s'] = 0.579
        self.wintable['Q9o'] = 0.555
        self.wintable['Q8s'] = 0.562
        self.wintable['Q8o'] = 0.538
        self.wintable['Q7s'] = 0.545
        self.wintable['Q7o'] = 0.519
        self.wintable['Q6s'] = 0.538
        self.wintable['Q6o'] = 0.511
        self.wintable['Q5s'] = 0.529
        self.wintable['Q5o'] = 0.502
        self.wintable['Q4s'] = 0.517
        self.wintable['Q4o'] = 0.49
        self.wintable['Q3s'] = 0.507
        self.wintable['Q3o'] = 0.479
        self.wintable['Q2s'] = 0.499
        self.wintable['Q2o'] = 0.47
        self.wintable['JJ'] = 0.775
        self.wintable['JTs'] = 0.575
        self.wintable['JTo'] = 0.554
        self.wintable['J9s'] = 0.558
        self.wintable['J9o'] = 0.534
        self.wintable['J8s'] = 0.542
        self.wintable['J8o'] = 0.517
        self.wintable['J7s'] = 0.524
        self.wintable['J7o'] = 0.499
        self.wintable['J6s'] = 0.508
        self.wintable['J6o'] = 0.479
        self.wintable['J5s'] = 0.5
        self.wintable['J5o'] = 0.471
        self.wintable['J4s'] = 0.49
        self.wintable['J4o'] = 0.461
        self.wintable['J3s'] = 0.479
        self.wintable['J3o'] = 0.45
        self.wintable['J2s'] = 0.471
        self.wintable['J2o'] = 0.44
        self.wintable['TT'] = 0.751
        self.wintable['T9s'] = 0.543
        self.wintable['T9o'] = 0.517
        self.wintable['T8s'] = 0.526
        self.wintable['T8o'] = 0.5
        self.wintable['T7s'] = 0.51
        self.wintable['T7o'] = 0.482
        self.wintable['T6s'] = 0.492
        self.wintable['T6o'] = 0.463
        self.wintable['T5s'] = 0.472
        self.wintable['T5o'] = 0.442
        self.wintable['T4s'] = 0.464
        self.wintable['T4o'] = 0.434
        self.wintable['T3s'] = 0.455
        self.wintable['T3o'] = 0.424
        self.wintable['T2s'] = 0.447
        self.wintable['T2o'] = 0.415
        self.wintable['99'] = 0.721
        self.wintable['98s'] = 0.511
        self.wintable['98o'] = 0.484
        self.wintable['97s'] = 0.495
        self.wintable['97o'] = 0.467
        self.wintable['96s'] = 0.477
        self.wintable['96o'] = 0.449
        self.wintable['95s'] = 0.459
        self.wintable['95o'] = 0.429
        self.wintable['94s'] = 0.438
        self.wintable['94o'] = 0.407
        self.wintable['93s'] = 0.432
        self.wintable['93o'] = 0.399
        self.wintable['92s'] = 0.423
        self.wintable['92o'] = 0.389
        self.wintable['88'] = 0.691
        self.wintable['87s'] = 0.482
        self.wintable['87o'] = 0.455
        self.wintable['86s'] = 0.465
        self.wintable['86o'] = 0.436
        self.wintable['85s'] = 0.448
        self.wintable['85o'] = 0.417
        self.wintable['84s'] = 0.427
        self.wintable['84o'] = 0.396
        self.wintable['83s'] = 0.408
        self.wintable['83o'] = 0.375
        self.wintable['82s'] = 0.403
        self.wintable['82o'] =0.368
        self.wintable['77'] = 0.662
        self.wintable['76s'] = 0.457
        self.wintable['76o'] = 0.427
        self.wintable['75s'] = 0.438
        self.wintable['75o'] = 0.408
        self.wintable['74s'] = 0.418
        self.wintable['74o'] = 0.386
        self.wintable['73s'] = 0.4
        self.wintable['73o'] = 0.366
        self.wintable['72s'] = 0.381
        self.wintable['72o'] = 0.346
        self.wintable['66'] = 0.633
        self.wintable['65s'] = 0.432
        self.wintable['65o'] = 0.401
        self.wintable['64s'] = 0.414
        self.wintable['64o'] = 0.38
        self.wintable['63s'] = 0.394
        self.wintable['63o'] = 0.359
        self.wintable['62s'] = 0.375
        self.wintable['62o'] = 0.34
        self.wintable['55'] = 0.603
        self.wintable['54s'] = 0.411
        self.wintable['54o'] = 0.379
        self.wintable['53s'] = 0.393
        self.wintable['53o'] = 0.358
        self.wintable['52s'] = 0.375
        self.wintable['52o'] = 0.339
        self.wintable['44'] = 0.57
        self.wintable['43s'] = 0.38
        self.wintable['43o'] = 0.344
        self.wintable['42s'] = 0.363
        self.wintable['42o'] = 0.325
        self.wintable['33'] = 0.573
        self.wintable['32s'] = 0.351
        self.wintable['32o'] = 0.312
        self.wintable['22'] = 0.503

    def get_winrate(self, hand):
        suit1 = hand[0][0]
        suit2 = hand[1][0]
        card1 = hand[0][1]
        card2 = hand[1][1]
        if card1 == card2:
            return self.wintable[card1+card2]
        if suit1 == suit2:
            hand = card1+card2+'s'
            if hand in self.wintable:
                return self.wintable[hand]
            else:
                hand = card2+card1+'s'
                return self.wintable[hand]
        else:
            hand = card1+card2+'o'
            if hand in self.wintable:
                return self.wintable[hand]
            else:
                hand = card2+card1+'o'
                return self.wintable[hand]