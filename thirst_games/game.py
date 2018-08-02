#!python
from typing import List, Optional

from copy import copy
from random import random, choice

from thirst_games.constants import AFTERNOON, MORNING, NIGHT, STARTER
from thirst_games.context import Context, AbstractGame
from thirst_games.event import WildFire, DropEvent
from thirst_games.map import Map, START_AREA
from thirst_games.narrator import Narrator, format_list
from thirst_games.player.player import Player
from thirst_games.singleton import Singleton


class Game(AbstractGame, metaclass=Singleton):
    def __init__(self, players: Optional[List[Player]]=None):
        if players is None:
            raise ValueError('No players in the arena')
        self.players = players
        self.map = Map(len(players))
        self._event_gauge = 0
        self._players_at_last_event = 0
        self._time_since_last_event = 0
        for p in self.players:
            self.map.add_player(p)
            for p2 in self.players:
                if p != p2 and p.district == p2.district:
                    p.relationship(p2).friendship += 0.5
        self.event_classes = [WildFire, DropEvent]
        self.day = 0
        self.time = STARTER
        Context().game = self

    @property
    def alive_players(self):
        return [p for p in self.players if p.is_alive]

    def run(self):
        self.day = 1
        self._event_gauge = 0
        self._players_at_last_event = len(self.alive_players)
        self._time_since_last_event = 0
        Narrator().new(f'== DAY {self.day} START ==')
        Narrator().new(['All players start at', START_AREA])
        self.time = STARTER
        while self.map.players_count(START_AREA) > 1:
            self.launch()
            Narrator().new(f'...')
            if self.map.players_count(START_AREA) > 1:
                Narrator().new([
                    format_list([p.first_name for p in self.alive_players if p.current_area.is_start]),
                    'remain at',
                    START_AREA
                ])
            elif self.map.players_count(START_AREA) == 1:
                Narrator().new([
                    'Only',
                    [p for p in self.alive_players if p.current_area.is_start][0].first_name,
                    'remain at',
                    START_AREA
                ])
                self.launch()
        Narrator().tell(filters=[f'at {START_AREA}'])
        self._players_at_last_event = len(self.alive_players)
        while len(self.alive_players) > 1 and self.day < 10:
            if self.day != 1:
                self.time = MORNING
                self.launch()
            if len(self.alive_players) < 2:
                break
            Narrator().new(f'-- DAY {self.day} afternoon --')
            self.time = AFTERNOON
            self.launch()
            if len(self.alive_players) < 2:
                break
            Narrator().new(f'-- NIGHT {self.day} --')
            self.time = NIGHT
            self.launch()
            if len(self.alive_players) < 2:
                break
            Narrator().tell()
            self.status()
            self.day += 1
            Narrator().new(f'\n== DAY {self.day} morning ==')
        if len(self.alive_players) == 1:
            Narrator().tell()
            print(f'{self.alive_players[0].name} wins the Hunger Games!')

    def launch(self):
        self.alive_players.sort(key=lambda x: random())
        self.play()

    def play(self):
        Narrator().cut()
        players = copy(self.alive_players)
        if self.time != STARTER:
            for p in players:
                p.upkeep()
        if self.check_for_event():
            self.trigger_event()
        for i in range(len(players) + 2):
            if i < len(players) and players[i].is_alive:
                if self.time != STARTER or players[i].current_area.is_start:
                    players[i].think()
            if i - 2 >= 0 and players[i-2].is_alive:
                if self.time != STARTER or players[i-2].current_area.is_start:
                    players[i-2].act()
        for p in players:
            p.busy = False

    def status(self):
        l_name = max([len(p.name) for p in self.alive_players])
        l_weapon = max([len(str(p.weapon)) for p in self.alive_players])
        l_area = max([len(p.current_area.name) for p in self.alive_players])
        l_status = max([len(p.full_status_desc) for p in self.alive_players])
        for p in self.alive_players:
            status = f'- {p.name:<{l_name}} {int(p.health * 100):>3}/{int(p.max_health * 100):>3}hp ' \
                     f'{int(p.energy * 100):>3}nrg ' \
                     f'{int(p.sleep * 100):>3}slp {int(p.stomach * 100):>3}stm{int(p.water * 100):>4}wtr ' \
                     f'{str(p.weapon):<{l_weapon}} {p.current_area.name.upper():<{l_area}} ' \
                     f'{p.full_status_desc:<{l_status}} '
            bag = str([str(e) for e in p._equipment]).replace('\'', '')
            max_l = 200 - len(status)
            if len(bag) > max_l:
                bag = bag[:max_l-3] + '...'
            print(status + bag)

    def check_for_event(self):
        if self.time == STARTER:
            return False
        # Narrator().new([
        #     'event gauge:', self._event_gauge, '+', len(self.alive_players), '-', self._players_at_last_event, '+',
        #     self._time_since_last_event])
        self._event_gauge += len(self.alive_players) - self._players_at_last_event + self._time_since_last_event
        self._time_since_last_event += 2
        # Narrator().add(['=', self._event_gauge])
        return self._event_gauge > 0

    def trigger_event(self):
        possible_events = [cls for cls in self.event_classes if cls.can_happen()]
        if not len(possible_events):
            return
        self._event_gauge = 0
        event = choice(possible_events)()
        areas = format_list([f'the {area.name}' for area in event.areas])
        Narrator().new(['EVENT:', event.name.upper(), f'at {areas}'])
        Narrator().cut()
        event.trigger()
        Narrator().new(' ')
        Narrator().cut()
        Map().test += f' {event.name}-{self.day}'
        self._players_at_last_event = len(self.alive_players)
        self._time_since_last_event = 0

    def death(self, dead_player):
        try:
            self.map.remove_player(dead_player)
        except ValueError as e:
            Narrator().tell()
            raise ValueError(
                f'{dead_player.first_name} has {dead_player.health}hp, is_alive={dead_player.is_alive}, '
                f'is_in_players={dead_player in self.alive_players}'
            ) from e
