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
        rotatingFileHandler = logging.handlers.RotatingFileHandler('Debug_TaxHoldem.log', 'a', 5*1024*1024, 10, 'utf-8')
        rotatingFileHandler.setLevel(logging.DEBUG)
        rotatingFileFormatter = logging.Formatter('%(asctime)s:Line%(lineno)s[%(levelname)s]%(funcName)s>>%(message)s')
        rotatingFileHandler.setFormatter((rotatingFileFormatter))
        self.logger.addHandler(rotatingFileHandler)

class PokerBot(object):
    def declareAction(self,hole, board, round, my_Raise_Bet, my_Call_Bet,Table_Bet,number_players,raise_count,bet_count,my_Chips,total_bet):
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
    my_Chips=0
    Table_Bet=0
    playerGameName=None
    raise_count=0
    bet_count=0
    total_bet=0
    isSomebodyAllIn = False
    whoAllIn = []
    isTurnRaise = False
    whoTrunRaise = []
    isRiverRaise = False
    whoRiverRaise = []
    logger = None

    def __init__(self, playerName, connect_url, pokerbot):
        self.pokerbot=pokerbot
        self.playerName=playerName
        self.connect_url=connect_url
        self.logger = Logger().logger

    def getRoundName(self, roundName, board):
        if len(board) == 0:
            return 'preflop'
        elif len(board) == 3:
            return 'flop'
        else:
            return roundName.lower()

    def getAction(self, data):
        self.logger.debug('enter function')
        self.logger.info('round name={}'.format(data['game']['roundName']))
        self.logger.debug('board={}'.format(self.board))
        round = self.getRoundName(data['game']['roundName'], self.board)
        # time.sleep(2)
        players = data['game']['players']
        chips = data['self']['chips']
        hands = data['self']['cards']

        self.raise_count = data['game']['raiseCount']
        self.bet_count = data['game']['betCount']
        self.my_Chips=chips
        self.playerGameName=data['self']['playerName']

        self.number_players = len(players)
        self.my_Call_Bet = data['self']['minBet']
        self.my_Raise_Bet = int(chips / 4)
        self.hole = []
        for card in (hands):
            self.hole.append(getCard(card))

        self.logger.debug('my Chips:{}, my Hands:{}'.format(chips, self.hole))
        self.logger.debug('table bet={}, current call bet={}, current raise bet={}'.format(self.Table_Bet, self.my_Call_Bet, self.my_Raise_Bet))

        # aggresive_Tight = PokerBotPlayer(preflop_threshold_Tight, aggresive_threshold)
        # tightAction, tightAmount = aggresive_Tight.declareAction(hole, board, round, my_Raise_Bet, my_Call_Bet,Table_Bet,number_players)
        self.pokerbot.isSomebodyAllIn = self.isSomebodyAllIn
        self.pokerbot.isRiverRaise = self.isRiverRaise
        self.pokerbot.isTurnRaise = self.isTurnRaise
        self.logger.debug('isSomebodyAllIn={}, isRiverRaise={}, isTurnRaise={}'.format(self.isSomebodyAllIn, self.isRiverRaise, self.isTurnRaise))
        action, amount = self.pokerbot.declareAction(self.hole, self.board, round, self.my_Raise_Bet, self.my_Call_Bet, self.Table_Bet, self.number_players, self.raise_count, self.bet_count, self.my_Chips, self.total_bet)
        self.total_bet += amount
        return action, amount

    def takeAction(self, action, data):
        self.logger.debug('enter function')
        try:
            self.logger.info('client-server={}'.format(action))
            if action == "__show_action" or action == '__deal':
                self.board = []
                for card in data['table']['board']:
                    self.board.append(getCard(card))
                self.Table_Bet = data['table']['totalBet']
                self.logger.debug('Table Bet:{}'.format(self.Table_Bet))

                currentPlayers = []
                for player in data['players']:
                    if (player['isSurvive'] and not player['folded']):
                        currentPlayers.append(player)
                self.number_players = len(currentPlayers)
                self.logger.debug('number_players:{}'.format(str(self.number_players)))

                if action != '__deal':
                    if data['action']['action'].lower() == 'raise':
                        if self.getRoundName(data['table']['roundName'], self.board) == 'turn':
                            if len(self.whoTrunRaise) == 0:
                                self.isTurnRaise = True
                            if data['action']['playerName'] not in self.whoTrunRaise:
                                self.whoTrunRaise.append(data['action']['playerName'])
                        elif self.getRoundName(data['table']['roundName'], self.board) == 'river':
                            if len(self.whoRiverRaise) == 0:
                                self.isRiverRaise = True
                            if data['action']['playerName'] not in self.whoRiverRaise:
                                self.whoRiverRaise.append(data['action']['playerName'])
                    elif data['action']['action'].lower() == 'allin':
                        if len(self.whoAllIn) == 0:
                            self.isSomebodyAllIn = True
                        if data['action']['playerName'] not in self.whoAllIn:
                            self.whoAllIn.append(data['action']['playerName'])
                    elif data['action']['action'].lower() == 'fold':
                        if data['action']['playerName'] in self.whoTrunRaise:
                            self.whoTrunRaise.remove(data['action']['playerName'])
                        if data['action']['playerName'] in self.whoRiverRaise:
                            self.whoRiverRaise.remove(data['action']['playerName'])
                        if data['action']['playerName'] in self.whoAllIn:
                            self.whoAllIn.remove(data['action']['playerName'])

                    self.logger.debug('isTurnRaise={}, whoTrunRaise={}, isRiverRaise={}, whoRiverRaise={}, isSomebodyAllIn={}, whoAllIn={}'.format(str(self.isTurnRaise), self.whoTrunRaise, str(self.isRiverRaise), self.whoRiverRaise, str(self.isSomebodyAllIn), self.whoAllIn))

            elif action == "__action" or action == "__bet":
                action, amount = self.getAction(data)
                self.logger.debug("action={}, amount={}".format(action, amount))
                self.ws.send(json.dumps({
                    "eventName": "__action",
                    "data": {
                        "action": action,
                        "playerName": self.playerName,
                        "amount": amount
                    }}))

                tableNumber = data['tableNumber']
                self.board = []
                for card in data['game']['board']:
                    self.board.append(getCard(card))
                self.logger.debug('board:{}'.format(self.board))
                round = self.getRoundName(data['game']['roundName'], self.board)
                self.logger.debug("round:{}".format(round))
                roundCount = data['game']['roundCount']
                myChips = data['self']['chips']
                playerActions = []
                for player in data['game']['players']:
                    playerid = player['playerName']
                    if (player['isSurvive'] and playerid != self.playerGameName):
                        playerActions.append('isFold={};isAllIn={}'.format(player['folded'], player['allIn']))
                with open('RoundAction_Result.csv', 'ab') as csvfile:
                    spamwriter = csv.writer(csvfile, delimiter=',')
                    spamwriter.writerow([time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
                                         str(tableNumber),
                                         str(roundCount),
                                         round,
                                         action,
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
                                         ', '.join(str(hand) for hand in playerActions)])
            elif action == "__round_end":
                self.total_bet=0
                players=data['players']
                isWin=False
                winChips=0
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
                self.whoTrunRaise = []
                self.isRiverRaise = False
                self.whoRiverRaise = []
                self.board = []
                for player in players:
                    winMoney=player['winMoney']
                    isFold = player['folded']
                    isAllIn = player['allIn']
                    if (winMoney > 0):
                        tableChips = winMoney
                    playerid=player['playerName']
                    if (self.playerGameName == playerid):
                        myChips = player['chips']
                        if (winMoney==0):
                            isWin = False
                        else:
                            isWin = True
                        winChips=winMoney
                        myHand=player['hand']['message']
                        amIFold = isFold
                        amIAllIn = isAllIn
                    else:
                        if (player['isSurvive']):
                            playerHands.append('{}:isFold={};isAllIn={}'.format(player['hand']['message'], str(isFold), str(isAllIn)))
                self.logger.info('round set finished')
                with open('GameSet_Result.csv', 'ab') as csvfile:
                    spamwriter = csv.writer(csvfile, delimiter=',')
                    enemyHands = format(', '.join(str(hand) for hand in playerHands))
                    spamwriter.writerow([time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
                                         str(tableNumber),
                                         winChips,
                                         str(amIFold),
                                         str(amIAllIn),
                                         str(myChips),
                                         tableChips,
                                         myHand,
                                         enemyHands])
                self.pokerbot.game_over(isWin, winChips, data)
            elif action == "__game_over":
                self.logger.info('game match over')
                self.logger.debug('data={}'.format(data))
                time.sleep(5)
                self.logger.info('try to join game match')
                self.ws.send(json.dumps({
                    "eventName": "__join",
                    "data": {
                        "playerName": self.playerName
                    }
                }))
        except Exception as e:
            self.logger.error(e.message)
            raise

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
            while 1:
                msg = json.loads(self.ws.recv())
                self.takeAction(msg["eventName"], msg["data"])
        except Exception, e:
            self.logger.error(e.message)
            self.ws.close()
            self.logger.info('shut down the connection and wait a while to resume')
            time.sleep(5)
            self.doListen()


