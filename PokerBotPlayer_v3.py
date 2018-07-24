#coding=UTF-8
from pokereval.card import Card
#from deuces import Card, Evaluator
from pokereval.hand_evaluator import HandEvaluator
from websocket import create_connection
#import math
import random
import json
#import numpy as np
import time
from sklearn.externals import joblib
import logging
import logging.handlers
import csv

def getCard(card):
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

class Logger(object):
    logger = None

    def __init__(self):
        #logging.basicConfig()
        self.logger = logging.getLogger('Logger')
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

class PokerBot(object):
    def declareAction(self,hole, board, round, my_Raise_Bet, my_Call_Bet, Table_Bet, number_players, raise_count, bet_count,my_Chips,total_bet):
        err_msg = self.__build_err_msg("declare_action")
        raise NotImplementedError(err_msg)
    def game_over(self,isWin,winChips,data):
        err_msg = self.__build_err_msg("game_over")
        raise NotImplementedError(err_msg)

class PokerSocket(object):
    ws = ""
    board = []
    hole = []
    my_Raise_Bet = 0
    my_Call_Bet = 0
    number_players = 0
    total_number_players = 0
    my_Chips=0
    Table_Bet=0
    playerGameName=None
    raise_count=0
    bet_count=0
    total_bet=0
    isSomebodyAllIn = False
    whoAllIn = []
    isTurnRaise = False
    whoTurnRaise = []
    isRiverRaise = False
    whoRiverRaise = []
    isFlopRaise = False
    whoFlopRaise = []
    logger = None
    matchCount = 0
    totalEarnedChips = 0.0
    avgEarnedChips = 0.0
    myPocketChips = 0.0
    gameMatchResultFile = 'GameMatch_Result_{}.csv'.format('')
    gameSetResultFile = 'GameSet_Result_{}.csv'.format('')
    roundActionResultFile = 'GameRound_Action_{}.csv'.format('')
    blindAmount = []

    def __init__(self, playerName, connect_url, pokerbot, logger):
        self.pokerbot=pokerbot
        self.playerName=playerName
        self.connect_url=connect_url
        self.logger = logger

    def getRoundName(self, roundName, board):
        self.logger.debug('enter function, roundName={}, board={}'.format(roundName, board))
        if len(board) == 0:
            return 'preflop'
        elif len(board) == 3:
            return 'flop'
        else:
            return roundName.lower()

    def getAction(self, event, data):
        self.logger.debug('enter function')
        round = self.getRoundName(data['game']['roundName'], self.board)
        self.logger.info('round name={}'.format(round))
        self.my_Chips = data['self']['chips']
        hands = data['self']['cards']
        self.raise_count = data['game']['raiseCount']
        self.bet_count = data['game']['betCount']
        self.playerGameName=data['self']['playerName']
        self.my_Call_Bet = data['self']['minBet']
        #self.my_Raise_Bet = int(self.my_Chips / 4)
        self.my_Raise_Bet = self.my_Call_Bet * 2.0
        self.hole = []
        for card in (hands):
            self.hole.append(getCard(card))
        self.logger.debug('my Chips:{}, my Hands:{}'.format(str(self.my_Chips), str(self.hole)))
        self.logger.debug('table bet={}, current call bet={}, current raise bet={}'.format(str(self.Table_Bet), str(self.my_Call_Bet), str(self.my_Raise_Bet)))
        # aggresive_Tight = PokerBotPlayer(preflop_threshold_Tight, aggresive_threshold)
        # tightAction, tightAmount = aggresive_Tight.declareAction(hole, board, round, my_Raise_Bet, my_Call_Bet,Table_Bet,number_players)
        self.pokerbot.isSomebodyAllIn = self.isSomebodyAllIn
        self.pokerbot.whoAllIn = self.whoAllIn
        self.pokerbot.isRiverRaise = self.isRiverRaise
        self.pokerbot.whoRiverRaise = self.whoRiverRaise
        self.pokerbot.isTurnRaise = self.isTurnRaise
        self.pokerbot.whoTurnRaise = self.whoTurnRaise
        self.pokerbot.isFlopRaise = self.isFlopRaise
        self.pokerbot.whoFlopRaise = self.whoFlopRaise
        self.pokerbot.total_number_players = self.total_number_players
        self.logger.debug('isSomebodyAllIn={}, isRiverRaise={}, isTurnRaise={}, isFlopRaise={}, blindAmount={}'.format(str(self.isSomebodyAllIn), str(self.isRiverRaise), str(self.isTurnRaise), str(self.isFlopRaise), ', '.join(str(amount) for amount in self.blindAmount)))
        action, amount = self.pokerbot.declareAction(self.hole, self.board, round, self.my_Raise_Bet, self.my_Call_Bet, self.Table_Bet, self.number_players, self.raise_count, self.bet_count, self.my_Chips, self.total_bet, event, self.blindAmount)
        return action, amount

    def takeAction(self, action, data):
        self.logger.debug('enter function')
        doActionStop = True
        try:
            self.logger.info('client-server={}'.format(action))
            if action == '__new_round':
                self.myPocketChips = data['table']['initChips']
                self.total_number_players = len(data['players'])
                self.logger.debug('init Chips={}'.format(float(self.myPocketChips)))
            elif action == '__show_action' or action == '__deal':
                self.board = []
                for card in data['table']['board']:
                    self.board.append(getCard(card))
                self.Table_Bet = data['table']['totalBet']
                self.logger.debug('Table Bet:{}'.format(str(self.Table_Bet)))

                currentPlayers = []
                for player in data['players']:
                    if (player['isSurvive'] and not player['folded']):
                        currentPlayers.append(player)
                self.number_players = len(currentPlayers)
                #observe player
                if action != '__deal':
                    if data['action']['action'].lower() == 'allin':
                        if len(self.whoAllIn) == 0:
                            self.isSomebodyAllIn = True
                        if data['action']['playerName'] not in self.whoAllIn:
                            self.whoAllIn.append(data['action']['playerName'])
                    elif data['action']['action'].lower() == 'raise':
                        if self.getRoundName(data['table']['roundName'], self.board) == 'flop':
                            if len(self.whoFlopRaise) == 0:
                                self.isFlopRaise = True
                            if data['action']['playerName'] not in self.whoFlopRaise:
                                self.whoFlopRaise.append(data['action']['playerName'])
                        elif self.getRoundName(data['table']['roundName'], self.board) == 'turn':
                            if len(self.whoTurnRaise) == 0:
                                self.isTurnRaise = True
                            if data['action']['playerName'] not in self.whoTurnRaise:
                                self.whoTurnRaise.append(data['action']['playerName'])
                        elif self.getRoundName(data['table']['roundName'], self.board) == 'river':
                            if len(self.whoRiverRaise) == 0:
                                self.isRiverRaise = True
                            if data['action']['playerName'] not in self.whoRiverRaise:
                                self.whoRiverRaise.append(data['action']['playerName'])
                    elif data['action']['action'].lower() == 'fold':
                        if data['action']['playerName'] in self.whoFlopRaise:
                            self.whoFlopRaise.remove(data['action']['playerName'])
                        if data['action']['playerName'] in self.whoTurnRaise:
                            self.whoTurnRaise.remove(data['action']['playerName'])
                        if data['action']['playerName'] in self.whoRiverRaise:
                            self.whoRiverRaise.remove(data['action']['playerName'])
                        if data['action']['playerName'] in self.whoAllIn:
                            self.whoAllIn.remove(data['action']['playerName'])

                    self.logger.info('number_players:{}, player action={}'.format(str(self.number_players), data['action']))
                    self.logger.debug('isTurnRaise={}, whoTurnRaise={}, isRiverRaise={}, whoRiverRaise={}, isSomebodyAllIn={}, whoAllIn={}'.format(str(self.isTurnRaise), self.whoTurnRaise, str(self.isRiverRaise), self.whoRiverRaise, str(self.isSomebodyAllIn), self.whoAllIn))
            elif action == '__action' or action == '__bet':
                event = '__action'
                if action == '__bet':
                    event = '__bet'
                # blind bet
                if len(self.blindAmount) == 0:
                    self.blindAmount = [0, 0]
                    if data['game']['smallBlind']['playerName'] == self.playerGameName:
                        self.blindAmount[0] = data['game']['smallBlind']['amount']
                    if data['game']['bigBlind']['playerName'] == self.playerGameName:
                        self.blindAmount[1] = data['game']['bigBlind']['amount']
                action, amount = self.getAction(event, data)
                self.ws.send(json.dumps({
                    "eventName": "__action",
                    "data": {
                        "action": action,
                        "playerName": self.playerName,
                        "amount": amount
                    }}))
                self.total_bet += amount
                tableNumber = data['tableNumber']
                self.board = []
                for card in data['game']['board']:
                    self.board.append(getCard(card))
                round = self.getRoundName(data['game']['roundName'], self.board)
                myChips = data['self']['chips']
                self.logger.info("round={}, action={}, hands={}, amount={}, board={}, myChips={}".format(round, action, data['self']['cards'], amount, self.board, myChips))
                roundCount = data['game']['roundCount']
                playerActions = []
                for player in data['game']['players']:
                    playerid = player['playerName']
                    if (player['isSurvive'] and playerid != self.playerGameName):
                        playerActions.append('isFold={};isAllIn={}'.format(player['folded'], player['allIn']))
                with open(self.roundActionResultFile, 'ab') as csvfile:
                    spamwriter = csv.writer(csvfile, delimiter=',')
                    spamwriter.writerow([time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
                                         str(tableNumber),
                                         str(roundCount),
                                         round,
                                         action,
                                         ', '.join(str(card) for card in data['self']['cards']),
                                         ', '.join(str(card) for card in data['game']['board']),
                                         str(amount),
                                         str(self.total_bet),
                                         str(self.Table_Bet),
                                         str(myChips),
                                         self.pokerbot.predictedScore,
                                         self.pokerbot.predictedTableOdds,
                                         self.pokerbot.predictedWinRate,
                                         str(self.isSomebodyAllIn),
                                         str(self.isTurnRaise),
                                         str(self.isRiverRaise),
                                         str(self.isFlopRaise),
                                         ', '.join(str(hand) for hand in playerActions)])
            elif action == '__round_end':
                self.total_bet = 0
                players=data['players']
                isWin=False
                myWinChips=0
                tableChips=0
                playerHands = []
                myHand=''
                amIFold = False
                amIAllIn = False
                myChips = 0
                tableNumber = data['table']['tableNumber']
                self.isSomebodyAllIn = False
                self.whoAllIn = []
                self.isTurnRaise = False
                self.whoTurnRaise = []
                self.isRiverRaise = False
                self.whoRiverRaise = []
                self.isFlopRaise = False
                self.whoFlopRaise = []
                self.board = []
                self.blindAmount = []
                for player in players:
                    winMoney = player['winMoney']
                    isFold = player['folded']
                    isAllIn = player['allIn']
                    if (winMoney > 0):
                        tableChips = winMoney
                    playerid=player['playerName']
                    #self.logger.debug(player)
                    if (self.playerGameName == playerid):
                        myChips = player['chips']
                        if (winMoney == 0):
                            isWin = False
                        else:
                            isWin = True
                        myWinChips = float(winMoney)
                        myHand=player['hand']['message']
                        amIFold = isFold
                        amIAllIn = isAllIn
                    else:
                        if (player['isSurvive']):
                            playerHands.append('{}:isFold={};isAllIn={}'.format(player['hand']['message'], str(isFold), str(isAllIn)))
                myLosedChips = 0.0
                if self.myPocketChips > myChips:
                    myLosedChips = self.myPocketChips - myChips
                    self.myPocketChips = myChips
                else:
                    self.myPocketChips += float(myWinChips)
                self.logger.info('round set finished')
                with open(self.gameSetResultFile, 'ab') as csvfile:
                    spamwriter = csv.writer(csvfile, delimiter=',')
                    enemyHands = format(', '.join(str(hand) for hand in playerHands))
                    spamwriter.writerow([time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
                                         str(tableNumber),
                                         str(myWinChips),
                                         str(myLosedChips),
                                         str(amIFold),
                                         str(amIAllIn),
                                         str(myChips),
                                         str(tableChips),
                                         myHand,
                                         enemyHands])
                self.pokerbot.game_over(isWin, myWinChips, data)
            elif action == '__game_over':
                self.logger.info('game match over')
                self.matchCount += 1
                self.logger.debug('data={}'.format(data))
                for player in data['players']:
                    if (self.playerGameName == player['playerName']):
                        self.totalEarnedChips += float(player['chips'])
                        self.avgEarnedChips = self.totalEarnedChips / float(self.matchCount)
                        break
                self.logger.info('total my earned chips={}, average my earned chips={} with {} matches'.format(str(self.totalEarnedChips), str(self.avgEarnedChips), str(self.matchCount)))
                with open(self.gameMatchResultFile, 'ab') as csvfile:
                    spamwriter = csv.writer(csvfile, delimiter=',')
                    spamwriter.writerow([time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
                                         self.matchCount,
                                         player['chips'],
                                         self.totalEarnedChips,
                                         str(self.avgEarnedChips)])
                time.sleep(5)
                self.logger.info('try to join game match')
                self.ws.send(json.dumps({
                    "eventName": "__join",
                    "data": {
                        "playerName": self.playerName
                    }
                }))
            elif action == '__game_stop':
                doActionStop = False
        except Exception as e:
            self.logger.error(e.message)
            raise
        return  doActionStop

    def doListen(self):
        self.logger.debug('enter function')
        try:
            self.ws = create_connection(self.connect_url)
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
                doKeepGoing = self.takeAction(msg["eventName"], msg["data"])
            self.logger.info('game server stopped')
            self.logger.info('shut down the connection')
            self.ws.close()
        except Exception as e:
            self.logger.error('exception={}'.format(e.message))
            if self.ws is not None:
                if isinstance(self.ws, basestring):
                    self.logger.error('self.ws={}'.format(self.ws))
                else:
                    self.logger.info('shut down the connection')
                    self.ws.close()

