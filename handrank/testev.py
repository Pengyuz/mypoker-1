from card import Card
from deck import Deck
from evaluator import Evaluator

board = [
    Card.new('Ts'),
    Card.new('Td'),
    Card.new('2c')
]
hand = [
    Card.new('Qs'),
    Card.new('Th')
]

evaluator = Evaluator()
print(float((1-evaluator.evaluate(board, hand)*1.0/7462.00)))
