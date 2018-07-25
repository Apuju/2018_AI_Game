import logging
import logging.handlers
import deuces
import csv
import time
from websocket import create_connection
import json

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

class PokerSocket:
    def __init__(self, logger, connect_url, pokerbot, playerName):
        self.logger = logger
        self.connectUrl = connect_url
        self.pokerbot = pokerbot
        self.playerName = playerName
    def InitVariables(self):
        self.totalPlayers = []
    def GetCard(card):
        card_type = card[1]
        cardnume_code = card[0]
        card_num = 0
        card_num_type = 0
        if card_type == 'S':
            card_num_type = 1
        elif card_type == 'H':
            card_num_type = 2
        elif card_type == 'D':
            card_num_type = 3
        else:
            card_num_type = 4

        if cardnume_code == 'T':
            card_num = 10
        elif cardnume_code == 'J':
            card_num = 11
        elif cardnume_code == 'Q':
            card_num = 12
        elif cardnume_code == 'K':
            card_num = 13
        elif cardnume_code == 'A':
            card_num = 14
        else:
            card_num = int(cardnume_code)

        return Card(card_num, card_num_type)
    def TakeAction(self, action, data):
        self.logger.debug('enter function')
        doActionStop = True
        try:
            self.logger.info('client-server={}'.format(action))
            if action == '__new_round':
                self.myPocketChips = data['table']['initChips']
                self.total_number_players = len(data['players'])
            elif action == '__show_action' or action == '__deal':
                self.board = []
                for card in data['table']['board']:
                    self.board.append(self.GetCard(card))
            elif action == '__action' or action == '__bet':
                event = '__action'
            elif action == '__round_end':
                event = '__action'
            elif action == '__game_over':
                event = '__action'
            elif action == '__game_stop':
                self.logger.info('game has broken')
                doActionStop = False
            elif action == '__last_will':
                self.logger.info('server is off')
                doActionStop = False
            else:
                self.logger.debug('undefined event name')
        except Exception as e:
            self.logger.error(e.message)
            raise
        return  doActionStop
    def DoListen(self):
        self.logger.debug('enter function')
        try:
            self.ws = create_connection(self.connectUrl)
            self.logger.debug('join game')
            self.ws.send(json.dumps({
                "eventName": "__join",
                "data": {
                    "playerName": self.playerName
                }
            }))
            doKeepGoing = True
            while doKeepGoing:
                msg = json.loads(self.ws.recv())
                doKeepGoing = self.TakeAction(msg["eventName"], msg["data"])
            self.logger.info('game server stopped')
            self.logger.info('shut down the connection')
            self.ws.close()
        except Exception as e:
            self.logger.error('exception={}'.format(e.message))
            if hasattr(self, 'ws') and self.ws is not None:
                if isinstance(self.ws, basestring):
                    self.logger.error('self.ws={}'.format(self.ws))
                else:
                    self.logger.info('shut down the connection')
                    self.ws.close()

class MontecarloPokerBot:
    def __init__(self, logger):
        self.logger = logger

if __name__ == '__main__':
    resume_connection_threshold_second = 5

    logger = Logger().logger
    timestamp = str(time.strftime('%Y%m%d%H%M%S', time.localtime()))
    gameMatchResultFile = 'GameMatch_Result_{}.csv'.format(timestamp)
    gameSetResultFile = 'GameSet_Result_{}.csv'.format(timestamp)
    roundActionResultFile = 'GameRound_Action_{}.csv'.format(timestamp)
    try:
        with open(gameMatchResultFile, 'ab') as csvfile:
            spamwriter = csv.writer(csvfile, delimiter=',')
            spamwriter.writerow(['Time',
                                 'MatchCount',
                                 'WinChips',
                                 'TotalWinChips',
                                 'AvgWinChips'])
        with open(gameSetResultFile, 'ab') as csvfile:
            spamwriter = csv.writer(csvfile, delimiter=',')
            spamwriter.writerow(['Time',
                                 'TableNumber',
                                 'WinChips',
                                 'LosedChips',
                                 'AmIFold',
                                 'AmIAllIn',
                                 'MyChips',
                                 'TableChips',
                                 'MyHand',
                                 'EnemyHands'])
        with open(roundActionResultFile, 'ab') as csvfile:
            spamwriter = csv.writer(csvfile, delimiter=',')
            spamwriter.writerow(['Time',
                                 'TableNumber',
                                 'RoundCount',
                                 'RoundName',
                                 'MyAction',
                                 'MyHands',
                                 'BoardCards',
                                 'WillBeAmount',
                                 'MyTotalBet',
                                 'TableBet',
                                 'MyChips',
                                 'PredictedScore',
                                 'PredictedTableOdds',
                                 'PredictedWinRate',
                                 'IsSomebodyAllIn',
                                 'IsTurnRaise',
                                 'IsRiverRaise',
                                 'isFlopRaise',
                                 'PlayerActions'])
    except Exception as e:
        logger.error(e.message)
        raise
    # playerName = "c3b0cc70c2504124998b88d57b7fc0c6"
    playerName = 'icebreaker'
    # playerName = 'icebreaka'
    # connect_url = "ws://poker-battle.vtr.trendnet.org:3001"
    connect_url = 'ws://poker-training.vtr.trendnet.org:3001'
    # connect_url = 'ws://poker-dev.wrs.club:3001'
    trainMode = True
    if trainMode:
        print 'training mode was on'
    myPokerBot = MontecarloPokerBot(logger)
    currentTime = None
    hour = 0
    minute = 0
    myPokerSocket = PokerSocket(logger, connect_url, myPokerBot, playerName)
    while 1:
        currentTime = time.localtime()
        print('now is {}'.format(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())))
        hour = currentTime.tm_hour
        minute = currentTime.tm_min
        if (hour >= 12 and hour < 14) \
                or (hour >= 17 and hour < 20) \
                or trainMode:
            myPokerSocket.DoListen()
        print('wait {} second(s) to resume'.format(str(resume_connection_threshold_second)))
        time.sleep(resume_connection_threshold_second)