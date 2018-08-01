#!python
from typing import List

from copy import copy
from random import random, choice

from thirst_games.constants import MAP, PLAYERS, DEATH, AFTERNOON, TIME, MORNING, DEADS, NARRATOR, NIGHT, STARTER, DAY
from thirst_games.event import WildFire, DropEvent
from thirst_games.map import Map, START_AREA
from thirst_games.narrator import Narrator, format_list
from thirst_games.player.player import Player


class Game:
    def __init__(self, players: List[Player]):
        self.players = players
        self.map = Map(len(players))
        self.narrator = Narrator()
        self._event_gauge = 0
        self._players_at_last_event = 0
        self._time_since_last_event = 0
        for p in self.players:
            self.map.add_player(p)
            for p2 in self.players:
                if p != p2 and p.district == p2.district:
                    p.relationship(p2).friendship += 0.5
        self.event_classes = [WildFire, DropEvent]

    @property
    def alive_players(self):
        return [p for p in self.players if p.is_alive]

    def run(self):
        day = 1
        self._event_gauge = 0
        self._players_at_last_event = len(self.alive_players)
        self._time_since_last_event = 0
        self.narrator.new(f'== DAY {day} START ==')
        self.narrator.new(['All players start at', START_AREA])
        while len(self.map.areas[START_AREA]) > 1:
            self.launch(**{TIME: STARTER, DAY: day})
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
                self.launch(**{TIME: STARTER, DAY: day})
        self.narrator.tell(filters=[f'at {START_AREA}'])
        self._players_at_last_event = len(self.alive_players)
        while len(self.alive_players) > 1 and day < 10:
            if day != 1:
                self.launch(**{TIME: MORNING, DAY: day})
            if len(self.alive_players) < 2:
                break
            self.narrator.new(f'-- DAY {day} afternoon --')
            self.launch(**{TIME: AFTERNOON, DAY: day})
            if len(self.alive_players) < 2:
                break
            self.narrator.new(f'-- NIGHT {day} --')
            self.launch(**{TIME: NIGHT, DAY: day})
            if len(self.alive_players) < 2:
                break
            day += 1
            self.narrator.tell()
            self.status()
            self.narrator.new(f'\n== DAY {day} morning ==')
        if len(self.alive_players) == 1:
            self.narrator.tell()
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
        if self.check_for_event(**context):
            self.trigger_event(**context)
        for i in range(len(players) + 2):
            if i < len(players) and players[i].is_alive:
                if context[TIME] != STARTER or players[i].current_area == START_AREA:
                    players[i].think(**context)
            if i - 2 >= 0 and players[i-2].is_alive:
                if context[TIME] != STARTER or players[i-2].current_area == START_AREA:
                    players[i-2].act(**context)
        for p in players:
            p.busy = False

    def status(self):
        l_name = max([len(p.name) for p in self.alive_players])
        l_weapon = max([len(str(p.weapon)) for p in self.alive_players])
        l_area = max([len(p.current_area) for p in self.alive_players])
        for p in self.alive_players:
            bag = str([str(e) for e in p._equipment]).replace('\'', '')
            max_l = 180
            if len(bag) > max_l:
                bag = bag[:max_l-3] + '...'
            print(f'- {p.name:<{l_name}} {int(p.health * 100):>3}/{int(p.max_health * 100):>3}hp '
                  f'{int(p.energy * 100):>3}nrg '
                  f'{int(p.sleep * 100):>3}slp {int(p.stomach * 100):>3}stm {int(p.water * 100):>3}wtr  '
                  f'{str(p.weapon):<{l_weapon}}  {p.current_area.upper():<{l_area}}  '
                  f'{format_list(p.status)}  '
                  f'{format_list([str(po) for po in p.active_poisons])}')
            print(f'           {bag}')

    def check_for_event(self, **context):
        if context[TIME] == STARTER:
            return False
        # context[NARRATOR].new([
        #     'event gauge:', self._event_gauge, '+', len(self.alive_players), '-', self._players_at_last_event, '+',
        #     self._time_since_last_event])
        self._event_gauge += len(self.alive_players) - self._players_at_last_event + self._time_since_last_event
        self._time_since_last_event += 2
        # context[NARRATOR].add(['=', self._event_gauge])
        return self._event_gauge > 0

    def trigger_event(self, **context):
        possible_events = [cls for cls in self.event_classes if cls.can_happen(**context)]
        if not len(possible_events):
            return
        self._event_gauge = 0
        event = choice(possible_events)(**context)
        context[NARRATOR].new(['EVENT:', event.name.upper(), f'at {format_list(event.areas)}'])
        context[NARRATOR].cut()
        event.trigger(**context)
        context[NARRATOR].new(' ')
        context[NARRATOR].cut()
        context[MAP].test = f'{context[MAP].test} {event.name}-{context[DAY]}'
        self._players_at_last_event = len(self.alive_players)
        self._time_since_last_event = 0


def death(dead_player, **context):
    try:
        context[PLAYERS].remove(dead_player)
        context[MAP].remove_player(dead_player)
    except ValueError as e:
        context[NARRATOR].tell()
        raise ValueError(
            f'{dead_player.first_name} has {dead_player.health}hp, is_alive={dead_player.is_alive}, '
            f'is_in_players={dead_player in context[PLAYERS]}'
        ) from e