class PotOddsPokerBot(PokerBot):

    predictedScore = 0
    predictedTableOdds = 0
    predictedWinRate = 0
    isSomebodyAllIn = False
    whoAllIn = []
    isTurnRaise = False
    whoTurnRaise = []
    isRiverRaise = False
    whoRiverRaise = []
    isFlopRaise = False
    whoFlopRaise = []
    logger = None
    total_number_players = 0
    haveIRaised = False
    previousMyAction = ''
    previouspredictedScore = 0.0
    totalTableChips = 0.0
    totalMyBetChips = 0.0
    myMinCallChips = 0.0
    myRaiseChips = 0.0

    def __init__(self, preflop_tight_loose_threshold, aggresive_passive_threshold, bet_tolerance, logger):
        self.preflop_tight_loose_threshold = preflop_tight_loose_threshold
        self.aggresive_passive_threshold=aggresive_passive_threshold
        self.bet_tolerance=bet_tolerance
        self.logger = logger

    def game_over(self, isWin, winChips, data):
        self.logger.debug('enter function')
        self.logger.info("game set over")
        self.isSomebodyAllIn = False
        self.whoAllIn = []
        self.isTurnRaise = False
        self.whoTurnRaise = []
        self.isRiverRaise = False
        self.whoRiverRaise = []
        self.isFlopRaise = False
        self.whoFlopRaise = []
        self.total_number_players = 0
        self.haveIRaised = False
        self.logger.debug('win chips={}, response data={}'.format(str(winChips), data))

    def isSomeoneComboRaise(self):
        #The one's rank would be high
        if self.isTurnRaise and self.isRiverRaise:
            for player in self.whoRiverRaise:
                if player in self.whoTurnRaise:
                    return True
        if self.isFlopRaise and self.isTurnRaise:
            for player in self.isTurnRaise:
                if player in self.isFlopRaise:
                    return True
        return False

    def getCardID(self,card):
        rank=card.rank
        suit=card.suit
        suit=suit-1
        id=(suit*13)+rank
        return id

    def genCardFromId(self,cardID):
        if int(cardID)>13:
            rank=int(cardID)%13
            if rank==0:
                suit=int((int(cardID)-rank)/13)
            else:
                suit = int((int(cardID) - rank) / 13) + 1

            if(rank==0):
                rank=14
            else:
                rank+=1
            return Card(rank,suit)
        else:
            suit=1
            rank=int(cardID)
            if (rank == 0):
                rank = 14
            else:
                rank+=1
            return Card(rank,suit)

    def _pick_unused_card(self, card_num, used_card):
        used = [self.getCardID(card) for card in used_card]
        unused = [card_id for card_id in range(1, 53) if card_id not in used]
        choiced = random.sample(unused, card_num)
        return [self.genCardFromId(card_id) for card_id in choiced]

    def get_win_prob(self, hand_cards, board_cards, simulation_number, num_players):
        win = 0
        round=0
        evaluator = HandEvaluator()
        for i in range(simulation_number):

            board_cards_to_draw = 5 - len(board_cards)  # 2
            board_sample = board_cards + self._pick_unused_card(board_cards_to_draw, board_cards + hand_cards)
            unused_cards = self._pick_unused_card((num_players - 1)*2, hand_cards + board_sample)
            opponents_hole = [unused_cards[2 * i:2 * i + 2] for i in range(num_players - 1)]
            temp = []

            try:
                for hole in opponents_hole:
                    temp = hole + board_sample
                    opponents_score = pow(evaluator.evaluate_hand(hole, board_sample), num_players)
                #opponents_score = [pow(evaluator.evaluate_hand(hole, board_sample), num_players) for hole in opponents_hole]
                # hand_sample = self._pick_unused_card(2, board_sample + hand_cards)
                my_rank = pow(evaluator.evaluate_hand(hand_cards, board_sample), num_players)
                if my_rank > max(opponents_score):
                    win += 1
                elif my_rank == max(opponents_score):
                    win += 0.5
                #rival_rank = evaluator.evaluate_hand(hand_sample, board_sample)
                round += 1
            except Exception, e:
                self.logger.error('exception={}, temp={}'.format(e.message, temp))
                continue
        # The large rank value means strong hand card
        print hand_cards
        print board_cards
        print num_players
        print "Win:{}".format(win)
        win_prob = win / float(round)
        print "win_prob:{}".format(win_prob)
        return win_prob

    def calcTableOdds(self, my_Next_Bet, total_my_bet, table_bet):
        self.logger.debug('enter function')
        if my_Next_Bet + table_bet == 0:
            return 0
        else:
            return (my_Next_Bet + total_my_bet) / float(my_Next_Bet + table_bet)

    def declareBet(self, round, action, amount, blindAmount):
        isSmallBlindBetPlayer = False
        isBigBlindBetPlayer = False
        betOdds = 0.0
        if blindAmount[0] > 0:
            isSmallBlindBetPlayer = True
        if blindAmount[1] > 0:
            isBigBlindBetPlayer = True

        if isBigBlindBetPlayer or isSmallBlindBetPlayer:
            if action == 'fold':
                action == 'check'
            elif action == 'call':
                thinking = True
                minusBet = 0
                while thinking:
                    minusBet -= 10
                    if self.myRaiseChips - minusBet > 0:
                        betOdds = self.calcTableOdds(self.myRaiseChips - minusBet, self.totalMyBetChips, self.totalTableChips)
                        if self.predictedScore >= betOdds:
                            thinking = False
                    else:
                        thinking = False
                if self.myRaiseChips - minusBet > 0:
                    action = 'bet'
                    amount = self.myRaiseChips - minusBet
                else:
                    action = 'check'
                    amount = 0
        return action, amount, betOdds

    def declareAction(self, hole, board, round, my_Raise_Bet, my_Call_Bet, Table_Bet, number_players, raise_count, bet_count, my_Chips, total_my_bet, event, blindAmount):
        self.logger.debug('enter function, hole={}, board={}, round={}, my_Raise_Bet={}, my_Call_Bet={}, Table_Bet={}, number_players={}, raise_count={}, bet_count={}, my_Chips={}, total_my_bet={}'.format(str(hole), str(board), str(round), str(my_Raise_Bet), str(my_Call_Bet), str(Table_Bet), str(number_players), str(raise_count), str(bet_count), str(my_Chips), str(total_my_bet)))
        # Aggresive -tight
        # preflop->flop->turn->river
        amount = 0
        self.number_players = number_players
        self.totalTableChips = Table_Bet
        self.totalMyBetChips = total_my_bet
        self.myMinCallChips = my_Call_Bet
        self.myRaiseChips = my_Raise_Bet
        #my_Raise_Bet = (my_Chips * self.bet_tolerance) / (1 - self.bet_tolerance)
        self.predictedScore = HandEvaluator.evaluate_hand(hole, board)
        #score = math.pow(score, self.number_players)
        isSmallBlindBetPlayer = False
        isBigBlindBetPlayer = False
        if round == 'preflop' and blindAmount[0] > 0:
            self.totalMyBetChips += blindAmount[0]
        if round == 'preflop' and blindAmount[1] > 0:
            self.totalMyBetChips += blindAmount[1]
        raiseTableOdds = self.calcTableOdds(self.myRaiseChips, self.totalMyBetChips, self.totalTableChips)
        callTableOdds = self.calcTableOdds(self.myMinCallChips, self.totalMyBetChips, self.totalTableChips)
        allInTableOdds = self.calcTableOdds(my_Chips, self.totalMyBetChips, self.totalTableChips)
        fightingHeartBreak_threshold = 0.95
        self.logger.debug('my_Raise_Bet={}, bet_tolerance={}, predictedScore={}, raiseTableOdds={}, callTableOdds={}, allInTableOdds={}, total_number_players={}'.format(str(my_Raise_Bet), str(self.bet_tolerance), str(self.predictedScore), str(raiseTableOdds), str(callTableOdds), str(allInTableOdds), str(self.total_number_players)))
        betOdds = 0.0
        if round == 'preflop':
            bet_threshold = 0.8
            blindBet_threshold = 0.6
            blindBet_bare_threshold = float(my_Chips / 10)
            if self.predictedScore >= bet_threshold:
                if self.predictedScore >= raiseTableOdds:
                    action = 'raise'
                else:
                    action = 'call'
            else:
                action = 'fold'
            # interaction with player and humanity
            if event == '__bet':
                action, amount, betOdds = self.declareBet(round, action, amount, blindAmount)
            else:
                if (action == 'raise' or action == 'call') \
                        and hole[0].rank == hole[1].rank \
                        and hole[0].rank <= 9:
                    self.logger.debug('pair number less than {}, fold'.format(str(hole[0].rank)))
                    action = 'fold'
                    amount = 0
                if (action == 'raise' or action == 'call') \
                        and abs(hole[0].rank - hole[1].rank) >= 4:
                    self.logger.debug('gap of straight less than 4 between {} and {}, fold'.format(str(hole[0].rank), str(hole[1].rank)))
                    action = 'fold'
                    amount = 0
                if self.isSomebodyAllIn and self.predictedScore <= fightingHeartBreak_threshold:
                    self.logger.debug('isSomebodyAllIn={} and predictedScore {} less than {}, fold'.format(str(self.isSomebodyAllIn), str(self.predictedScore), str(fightingHeartBreak_threshold)))
                    action = 'fold'
        elif round == 'turn':
            bet_threshold = 0.7
            if self.predictedScore >= 0.9:
                action = 'allin'
                amount = my_Chips
            elif self.predictedScore >= bet_threshold:
                if self.predictedScore >= raiseTableOdds:
                    action = 'raise'
                    amount = my_Raise_Bet
                elif self.predictedScore >= callTableOdds:
                    action = 'call'
                    amount = my_Call_Bet
                else:
                    action = 'fold'
                    amount = 0
            else:
                action = 'fold'
                amount = 0
            # interaction with player and humanity
            if self.isTurnRaise:
                if action == 'call' \
                        and not self.haveIRaised:
                    action = 'fold'
            elif self.number_players / float(self.total_number_players) < 0.6:
                if action == 'fold' and self.predictedScore >= bet_threshold:
                    action = 'call'
            elif self.haveIRaised and self.predictedScore >= bet_threshold:
                if action == 'fold':
                    action = 'call'
            if self.isSomebodyAllIn and self.predictedScore <= fightingHeartBreak_threshold:
                self.logger.debug('isSomebodyAllIn={} and predictedScore less than {}, fold'.format(str(self.isSomebodyAllIn), str(self.predictedScore), str(fightingHeartBreak_threshold)))
                action = 'fold'
            if event == '__bet':
                action, amount, betOdds = self.declareBet(round, action, amount, blindAmount)
        elif round == 'river':
            bet_threshold = 0.65
            if self.predictedScore >= 0.85:
                action = 'allin'
                amount = my_Chips
            elif self.predictedScore >= bet_threshold:
                if self.predictedScore >= raiseTableOdds:
                    action = 'raise'
                    amount = my_Raise_Bet
                else:
                    action = 'call'
                    amount = my_Call_Bet
            else:
                action = 'fold'
                amount = 0
            # interaction with player and humanity
            if self.isRiverRaise:
                if action == 'call' \
                        and not self.haveIRaised:
                    action = 'fold'
            elif self.number_players / float(self.total_number_players) < 0.7:
                if action == 'fold' and self.predictedScore >= bet_threshold:
                    action = 'call'
            elif self.haveIRaised and self.predictedScore >= bet_threshold:
                if action == 'fold':
                    action = 'call'
            if self.isSomebodyAllIn and self.predictedScore <= fightingHeartBreak_threshold:
                self.logger.debug('isSomebodyAllIn={} and predictedScore less than {}, fold'.format(str(self.isSomebodyAllIn), str(self.predictedScore), str(fightingHeartBreak_threshold)))
                action = 'fold'
            if event == '__bet':
                action, amount, betOdds = self.declareBet(round, action, amount, blindAmount)
        else:
            bet_threshold = 0.75
            if self.predictedScore >= bet_threshold:
                if self.predictedScore >= raiseTableOdds:
                    action = 'raise'
                elif self.predictedScore >= callTableOdds:
                    action = 'call'
                else:
                    action = 'fold'
            else:
                if self.predictedScore >= callTableOdds:
                    action = 'call'
                else:
                    action = 'fold'
            # interaction with player and humanity
            if self.isFlopRaise:
                if action == 'call' \
                        and not self.haveIRaised:
                    action = 'fold'
            elif self.number_players / float(self.total_number_players) < 0.5:
                if self.predictedScore >= bet_threshold and action == 'fold':
                    action = 'call'
            elif self.haveIRaised and self.predictedScore >= bet_threshold:
                if action == 'fold':
                    action = 'call'
            if self.isSomebodyAllIn and self.predictedScore <= fightingHeartBreak_threshold:
                self.logger.debug('isSomebodyAllIn={} and predictedScore less than {}, fold'.format(str(self.isSomebodyAllIn), str(self.predictedScore), str(fightingHeartBreak_threshold)))
                action = 'fold'
            if event == '__bet':
                action, amount, betOdds = self.declareBet(round, action, amount, blindAmount)
        self.logger.debug('Round={}, Rank={}, Rank Decision={}'.format(str(round), str(self.predictedScore), action))
        if action == 'bet' or action == 'check':
            self.predictedTableOdds = betOdds
        elif action == 'call':
            self.predictedTableOdds = callTableOdds
            amount = my_Call_Bet
        elif action == 'raise':
            self.predictedTableOdds = raiseTableOdds
            amount = my_Raise_Bet
            self.haveIRaised = True
        elif action == 'allin':
            self.predictedTableOdds = allInTableOdds
            amount = my_Chips
        return action, amount

        #self.predictedWinRate = self.get_win_prob(hole, board, 1000, number_players)