class PotOddsPokerBot(PokerBot):

    predictedScore = 0
    predictedTableOdds = 0
    predictedWinRate = 0
    isSomebodyAllIn = False
    isTurnRaise = False
    isRiverRaise = False
    logger = None

    def __init__(self, preflop_tight_loose_threshold, aggresive_passive_threshold, bet_tolerance):
        self.preflop_tight_loose_threshold = preflop_tight_loose_threshold
        self.aggresive_passive_threshold=aggresive_passive_threshold
        self.bet_tolerance=bet_tolerance
        self.logger = Logger().logger

    def game_over(self, isWin, winChips, data):
        self.logger.debug('enter function')
        self.logger.info("game set over")
        self.logger.debug('win chips={}, response data={}', str(winChips), data)

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

    def declareAction(self, hole, board, round, my_Raise_Bet, my_Call_Bet, Table_Bet, number_players, raise_count, bet_count, my_Chips, total_my_bet):
        self.logger.debug('enter function, hole={}, board={}, round={}, my_Raise_Bet={}, my_Call_Bet={}, Table_Bet={}, number_players={}, raise_count={}, bet_count={}, my_Chips={}, total_my_bet={}', hole, board, round, my_Raise_Bet, my_Call_Bet, Table_Bet, number_players, raise_count, bet_count, my_Chips, total_my_bet)
        # Aggresive -tight
        # preflop->flop->turn->river
        self.number_players = number_players
        my_Raise_Bet = (my_Chips * self.bet_tolerance) / (1 - self.bet_tolerance)

        self.predictedScore = HandEvaluator.evaluate_hand(hole, board)
        #score = math.pow(score, self.number_players)

        raiseTableOdds = self.calcTableOdds(my_Raise_Bet, total_my_bet, Table_Bet)
        callTableOdds = self.calcTableOdds(my_Call_Bet, total_my_bet, Table_Bet)
        allInTableOdds = self.calcTableOdds(my_Chips, total_my_bet, Table_Bet)

        self.logger.debug('my_Raise_Bet={}, bet_tolerance={}, predictedScore={}, raiseTableOdds={}, callTableOdds={}, allInTableOdds={}'.format(my_Raise_Bet, self.bet_tolerance, self.predictedScore, raiseTableOdds, callTableOdds, allInTableOdds))

        if round == 'preflop':
            if self.predictedScore >= self.preflop_tight_loose_threshold:
                action = 'raise'
                amount = my_Raise_Bet
            else:
                action = 'fold'
                amount = 0
        elif round == 'turn':
            if self.predictedScore >= 0.9:
                action = 'allin'
                amount = my_Chips
            elif self.predictedScore >= self.preflop_tight_loose_threshold:
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
        elif round == 'river':
            if self.predictedScore >= 0.9:
                action = 'allin'
                amount = my_Chips
            elif self.predictedScore >= self.preflop_tight_loose_threshold:
                if self.predictedScore >= raiseTableOdds:
                    action = 'raise'
                    amount = my_Raise_Bet
                else:
                    action = 'call'
                    amount = my_Call_Bet
            else:
                action = 'fold'
                amount = 0
        else:
            if self.predictedScore >= 0.9:
                if self.predictedScore >= raiseTableOdds:
                    action = 'raise'
                    amount = my_Raise_Bet
                else:
                    action = 'call'
                    amount = my_Call_Bet
            elif self.predictedScore >= self.preflop_tight_loose_threshold:
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
                if self.predictedScore >= callTableOdds:
                    action = 'call'
                    amount = my_Call_Bet
                else:
                    action = 'fold'
                    amount = 0

        if(self.isSomebodyAllIn):
            self.logger.debug('isSomebodyAllIn={}, always fold'.format(self.isSomebodyAllIn))
            action = 'fold'
            amount = 0

        self.logger.debug('Round={}, Rank={}, Rank Decision={}'.format(round, self.predictedScore, action))

        if action == 'call':
            self.predictedTableOdds = callTableOdds
        elif action == 'raise':
            self.predictedTableOdds = raiseTableOdds
        elif action == 'allin':
            self.predictedTableOdds = allInTableOdds

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

    def declareAction(self,hole, board, round, my_Raise_Bet, my_Call_Bet,Table_Bet,number_players,raise_count,bet_count,my_Chips,total_bet):
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

