from pypokerengine.players import BasePokerPlayer
from pypokerengine.utils.card_utils import gen_cards, estimate_hole_card_win_rate
import copy
from random import shuffle
import pprint
import itertools
import numpy as np
import timeit


class TestPlayer(BasePokerPlayer):

    def __init__(self):
        self.my_stack = 1000
        self.weights = {'strength': 1.799987449308683, 'ps': 1, 'raiseNo': 1}

    def setWeights(self, new_weights):
        self.weights = new_weights

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
            proba_distri = [0.33, 0.33, 0.33]  # oppo model
            for child in node.children:
                q_list.append(self.expectiminimax(child))
            q = sum([i * j for i, j in zip(q_list, proba_distri)])
        elif node.type == 'nature':
            q = 0
            for child in node.children:
                # All children are equally probable
                q += len(node.children) ** -1 * self.expectiminimax(child)
        node.set_value(q)
        return q

    def add_nature_node_children(self, nature_node, depth):
        '''
        append chldren of this nature_node
        '''
        game_state = nature_node.game_state
        if game_state['street'] != 'river':
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
            for card1 in visible_cards:
                all_cards.remove(card1)

            sample = np.random.choice(all_cards, size=5, replace=False)
            for card in sample:
                new_game_state = copy.deepcopy(game_state)
                new_game_state['community_card'].append(card)
                nature_node.add_child(TreeNode([], self.evaluate(new_game_state), "nature_child", None))
        else:
            nature_node.add_child(TreeNode([], self.evaluate(game_state), "nature_child", None))

    def evaluate(self, game_state):
        '''
        evaluation function for cut off nodes
        '''
        hole_card = gen_cards(game_state['my_hole_card'])
        community_card = gen_cards(game_state['community_card'])
        pot = game_state['pot']
        strength = getRank(hole_card, community_card)
        stack = self.my_stack
        raiseNo = self.compute_oppo_raisetime(game_state)
        result = strength * self.weights['strength'] - (pot / 2.0) / (stack+1) * self.weights['ps'] + raiseNo * \
                 self.weights['raiseNo']

        return (1-result/(7462*self.weights['strength']))*pot

    def compute_oppo_raisetime(self, game_state):
        action_history = game_state['action_histories']
        count = 0
        for hists in action_history.values():
            for hist in hists:
                if hist['uuid'] != self.uuid and hist['action'] == 'RAISE':
                    count += 1
        return count

    def construct_tree(self, game_state, depth, raise_time):

        if game_state["turn"] == "me":

            node = TreeNode([], 0, "self", game_state)
            if depth == 5:
                node.set_value(self.evaluate(game_state))
                return node

            my_bet = game_state["my_bet"]
            oppo_bet = game_state["oppo_bet"]
            for action in game_state["valid_actions"]:

                if action["action"] == "fold":

                    node.add_child(TreeNode([], -game_state["my_bet"], "fold", None))

                elif action["action"] == "raise":

                    new_game_state = copy.deepcopy(game_state)
                    new_game_state["turn"] = "oppo"
                    new_game_state["pot"] = new_game_state["pot"] + oppo_bet + 10 - my_bet
                    new_game_state["my_bet"] = new_game_state["my_bet"] + oppo_bet + 10 - my_bet

                    if raise_time == 4:
                        new_valid_actions = [{"action": "fold"}, {"action": "call"}]
                    else:
                        new_valid_actions = [{"action": "fold"}, {"action": "call"}, {"action": "raise"}]

                    new_game_state["valid_actions"] = new_valid_actions
                    node.add_child(self.construct_tree(new_game_state, depth + 1, raise_time + 1))

                elif action["action"] == "call":

                    if my_bet == oppo_bet:
                        nature_node = TreeNode([], 0, "nature", game_state)
                        node.add_child(nature_node)
                        self.add_nature_node_children(nature_node, depth)
                    else:
                        new_game_state = copy.deepcopy(game_state)
                        new_game_state["turn"] = "oppo"
                        new_game_state["pot"] = new_game_state["pot"] + 10
                        new_game_state["my_bet"] = new_game_state["my_bet"] + 10

                        if raise_time == 4:
                            new_valid_actions = [{"action": "fold"}, {"action": "call"}]
                        else:
                            new_valid_actions = [{"action": "fold"}, {"action": "call"}, {"action": "raise"}]

                        new_game_state["valid_actions"] = new_valid_actions
                        node.add_child(self.construct_tree(new_game_state, depth + 1, raise_time))

            return node

        else:
            node = TreeNode([], 0, "oppo", game_state)
            if depth == 5:
                node.set_value(self.evaluate(game_state))
                return node

            my_bet = game_state["my_bet"]
            oppo_bet = game_state["oppo_bet"]
            for action in game_state["valid_actions"]:

                if action["action"] == "fold":

                    node.add_child(TreeNode([], game_state["oppo_bet"], "fold", None))

                elif action["action"] == "raise":

                    new_game_state = copy.deepcopy(game_state)
                    new_game_state["turn"] = "me"
                    new_game_state["pot"] = new_game_state["pot"] + my_bet + 10 - oppo_bet
                    new_game_state["oppo_bet"] = new_game_state["oppo_bet"] + my_bet + 10 - oppo_bet

                    if raise_time == 4:
                        new_valid_actions = [{"action": "fold"}, {"action": "call"}]
                    else:
                        new_valid_actions = [{"action": "fold"}, {"action": "call"}, {"action": "raise"}]

                    new_game_state["valid_actions"] = new_valid_actions
                    node.add_child(self.construct_tree(new_game_state, depth + 1, raise_time + 1))

                elif action["action"] == "call":

                    if my_bet == oppo_bet:
                        nature_node = TreeNode([], 0, "nature", game_state)
                        node.add_child(nature_node)
                        self.add_nature_node_children(nature_node, depth)
                    else:
                        new_game_state = copy.deepcopy(game_state)
                        new_game_state["turn"] = "me"
                        new_game_state["pot"] = new_game_state["pot"] + 10
                        new_game_state["oppo_bet"] = new_game_state["oppo_bet"] + 10

                        if raise_time == 4:
                            new_valid_actions = [{"action": "fold"}, {"action": "call"}]
                        else:
                            new_valid_actions = [{"action": "fold"}, {"action": "call"}, {"action": "raise"}]

                        new_game_state["valid_actions"] = new_valid_actions
                        node.add_child(self.construct_tree(new_game_state, depth + 1, raise_time))

            return node

    #  we define the logic to make an action through this method. (so this method would be the core of your AI)
    def declare_action(self, valid_actions, hole_card, round_state):

        game_state = self.build_game_state(valid_actions, hole_card, round_state)
        pp = pprint.PrettyPrinter(indent=2)
        # pp.pprint(hole_card)
        # pp.pprint(valid_actions)
        # print("------------ROUND_STATE(testpalyer)--------")
        # pp.pprint(round_state)
        # print("------------GAME_STATE(testpalyer)--------")
        # pp.pprint(game_state)
        # print("my stack:" + str(self.my_stack))

        if round_state['street'] == 'preflop':
            start = timeit.timeit()
            winrate = PreFlopWinTable().get_winrate(hole_card)
            if winrate <= 0.35:  # fold
                call_action_info = valid_actions[0]
            elif winrate >= 0.6 and len(valid_actions) == 3:  # raise
                call_action_info = valid_actions[2]
            else:  # call
                call_action_info = valid_actions[1]
            action = call_action_info["action"]
            end = timeit.timeit()
            #print((end - start)*1000)
            return action
        else:
            start1 = timeit.timeit()
            start_node = self.construct_tree(game_state, 1, 0)
            self.expectiminimax(start_node)
            res = []
            for child in start_node.children:
                res.append(child.value)
            #print(res)
            index = res.index(max(res))
            action = valid_actions[index]["action"]
            end1 = timeit.timeit()
            #print((end1-start1)*1000)
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
        self.wintable['82o'] = 0.368
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
            return self.wintable[card1 + card2]
        if suit1 == suit2:
            hand = card1 + card2 + 's'
            if hand in self.wintable:
                return self.wintable[hand]
            else:
                hand = card2 + card1 + 's'
                return self.wintable[hand]
        else:
            hand = card1 + card2 + 'o'
            if hand in self.wintable:
                return self.wintable[hand]
            else:
                hand = card2 + card1 + 'o'
                return self.wintable[hand]