"""
        if (action=='call' or action=='raise' or action == 'allin') and (len(board) == 3 or len(board) == 4):
            simulation_number = 1000
            self.predictedWinRate = self.get_win_prob(hole, board, simulation_number, number_players)
            if self.predictedWinRate < 0.5 and action == 'call':
                action = 'fold'
                amount = 0
                print 'Probability of victory is too small'
            elif self.predictedWinRate < 0.6 and action == 'raise':
                action = 'call'
                amount = my_Call_Bet
                print 'Wait next round, raise=>call'
            elif self.predictedWinRate < 0.7 and action == 'allin':
                action = 'raise'
                amount = my_Raise_Bet
                print 'Wait next round, allin=>raise'
            elif self.predictedWinRate >= 0.7 and action == 'raise':
                action = 'allin'
                amount = my_Chips
                print 'Probability of victory is large'
                """
        #return action, amount

class PotOddsPokerBot_MinionGo(PokerBot):

    def __init__(self, preflop_tight_loose_threshold,aggresive_passive_threshold,bet_tolerance):
        self.preflop_tight_loose_threshold = preflop_tight_loose_threshold
        self.aggresive_passive_threshold=aggresive_passive_threshold
        self.bet_tolerance=bet_tolerance
        self.clf = joblib.load('poker.pkl')

    def game_over(self, isWin,winChips,data):
        print "Game Over"

    def getCardID(self, card):
        rank=card.rank
        suit=card.suit
        suit=suit-1
        id=(suit*13)+rank
        return id

    def genCardFromId(self,cardID):
        if int(cardID)>13:
            rank=int(cardID)%13
            if rank==0:
                suit=int((int(cardID)-rank)/13)
            else:
                suit = int((int(cardID) - rank) / 13) + 1

            if(rank==0):
                rank=14
            else:
                rank+=1
            return Card(rank,suit)
        else:
            suit=1
            rank=int(cardID)
            if (rank == 0):
                rank = 14
            else:
                rank+=1
            return Card(rank,suit)

    def _pick_unused_card(self,card_num, used_card):
        used = [self.getCardID(card) for card in used_card]
        unused = [card_id for card_id in range(1, 53) if card_id not in used]
        choiced = random.sample(unused, card_num)
        return [self.genCardFromId(card_id) for card_id in choiced]

    def get_win_prob(self,hand_cards, board_cards,simulation_number,num_players):
        """Calculate the win probability from your board cards and hand cards by using simple Monte Carlo method.

        Args:
            board_cards: The board card list.
            hand_cards: The hand card list

        Examples:
#            >>> get_win_prob(["8H", "TS", "6C"], ["7D", "JC"])
        """
        win = 0
        round=0
        evaluator = HandEvaluator()
        for i in range(simulation_number):

            board_cards_to_draw = 5 - len(board_cards)  # 2
            board_sample = board_cards + self._pick_unused_card(board_cards_to_draw, board_cards + hand_cards)
            unused_cards = self._pick_unused_card((num_players - 1)*2, hand_cards + board_sample)
            opponents_hole = [unused_cards[2 * i:2 * i + 2] for i in range(num_players - 1)]

            try:
                opponents_score = [pow(evaluator.evaluate_hand(hole, board_sample), num_players) for hole in opponents_hole]
                # hand_sample = self._pick_unused_card(2, board_sample + hand_cards)
                my_rank = pow(evaluator.evaluate_hand(hand_cards, board_sample),num_players)
                if my_rank >= max(opponents_score):
                    win += 1
                #rival_rank = evaluator.evaluate_hand(hand_sample, board_sample)
                round+=1
            except Exception, e:
                print e.message
                continue
        # The large rank value means strong hand card
        print "Win:{}".format(win)
        win_prob = win / float(round)
        print "win_prob:{}".format(win_prob)
        return win_prob

    def declareAction(self, hole, board, round, my_Raise_Bet, my_Call_Bet,Table_Bet,number_players,raise_count,bet_count,my_Chips,total_bet):
        # Aggresive -tight
        self.number_players=number_players

        my_Raise_Bet=(my_Chips*self.bet_tolerance)/(1-self.bet_tolerance)
        print "Round:{}".format(round)
        score = HandEvaluator.evaluate_hand(hole, board)
        hand_score = HandEvaluator.evaluate_hand(hole, [])
        print "score:{}".format(score)
        #score = math.pow(score, self.number_players)
        print "score:{}".format(score)

        if round == 'preflop':
            if score >= self.preflop_tight_loose_threshold:
                action = 'call'
                amount = my_Call_Bet
            else:
                action = 'fold'
                amount = 0
        else:
            result = self.clf.predict([[hand_score, score]])
            action = result[0]
            if score >= self.aggresive_passive_threshold:
                TableOdds = (my_Raise_Bet+total_bet) / float(my_Raise_Bet + Table_Bet)
                if score >= TableOdds and action == "raise":
                    # action = 'raise'
                    amount = my_Raise_Bet
                else:
                    TableOdds = (my_Call_Bet+total_bet) / float(my_Call_Bet + Table_Bet)
                    if score >= TableOdds and action == 'call':
                        # action = 'call'
                        amount = my_Call_Bet
                    elif action == 'fold':
                        # action = 'fold'
                        amount = 0
                    else:
                        amount = 0
            else:
                TableOdds = (my_Call_Bet+total_bet) / float(my_Call_Bet + Table_Bet)
                if score >= TableOdds and action == 'call':
                    # action = 'call'
                    amount = my_Call_Bet
                elif action == 'fold':
                    # action = 'fold'
                    amount = 0
                else:
                    amount = 0
        #if (action=='call' or action=='raise') and len(board)>=4:
            #simulation_number=1000
            #win_rate=self.get_win_prob(hole, board, simulation_number,number_players)
            #if win_rate<0.4:
                #action = 'fold'
                #amount = 0
                #print 'change'
        return action, amount

