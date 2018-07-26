#!python
from copy import copy
from random import random

from thirst_games.constants import MAP, PLAYERS, DEATH, AFTERNOON, TIME, MORNING, DEADS, NARRATOR
from thirst_games.map import Map
from thirst_games.narrator import Narrator


class Game:
    def __init__(self, players: list):
        self.players = players
        self.alive_players = players
        self.map = Map()
        self.narrator = Narrator()
        for p in self.players:
            self.map.add_player(p)
            for p2 in self.players:
                if p != p2 and p.district == p2.district:
                    p.relationship(p2).friendship += 0.5

    def run(self):
        day = 1
        self.narrator.new(f'\n== DAY {day} START ==')
        self.launch(**{TIME: MORNING})
        self.narrator.new(f'...')
        while len(self.alive_players) > 1 and day < 10:
            self.launch(**{TIME: MORNING})
            self.narrator.new(f'-- DAY {day} afternoon --')
            self.launch(**{TIME: AFTERNOON})
            day += 1
            self.narrator.tell()
            self.narrator.new(f'\n== DAY {day} morning ==')

    def play(self, **context):
        players = copy(context[PLAYERS])
        for i in range(len(players) + 2):
            if i < len(players) and players[i].is_alive:
                players[i].think(**context)
            if i - 2 >= 0 and players[i-2].is_alive:
                players[i-2].act(**context)
        # for i in range(len(players)):
        #     if players[i].strategy is not None:
        #         print(f'miss {i}/{len(players)} ({players[i].name})')
        for p in players:
            p.busy = False
        self.alive_players = [p for p in self.players if p.is_alive]

    def launch(self, **kwargs):
        players = copy(self.alive_players)
        players.sort(key=lambda x: random())
        context = {
            MAP: self.map,
            PLAYERS: players,
            DEATH: death,
            NARRATOR: self.narrator,
            DEADS: [],
            **kwargs
        }
        self.play(**context)


def death(dead_player, **context):
    context[PLAYERS].remove(dead_player)
    context[MAP].remove_player(dead_player)