# ---------------------------------------------------------------------------------------
def getRank(hole, community):
    hole_new = convertCard(hole)
    community_new = convertCard(community)
    evaluate = Evaluator()
    marks = evaluate.evaluate(hole_new, community_new)
    return marks


def convertCard(cards=[]):
    # C D H S
    result = []
    for ele in cards:
        ele = str(ele)
        a = str(ele[0]).lower()
        b = ele[1]
        result.append(Card.new(b + a))
    return result


# --------------------------------------------------------------------------------------- evaluation method
# card class

class Card():
    STR_RANKS = '23456789TJQKA'
    INT_RANKS = range(13)
    PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41]

    # converstion from string => int
    CHAR_RANK_TO_INT_RANK = dict(zip(list(STR_RANKS), INT_RANKS))
    CHAR_SUIT_TO_INT_SUIT = {
        's': 1,  # spades
        'h': 2,  # hearts
        'd': 4,  # diamonds
        'c': 8,  # clubs
    }
    INT_SUIT_TO_CHAR_SUIT = 'xshxdxxxc'

    # for pretty printing
    PRETTY_SUITS = {
        1: u"\u2660".encode('utf-8'),  # spades
        2: u"\u2764".encode('utf-8'),  # hearts
        4: u"\u2666".encode('utf-8'),  # diamonds
        8: u"\u2663".encode('utf-8')  # clubs
    }

    # hearts and diamonds
    PRETTY_REDS = [2, 4]

    @staticmethod
    def new(string):
        """
        Converts Card string to binary integer representation of card, inspired by:

        http://www.suffecool.net/poker/evaluator.html
        """

        rank_char = string[0]
        suit_char = string[1]
        rank_int = Card.CHAR_RANK_TO_INT_RANK[rank_char]
        suit_int = Card.CHAR_SUIT_TO_INT_SUIT[suit_char]
        rank_prime = Card.PRIMES[rank_int]

        bitrank = 1 << rank_int << 16
        suit = suit_int << 12
        rank = rank_int << 8

        return bitrank | suit | rank | rank_prime

    @staticmethod
    def int_to_str(card_int):
        rank_int = Card.get_rank_int(card_int)
        suit_int = Card.get_suit_int(card_int)
        return Card.STR_RANKS[rank_int] + Card.INT_SUIT_TO_CHAR_SUIT[suit_int]

    @staticmethod
    def get_rank_int(card_int):
        return (card_int >> 8) & 0xF

    @staticmethod
    def get_suit_int(card_int):
        return (card_int >> 12) & 0xF

    @staticmethod
    def get_bitrank_int(card_int):
        return (card_int >> 16) & 0x1FFF

    @staticmethod
    def get_prime(card_int):
        return card_int & 0x3F

    @staticmethod
    def hand_to_binary(card_strs):
        """
        Expects a list of cards as strings and returns a list
        of integers of same length corresponding to those strings.
        """
        bhand = []
        for c in card_strs:
            bhand.append(Card.new(c))
        return bhand

    @staticmethod
    def prime_product_from_hand(card_ints):
        """
        Expects a list of cards in integer form.
        """

        product = 1
        for c in card_ints:
            product *= (c & 0xFF)

        return product

    @staticmethod
    def prime_product_from_rankbits(rankbits):
        """
        Returns the prime product using the bitrank (b)
        bits of the hand. Each 1 in the sequence is converted
        to the correct prime and multiplied in.
        Params:
            rankbits = a single 32-bit (only 13-bits set) integer representing
                    the ranks of 5 _different_ ranked cards
                    (5 of 13 bits are set)
        Primarily used for evaulating flushes and straights,
        two occasions where we know the ranks are *ALL* different.
        Assumes that the input is in form (set bits):
                              rankbits
                        +--------+--------+
                        |xxxbbbbb|bbbbbbbb|
                        +--------+--------+
        """
        product = 1
        for i in Card.INT_RANKS:
            # if the ith bit is set
            if rankbits & (1 << i):
                product *= Card.PRIMES[i]

        return product

    @staticmethod
    def int_to_binary(card_int):
        """
        For debugging purposes. Displays the binary number as a
        human readable string in groups of four digits.
        """
        bstr = bin(card_int)[2:][::-1]  # chop off the 0b and THEN reverse string
        output = list("".join(["0000" + "\t"] * 7) + "0000")

        for i in range(len(bstr)):
            output[i + int(i / 4)] = bstr[i]

        # output the string to console
        output.reverse()
        return "".join(output)

    @staticmethod
    def int_to_pretty_str(card_int):
        """
        Prints a single card
        """

        color = False
        try:
            from termcolor import colored
            ### for mac, linux: http://pypi.python.org/pypi/termcolor
            ### can use for windows: http://pypi.python.org/pypi/colorama
            color = True
        except ImportError:
            pass

        # suit and rank
        suit_int = Card.get_suit_int(card_int)
        rank_int = Card.get_rank_int(card_int)

        # if we need to color red
        s = Card.PRETTY_SUITS[suit_int]
        if color and suit_int in Card.PRETTY_REDS:
            s = colored(s, "red")

        r = Card.STR_RANKS[rank_int]

        return " [ " + r + " " + s + " ] "

    @staticmethod
    def print_pretty_card(card_int):
        """
        Expects a single integer as input
        """
        print(Card.int_to_pretty_str(card_int))

    @staticmethod
    def print_pretty_cards(card_ints):
        """
        Expects a list of cards in integer form.
        """
        output = " "
        for i in range(len(card_ints)):
            c = card_ints[i]
            if i != len(card_ints) - 1:
                output += Card.int_to_pretty_str(c) + ","
            else:
                output += Card.int_to_pretty_str(c) + " "

        print(output)


