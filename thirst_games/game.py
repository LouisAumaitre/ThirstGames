#!python
from copy import copy
from random import random

from thirst_games.constants import MAP, PLAYERS, DEATH, AFTERNOON, TIME, MORNING
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
        while len(self.alive_players) > 1 and day < 10:
            print(f'== DAY {day} morning ==')
            self.morning()
            print(f'-- DAY {day} afternoon --')
            self.afternoon()
            day += 1

    def play(self, context):
        players = context[PLAYERS]
        for p1 in players:
            p1.think(context)
        for p in players:
            p.act(context)
        for p in players:
            p.busy = False
        self.alive_players = [p for p in self.players if p.is_alive]

    def afternoon(self):
        players = copy(self.alive_players)
        players.sort(key=lambda x: random())
        context = {
            MAP: self.map,
            PLAYERS: players,
            DEATH: cannon_ball,
            TIME: AFTERNOON,
        }
        self.play(context)

    def morning(self):
        players = copy(self.alive_players)
        players.sort(key=lambda x: random())
        context = {
            MAP: self.map,
            PLAYERS: players,
            DEATH: cannon_ball,
            TIME: MORNING,
        }
        self.play(context)


def cannon_ball(dead_player, context):
    context[PLAYERS].remove(dead_player)
    context[MAP].remove_player(dead_player)
