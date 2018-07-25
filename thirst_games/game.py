#!python
from copy import copy
from random import random

from thirst_games.constants import MAP, PLAYERS
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
            print(f'== DAY {day} ==')
            self.day()
            day += 1

    def day(self):
        players = copy(self.alive_players)
        players.sort(key=lambda x: random())
        context = {
            MAP: self.map,
            PLAYERS: players,
        }
        for p1 in players:
            for p2 in players:
                if p1 == p2 or p1.busy or p2.busy or not p1.is_alive or not p2.is_alive:
                    continue
                if p1.current_area == p2.current_area:
                    p1.interact(p2, context)
            if not p1.busy:
                p1.act_alone(context)
        for p in players:
            p.busy = False
        self.alive_players = [p for p in self.players if p.is_alive]
