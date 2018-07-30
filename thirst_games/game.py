#!python
from copy import copy
from random import random

from thirst_games.constants import MAP, PLAYERS, DEATH, AFTERNOON, TIME, MORNING, DEADS, NARRATOR, NIGHT, STARTER
from thirst_games.map import Map, START_AREA
from thirst_games.narrator import Narrator, format_list


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
        self.narrator.new(['All players start at', START_AREA])
        while len(self.map.areas[START_AREA]) > 1:
            self.launch(**{TIME: STARTER})
            self.narrator.new(f'...')
            if len(self.map.areas[START_AREA]) > 1:
                self.narrator.new([
                    format_list([p.first_name for p in self.alive_players if p.current_area == START_AREA]),
                    'remain at',
                    START_AREA
                ])
            elif len(self.map.areas[START_AREA]) == 1:
                self.narrator.new([
                    'Only',
                    [p for p in self.alive_players if p.current_area == START_AREA][0].first_name,
                    'remain at',
                    START_AREA
                ])
                self.launch(**{TIME: STARTER})
        self.narrator.tell(filters=[f'at {START_AREA}'])
        while len(self.alive_players) > 1 and day < 10:
            if day != 1:
                self.launch(**{TIME: MORNING})
            self.narrator.new(f'-- DAY {day} afternoon --')
            self.launch(**{TIME: AFTERNOON})
            self.narrator.new(f'-- NIGHT {day} --')
            self.launch(**{TIME: NIGHT})
            day += 1
            self.narrator.tell()
            self.status()
            self.narrator.new(f'\n== DAY {day} morning ==')
        if len(self.alive_players) == 1:
            print(f'{self.alive_players[0].name} wins the Hunger Games!')

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

    def play(self, **context):
        self.narrator.cut()
        players = copy(context[PLAYERS])
        if context[TIME] != STARTER:
            for p in players:
                p.upkeep(**context)
        for i in range(len(players) + 2):
            if i < len(players) and players[i].is_alive:
                if context[TIME] != STARTER or players[i].current_area == START_AREA:
                    players[i].think(**context)
            if i - 2 >= 0 and players[i-2].is_alive:
                if context[TIME] != STARTER or players[i-2].current_area == START_AREA:
                    players[i-2].act(**context)
        # for i in range(len(players)):
        #     if players[i].strategy is not None:
        #         print(f'miss {i}/{len(players)} ({players[i].name})')
        for p in players:
            p.busy = False
        self.alive_players = [p for p in self.players if p.is_alive]

    def status(self):
        l_name = max([len(p.name) for p in self.alive_players])
        for p in self.alive_players:
            bag = str([str(e) for e in p._equipment]).replace('\'', '')
            print(f'- {p.name:<{l_name}} {int(p.health * 100):>3}hp {int(p.energy * 100):>3}nrg '
                  f'{int(p.sleep * 100):>3}slp {int(p.stomach * 100):>3}stm {p.weapon.name:<10} '
                  f'{p.current_area:<10} {bag}, {format_list(p.status)}')


def death(dead_player, **context):
    try:
        context[PLAYERS].remove(dead_player)
        context[MAP].remove_player(dead_player)
    except ValueError as e:
        raise ValueError(
            f'{dead_player.first_name} has {dead_player.health}hp, is_alive={dead_player.is_alive}, '
            f'is_in_players={dead_player in context[PLAYERS]}'
        ) from e