class MontecarloPokerBot(PokerBot):

    def __init__(self, simulation_number):
       self.simulation_number=simulation_number

    def game_over(self, isWin,winChips,data):
        pass

    def declareAction(self,hole, board, round, my_Raise_Bet, my_Call_Bet,Table_Bet,number_players,raise_count,bet_count,my_Chips,total_bet):
        win_rate =self.get_win_prob(hole,board,number_players)
        print "win Rate:{}".format(win_rate)
        if win_rate > 0.5:
            if win_rate > 0.85:
                # If it is extremely likely to win, then raise as much as possible
                action = 'raise'
                amount = my_Raise_Bet
            elif win_rate > 0.75:
                # If it is likely to win, then raise by the minimum amount possible
                action = 'raise'
                amount = my_Raise_Bet
            else:
                # If there is a chance to win, then call
                action = 'call'
                amount=my_Call_Bet
        else:
            action = 'fold'
            amount=0
        return action,amount

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

    def _pick_unused_card(self,card_num, used_card):

        used = [self.getCardID(card) for card in used_card]
        unused = [card_id for card_id in range(1, 53) if card_id not in used]
        choiced = random.sample(unused, card_num)
        return [self.genCardFromId(card_id) for card_id in choiced]

    def get_win_prob(self,hand_cards, board_cards,num_players):

        win = 0
        round=0
        evaluator = HandEvaluator()

        for i in range(self.simulation_number):

            board_cards_to_draw = 5 - len(board_cards)  # 2
            board_sample = board_cards + self._pick_unused_card(board_cards_to_draw, board_cards + hand_cards)

            unused_cards = self._pick_unused_card((num_players - 1) * 2, hand_cards + board_sample)
            opponents_hole = [unused_cards[2 * i:2 * i + 2] for i in range(num_players - 1)]
            #hand_sample = self._pick_unused_card(2, board_sample + hand_cards)

            try:
                opponents_score = [evaluator.evaluate_hand(hole, board_sample) for hole in opponents_hole]
                my_rank = evaluator.evaluate_hand(hand_cards, board_sample)
                if my_rank >= max(opponents_score):
                    win += 1
                #rival_rank = evaluator.evaluate_hand(hand_sample, board_sample)
                round+=1
            except Exception, e:
                #print e.message
                continue
        print "Win:{}".format(win)
        win_prob = win / float(round)
        return win_prob