# -----------------------------------------------------------------------
# deck class
class Deck:
    """
    Class representing a deck. The first time we create, we seed the static
    deck with the list of unique card integers. Each object instantiated simply
    makes a copy of this object and shuffles it.
    """
    _FULL_DECK = []

    def __init__(self):
        self.shuffle()

    def shuffle(self):
        # and then shuffle
        self.cards = Deck.GetFullDeck()
        shuffle(self.cards)

    def draw(self, n=1):
        if n == 1:
            return self.cards.pop(0)

        cards = []
        for i in range(n):
            cards.append(self.draw())
        return cards

    def __str__(self):
        return Card.print_pretty_cards(self.cards)

    @staticmethod
    def GetFullDeck():
        if Deck._FULL_DECK:
            return list(Deck._FULL_DECK)

        # create the standard 52 card deck
        for rank in Card.STR_RANKS:
            for suit, val in Card.CHAR_SUIT_TO_INT_SUIT.iteritems():
                Deck._FULL_DECK.append(Card.new(rank + suit))

        return list(Deck._FULL_DECK)


# ------------------------------------------------------------------------
# evaluator class
class Evaluator(object):
    """
    Evaluates hand strengths using a variant of Cactus Kev's algorithm:
    http://suffe.cool/poker/evaluator.html
    I make considerable optimizations in terms of speed and memory usage,
    in fact the lookup table generation can be done in under a second and
    consequent evaluations are very fast. Won't beat C, but very fast as
    all calculations are done with bit arithmetic and table lookups.
    """

    def __init__(self):

        self.table = LookupTable()

        self.hand_size_map = {
            5: self._five,
            6: self._six,
            7: self._seven
        }

    def evaluate(self, cards, board):
        """
        This is the function that the user calls to get a hand rank.
        Supports empty board, etc very flexible. No input validation
        because that's cycles!
        """
        all_cards = cards + board
        return self.hand_size_map[len(all_cards)](all_cards)

    def _five(self, cards):
        """
        Performs an evalution given cards in integer form, mapping them to
        a rank in the range [1, 7462], with lower ranks being more powerful.
        Variant of Cactus Kev's 5 card evaluator, though I saved a lot of memory
        space using a hash table and condensing some of the calculations.
        """
        # if flush
        if cards[0] & cards[1] & cards[2] & cards[3] & cards[4] & 0xF000:
            handOR = (cards[0] | cards[1] | cards[2] | cards[3] | cards[4]) >> 16
            prime = Card.prime_product_from_rankbits(handOR)
            return self.table.flush_lookup[prime]

        # otherwise
        else:
            prime = Card.prime_product_from_hand(cards)
            return self.table.unsuited_lookup[prime]

    def _six(self, cards):
        """
        Performs five_card_eval() on all (6 choose 5) = 6 subsets
        of 5 cards in the set of 6 to determine the best ranking,
        and returns this ranking.
        """
        minimum = LookupTable.MAX_HIGH_CARD

        all5cardcombobs = itertools.combinations(cards, 5)
        for combo in all5cardcombobs:

            score = self._five(combo)
            if score < minimum:
                minimum = score

        return minimum

    def _seven(self, cards):
        """
        Performs five_card_eval() on all (7 choose 5) = 21 subsets
        of 5 cards in the set of 7 to determine the best ranking,
        and returns this ranking.
        """
        minimum = LookupTable.MAX_HIGH_CARD

        all5cardcombobs = itertools.combinations(cards, 5)
        for combo in all5cardcombobs:

            score = self._five(combo)
            if score < minimum:
                minimum = score

        return minimum

    def get_rank_class(self, hr):
        """
        Returns the class of hand given the hand hand_rank
        returned from evaluate.
        """
        if hr >= 0 and hr <= LookupTable.MAX_STRAIGHT_FLUSH:
            return LookupTable.MAX_TO_RANK_CLASS[LookupTable.MAX_STRAIGHT_FLUSH]
        elif hr <= LookupTable.MAX_FOUR_OF_A_KIND:
            return LookupTable.MAX_TO_RANK_CLASS[LookupTable.MAX_FOUR_OF_A_KIND]
        elif hr <= LookupTable.MAX_FULL_HOUSE:
            return LookupTable.MAX_TO_RANK_CLASS[LookupTable.MAX_FULL_HOUSE]
        elif hr <= LookupTable.MAX_FLUSH:
            return LookupTable.MAX_TO_RANK_CLASS[LookupTable.MAX_FLUSH]
        elif hr <= LookupTable.MAX_STRAIGHT:
            return LookupTable.MAX_TO_RANK_CLASS[LookupTable.MAX_STRAIGHT]
        elif hr <= LookupTable.MAX_THREE_OF_A_KIND:
            return LookupTable.MAX_TO_RANK_CLASS[LookupTable.MAX_THREE_OF_A_KIND]
        elif hr <= LookupTable.MAX_TWO_PAIR:
            return LookupTable.MAX_TO_RANK_CLASS[LookupTable.MAX_TWO_PAIR]
        elif hr <= LookupTable.MAX_PAIR:
            return LookupTable.MAX_TO_RANK_CLASS[LookupTable.MAX_PAIR]
        elif hr <= LookupTable.MAX_HIGH_CARD:
            return LookupTable.MAX_TO_RANK_CLASS[LookupTable.MAX_HIGH_CARD]
        else:
            raise Exception("Inavlid hand rank, cannot return rank class")

    def class_to_string(self, class_int):
        """
        Converts the integer class hand score into a human-readable string.
        """
        return LookupTable.RANK_CLASS_TO_STRING[class_int]

    def get_five_card_rank_percentage(self, hand_rank):
        """
        Scales the hand rank score to the [0.0, 1.0] range.
        """
        return float(hand_rank) / float(LookupTable.MAX_HIGH_CARD)

    def hand_summary(self, board, hands):
        """
        Gives a sumamry of the hand with ranks as time proceeds.
        Requires that the board is in chronological order for the
        analysis to make sense.
        """

        assert len(board) == 5, "Invalid board length"
        for hand in hands:
            assert len(hand) == 2, "Inavlid hand length"

        line_length = 10
        stages = ["FLOP", "TURN", "RIVER"]

        for i in range(len(stages)):
            line = ("=" * line_length) + " %s " + ("=" * line_length)
            print line % stages[i]

            best_rank = 7463  # rank one worse than worst hand
            winners = []
            for player, hand in enumerate(hands):

                # evaluate current board position
                rank = self.evaluate(hand, board[:(i + 3)])
                rank_class = self.get_rank_class(rank)
                class_string = self.class_to_string(rank_class)
                percentage = 1.0 - self.get_five_card_rank_percentage(rank)  # higher better here
                print ("Player %d hand = %s, percentage rank among all hands = %f" % (
                    player + 1, class_string, percentage))

                # detect winner
                if rank == best_rank:
                    winners.append(player)
                    best_rank = rank
                elif rank < best_rank:
                    winners = [player]
                    best_rank = rank

            # if we're not on the river
            if i != stages.index("RIVER"):
                if len(winners) == 1:
                    print ("Player %d hand is currently winning.\n" % (winners[0] + 1,))
                else:
                    print ("Players %s are tied for the lead.\n" % [x + 1 for x in winners])

            # otherwise on all other streets
            else:
                print
                print ("=" * line_length) + " HAND OVER " + ("=" * line_length)
                if len(winners) == 1:
                    print "Player %d is the winner with a %s\n" % (winners[0] + 1,
                                                                   self.class_to_string(self.get_rank_class(
                                                                       self.evaluate(hands[winners[0]], board))))
                else:
                    print "Players %s tied for the win with a %s\n" % (winners,
                                                                       self.class_to_string(self.get_rank_class(
                                                                           self.evaluate(hands[winners[0]], board))))