if __name__ == '__main__':
        aggresive_threshold = 0.7
        passive_threshold = 0.8
        preflop_threshold_Loose = 0.3
        preflop_threshold_Tight = 0.7
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
        # Aggresive -loose
        #myPokerBot=PotOddsPokerBot(preflop_threshold_Loose,aggresive_threshold,bet_tolerance)
        #myPokerBot=PotOddsPokerBot(preflop_threshold_Tight,aggresive_threshold,bet_tolerance)
        #myPokerBot=PotOddsPokerBot(preflop_threshold_Loose,passive_threshold,bet_tolerance)
        #myPokerBot=PotOddsPokerBot(preflop_threshold_Tight,passive_threshold,bet_tolerance)

        #playerName = "c3b0cc70c2504124998b88d57b7fc0c6"
        playerName = 'icebreaker'
        #playerName = 'icebreaka'
        #connect_url = "ws://poker-battle.vtr.trendnet.org:3001"
        connect_url = 'ws://poker-training.vtr.trendnet.org:3001'
        #connect_url = 'ws://poker-dev.wrs.club:3001'
        trainMode = False
        print 'training mode was on'
        simulation_number=100
        bet_tolerance=0.1
        #myPokerBot=FreshPokerBot()
        #myPokerBot=MontecarloPokerBot(simulation_number)
        myPokerBot=PotOddsPokerBot(preflop_threshold_Tight, aggresive_threshold, bet_tolerance, logger)
        #myPokerBot = PotOddsPokerBot_MinionGo(preflop_threshold_Tight, aggresive_threshold, bet_tolerance)
        myPokerSocket=PokerSocket(playerName, connect_url, myPokerBot, logger)
        myPokerSocket.gameMatchResultFile = gameMatchResultFile
        myPokerSocket.gameSetResultFile = gameSetResultFile
        myPokerSocket.roundActionResultFile = roundActionResultFile
        currentTime = None
        hour = 0
        minute = 0
        while 1:
            currentTime = time.localtime()
            print('now is {}'.format(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())))
            hour = currentTime.tm_hour
            minute = currentTime.tm_min
            if (hour >= 12 and hour < 14) \
                    or (hour >= 17 and hour < 20) \
                    or trainMode:
                myPokerSocket.doListen()
            print('wait {} second(s) to resume'.format(str(resume_connection_threshold_second)))
            time.sleep(resume_connection_threshold_second)