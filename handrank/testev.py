from card import Card
from deck import Deck
from evaluator import Evaluator

board = [
    Card.new('2h'),
    Card.new('Kd'),
    Card.new('Jc')
]
hand = [
    Card.new('Qs'),
    Card.new('Th')
]

evaluator = Evaluator()
print(float((1-evaluator.evaluate(board, hand)*1.0/7462.00)))
