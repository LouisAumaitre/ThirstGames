#!python
from copy import copy
from random import random

from thirst_games.constants import MAP, PLAYERS, DEATH, AFTERNOON, TIME, MORNING, DEADS
from thirst_games.map import Map


class Game:
    def __init__(self, players: list):
        self.players = players
        self.alive_players = players
        self.map = Map()
        for p in self.players:
            self.map.add_player(p)
            for p2 in self.players:
                if p != p2 and p.district == p2.district:
                    p.relationship(p2).friendship += 0.5

    def run(self):
        day = 1
        print(f'\n== DAY {day} START ==')
        self.morning()
        print(f'...')
        while len(self.alive_players) > 1 and day < 5:
            self.morning()
            print(f'-- DAY {day} afternoon --')
            self.afternoon()
            day += 1
            print(f'\n== DAY {day} morning ==')

    def play(self, context):
        players = copy(context[PLAYERS])
        for i in range(len(players) + 2):
            if i < len(players) and players[i].is_alive:
                players[i].think(context)
            if i - 2 > 0 and players[i-2].is_alive:
                players[i-2].act(context)
        # for p in players:
        #     p.think(context)
        # for p in players:
        #     p.act(context)
        for p in players:
            p.busy = False
            p.strategy = None
        self.alive_players = [p for p in self.players if p.is_alive]

    def afternoon(self):
        players = copy(self.alive_players)
        players.sort(key=lambda x: random())
        context = {
            MAP: self.map,
            PLAYERS: players,
            DEATH: death,
            TIME: AFTERNOON,
            DEADS: [],
        }
        self.play(context)

    def morning(self):
        players = copy(self.alive_players)
        players.sort(key=lambda x: random())
        context = {
            MAP: self.map,
            PLAYERS: players,
            DEATH: death,
            TIME: MORNING,
            DEADS: [],
        }
        self.play(context)


def death(dead_player, context):
    context[PLAYERS].remove(dead_player)
    context[MAP].remove_player(dead_player)