class FreshPokerBot(PokerBot):

    def game_over(self, isWin, winChips, data):
        pass

    def declareAction(self,holes, boards, round, my_Raise_Bet, my_Call_Bet, Table_Bet, number_players, raise_count, bet_count, my_Chips, total_bet):
        my_rank = HandEvaluator.evaluate_hand(holes, boards)
        if my_rank > 0.9:
            action = 'allin'
            amount = 0
        elif my_rank > 0.75:
            action = 'raise'
            amount = my_Raise_Bet
        elif my_rank > 0.5:
            action = 'call'
            amount = my_Call_Bet
        else:
            action = 'fold'
            amount = 0
        return action,amount

if __name__ == '__main__':
        aggresive_threshold = 0.5
        passive_threshold = 0.7
        preflop_threshold_Loose = 0.3
        preflop_threshold_Tight = 0.8

        # Aggresive -loose
        #myPokerBot=PotOddsPokerBot(preflop_threshold_Loose,aggresive_threshold,bet_tolerance)
        #myPokerBot=PotOddsPokerBot(preflop_threshold_Tight,aggresive_threshold,bet_tolerance)
        #myPokerBot=PotOddsPokerBot(preflop_threshold_Loose,passive_threshold,bet_tolerance)
        #myPokerBot=PotOddsPokerBot(preflop_threshold_Tight,passive_threshold,bet_tolerance)

        #playerName = "c3b0cc70c2504124998b88d57b7fc0c6"
        playerName = 'icebreaker'
        connect_url = 'ws://poker-training.vtr.trendnet.org:3001'
        simulation_number=100
        bet_tolerance=0.1
        #myPokerBot=FreshPokerBot()
        #myPokerBot=MontecarloPokerBot(simulation_number)
        myPokerBot=PotOddsPokerBot(preflop_threshold_Tight, aggresive_threshold, bet_tolerance)
        #myPokerBot = PotOddsPokerBot_MinionGo(preflop_threshold_Tight, aggresive_threshold, bet_tolerance)
        myPokerSocket=PokerSocket(playerName, connect_url, myPokerBot)
        myPokerSocket.doListen()