# ---------------------------------------------------------------------------------------------------------------------
#  lookup class

class LookupTable(object):
    MAX_STRAIGHT_FLUSH = 10
    MAX_FOUR_OF_A_KIND = 166
    MAX_FULL_HOUSE = 322
    MAX_FLUSH = 1599
    MAX_STRAIGHT = 1609
    MAX_THREE_OF_A_KIND = 2467
    MAX_TWO_PAIR = 3325
    MAX_PAIR = 6185
    MAX_HIGH_CARD = 7462

    MAX_TO_RANK_CLASS = {
        MAX_STRAIGHT_FLUSH: 1,
        MAX_FOUR_OF_A_KIND: 2,
        MAX_FULL_HOUSE: 3,
        MAX_FLUSH: 4,
        MAX_STRAIGHT: 5,
        MAX_THREE_OF_A_KIND: 6,
        MAX_TWO_PAIR: 7,
        MAX_PAIR: 8,
        MAX_HIGH_CARD: 9
    }

    RANK_CLASS_TO_STRING = {
        1: "Straight Flush",
        2: "Four of a Kind",
        3: "Full House",
        4: "Flush",
        5: "Straight",
        6: "Three of a Kind",
        7: "Two Pair",
        8: "Pair",
        9: "High Card"
    }

    def __init__(self):
        """
        Calculates lookup tables
        """
        # create dictionaries
        self.flush_lookup = {}
        self.unsuited_lookup = {}

        # create the lookup table in piecewise fashion
        self.flushes()  # this will call straights and high cards method,
        # we reuse some of the bit sequences
        self.multiples()

    def flushes(self):
        """
        Straight flushes and flushes.
        Lookup is done on 13 bit integer (2^13 > 7462):
        xxxbbbbb bbbbbbbb => integer hand index
        """

        # straight flushes in rank order
        straight_flushes = [
            7936,  # int('0b1111100000000', 2), # royal flush
            3968,  # int('0b111110000000', 2),
            1984,  # int('0b11111000000', 2),
            992,  # int('0b1111100000', 2),
            496,  # int('0b111110000', 2),
            248,  # int('0b11111000', 2),
            124,  # int('0b1111100', 2),
            62,  # int('0b111110', 2),
            31,  # int('0b11111', 2),
            4111  # int('0b1000000001111', 2) # 5 high
        ]

        # now we'll dynamically generate all the other
        # flushes (including straight flushes)
        flushes = []
        gen = self.get_lexographically_next_bit_sequence(int('0b11111', 2))

        # 1277 = number of high cards
        # 1277 + len(str_flushes) is number of hands with all cards unique rank
        for i in range(1277 + len(straight_flushes) - 1):  # we also iterate over SFs
            # pull the nepyxt flush pattern from our generator
            f = next(gen)

            # if this flush matches perfectly any
            # straight flush, do not add it
            notSF = True
            for sf in straight_flushes:
                # if f XOR sf == 0, then bit pattern
                # is same, and we should not add
                if not f ^ sf:
                    notSF = False

            if notSF:
                flushes.append(f)

        # we started from the lowest straight pattern, now we want to start ranking from
        # the most powerful hands, so we reverse
        flushes.reverse()

        # now add to the lookup map:
        # start with straight flushes and the rank of 1
        # since theyit is the best hand in poker
        # rank 1 = Royal Flush!
        rank = 1
        for sf in straight_flushes:
            prime_product = Card.prime_product_from_rankbits(sf)
            self.flush_lookup[prime_product] = rank
            rank += 1

        # we start the counting for flushes on max full house, which
        # is the worst rank that a full house can have (2,2,2,3,3)
        rank = LookupTable.MAX_FULL_HOUSE + 1
        for f in flushes:
            prime_product = Card.prime_product_from_rankbits(f)
            self.flush_lookup[prime_product] = rank
            rank += 1

        # we can reuse these bit sequences for straights
        # and high cards since they are inherently related
        # and differ only by context
        self.straight_and_highcards(straight_flushes, flushes)

    def straight_and_highcards(self, straights, highcards):
        """
        Unique five card sets. Straights and highcards.
        Reuses bit sequences from flush calculations.
        """
        rank = LookupTable.MAX_FLUSH + 1

        for s in straights:
            prime_product = Card.prime_product_from_rankbits(s)
            self.unsuited_lookup[prime_product] = rank
            rank += 1

        rank = LookupTable.MAX_PAIR + 1
        for h in highcards:
            prime_product = Card.prime_product_from_rankbits(h)
            self.unsuited_lookup[prime_product] = rank
            rank += 1

    def multiples(self):
        """
        Pair, Two Pair, Three of a Kind, Full House, and 4 of a Kind.
        """
        backwards_ranks = range(len(Card.INT_RANKS) - 1, -1, -1)

        # 1) Four of a Kind
        rank = LookupTable.MAX_STRAIGHT_FLUSH + 1

        # for each choice of a set of four rank
        for i in backwards_ranks:

            # and for each possible kicker rank
            kickers = backwards_ranks[:]
            kickers.remove(i)
            for k in kickers:
                product = Card.PRIMES[i] ** 4 * Card.PRIMES[k]
                self.unsuited_lookup[product] = rank
                rank += 1

        # 2) Full House
        rank = LookupTable.MAX_FOUR_OF_A_KIND + 1

        # for each three of a kind
        for i in backwards_ranks:

            # and for each choice of pair rank
            pairranks = backwards_ranks[:]
            pairranks.remove(i)
            for pr in pairranks:
                product = Card.PRIMES[i] ** 3 * Card.PRIMES[pr] ** 2
                self.unsuited_lookup[product] = rank
                rank += 1

        # 3) Three of a Kind
        rank = LookupTable.MAX_STRAIGHT + 1

        # pick three of one rank
        for r in backwards_ranks:

            kickers = backwards_ranks[:]
            kickers.remove(r)
            gen = itertools.combinations(kickers, 2)

            for kickers in gen:
                c1, c2 = kickers
                product = Card.PRIMES[r] ** 3 * Card.PRIMES[c1] * Card.PRIMES[c2]
                self.unsuited_lookup[product] = rank
                rank += 1

        # 4) Two Pair
        rank = LookupTable.MAX_THREE_OF_A_KIND + 1

        tpgen = itertools.combinations(backwards_ranks, 2)
        for tp in tpgen:

            pair1, pair2 = tp
            kickers = backwards_ranks[:]
            kickers.remove(pair1)
            kickers.remove(pair2)
            for kicker in kickers:
                product = Card.PRIMES[pair1] ** 2 * Card.PRIMES[pair2] ** 2 * Card.PRIMES[kicker]
                self.unsuited_lookup[product] = rank
                rank += 1

        # 5) Pair
        rank = LookupTable.MAX_TWO_PAIR + 1

        # choose a pair
        for pairrank in backwards_ranks:

            kickers = backwards_ranks[:]
            kickers.remove(pairrank)
            kgen = itertools.combinations(kickers, 3)

            for kickers in kgen:
                k1, k2, k3 = kickers
                product = Card.PRIMES[pairrank] ** 2 * Card.PRIMES[k1] \
                          * Card.PRIMES[k2] * Card.PRIMES[k3]
                self.unsuited_lookup[product] = rank
                rank += 1

    def write_table_to_disk(self, table, filepath):
        """
        Writes lookup table to disk
        """
        with open(filepath, 'w') as f:
            for prime_prod, rank in table.iteritems():
                f.write(str(prime_prod) + "," + str(rank) + '\n')

    def get_lexographically_next_bit_sequence(self, bits):
        """
        Bit hack from here:
        http://www-graphics.stanford.edu/~seander/bithacks.html#NextBitPermutation
        Generator even does this in poker order rank
        so no need to sort when done! Perfect.
        """
        t = (bits | (bits - 1)) + 1
        next = t | ((((t & -t) / (bits & -bits)) >> 1) - 1)
        yield next
        while True:
            t = (next | (next - 1)) + 1
            next = t | ((((t & -t) / (next & -next)) >> 1) - 1)
            yield next
