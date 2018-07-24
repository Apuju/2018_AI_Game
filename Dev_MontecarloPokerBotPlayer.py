import logging
import deuces

class GameCard:
    def __int__(self,
                rank,
                suit
                ):
        self.rank = rank
        self.suit = suit

class Hands:
    def __int__(self,
                cards
                ):
        self.cards = cards

class BetAction:
    def __int__(self,
                hands,
                action,
                amount
                ):
        self.action = action
        self.amount = amount

class Player:
    def __init__(self,
                 name,
                 previousAction,
                 nextAction,
                 isAllIn,
                 isRaise,
                 isFlod,
                 totalBetChips,
                 pocketChips
                 ):
        self.name = name
        self.previousAction = previousAction
        self.nextAction = nextAction
        self.isAllIn = isAllIn
        self.isRaise = isRaise
        self.isFlod = isFlod
        self.totalBetChips = totalBetChips
        self.pocketChips = pocketChips

class Board:
    def __int__(self,
                cards,
                totalChips
                ):
        self.cards = cards
        self.totalChip = totalChips

class GameTable:
    def __int__(self,
                me,
                players,
                board
                ):
        self.me = me
        self.players = players
        self.board = board

class Logger:
    logger = None

    def __init__(self):
        #logging.basicConfig()
        self.logger = logging.getLogger('MontecarloPokerBotPlayer')
        self.logger.setLevel(logging.DEBUG)
        streamHandler = logging.StreamHandler()
        streamHandler.setLevel(logging.INFO)
        streamFormatter = logging.Formatter('%(message)s')
        streamHandler.setFormatter(streamFormatter)
        self.logger.addHandler(streamHandler)
        rotatingFileHandler = logging.handlers.RotatingFileHandler('Debug_TaxHoldem.log', 'a', 2*1024*1024, 10, 'utf-8')
        rotatingFileHandler.setLevel(logging.DEBUG)
        rotatingFileFormatter = logging.Formatter('%(asctime)s:Line%(lineno)s[%(levelname)s]%(funcName)s>>%(message)s')
        rotatingFileHandler.setFormatter((rotatingFileFormatter))
        self.logger.addHandler(rotatingFileHandler)