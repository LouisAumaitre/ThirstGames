#!python
from typing import List, Optional, Union

from copy import copy
from random import random, choice

from thirst_games.abstract.entity import Entity
from thirst_games.abstract.playing_entity import PlayingEntity
from thirst_games.constants import AFTERNOON, MORNING, NIGHT, STARTER
from thirst_games.context import Context, AbstractGame
from thirst_games.event import WildFire, DropEvent, Flood, AcidGas, Wasps, Beasts
from thirst_games.map import Map, START_AREA, Area
from thirst_games.narrator import Narrator, format_list
from thirst_games.player.group import Group
from thirst_games.player.player import Player
from thirst_games.singleton import Singleton


class Game(AbstractGame, metaclass=Singleton):
    def __init__(self, players: Optional[List[Player]]=None):
        if players is None:
            raise ValueError('No players in the arena')
        Context().game = self
        self.players = players
        self.map = Map(len(players))
        self._event_gauge = 0
        self._players_at_last_event = 0
        self._time_since_last_event = 0
        for p in self.players:
            self.map.add_player(p)
            for p2 in self.players:
                if p != p2 and p.district == p2.district:
                    p.relationship(p2).add_friendship(0.5)
                    p.relationship(p2).add_trust(0.5)
        self.event_classes = [WildFire, DropEvent, Flood, AcidGas, Wasps, Beasts]
        self.day = 0
        self.time = STARTER

    @property
    def alive_players(self):
        return [p for p in self.players if p.is_alive]

    def all_players_at_start_are_allies(self):
        players = copy(self.map.get_area(START_AREA).players)
        player_one = players.pop()
        for p in players:
            if not player_one.relationship(p).allied:
                return False
        return True

    def run(self):
        self.day = 1
        self._event_gauge = 0
        self._players_at_last_event = len(self.alive_players)
        self._time_since_last_event = 0
        Narrator().new(f'== DAY {self.day} START ==')
        Narrator().new(['All players start', self.map.get_area(START_AREA).at])
        self.time = STARTER
        Context().forbidden_areas.append(self.map.get_area(START_AREA))
        rounds = 0
        while len(self.playing_entities_at(self.map.get_area(START_AREA))) > 1:
            Narrator().tell()
            self.launch()
            Narrator().tell(filters=[self.map.get_area(START_AREA).at])
            Narrator().new(f'...')
            if self.map.players_count(START_AREA) > 1:
                Narrator().new([
                    format_list([p.name for p in self.alive_players if p.current_area.is_start]),
                    'remain',
                    self.map.get_area(START_AREA).at
                ])
            elif self.map.players_count(START_AREA) == 1:
                Narrator().new([
                    'Only',
                    [p for p in self.alive_players if p.current_area.is_start][0].name,
                    'remains',
                    self.map.get_area(START_AREA).at
                ])
                Narrator().tell()
                self.launch()
                Narrator().tell(filters=[self.map.get_area(START_AREA).at])
            rounds += 1
            if rounds > 10:
                raise Exception
        self._players_at_last_event = len(self.alive_players)
        while len(self.alive_players) > 1 and self.day < 5:
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
        Context().new_day()
        self.play()

    def play(self):
        Narrator().cut()
        players: List[PlayingEntity] = []
        for player in self.alive_players:
            player.consider_betrayal()
        for area in self.map.areas:
            players.extend(self.playing_entities_at(area))
        if self.time != STARTER:
            for p in self.alive_players:
                p.upkeep()
        players.sort(key=lambda x: random())
        if self.check_for_event():
            self.trigger_event()
        for i in range(len(players) + 2):
            if i < len(players) and players[i].is_alive:
                if self.time != STARTER or players[i].current_area.is_start:
                    players[i].think()
            if i - 2 >= 0 and players[i-2].is_alive:
                if self.time != STARTER or players[i-2].current_area.is_start:
                    players[i-2].act()
        for p in self.alive_players:
            p.busy = False
            p.acted = False

    def playing_entities_at(self, area: Union[str, Area, Entity]) -> List[PlayingEntity]:
        area = self.map.get_area(area)
        players: List[PlayingEntity] = []
        area_players = copy(area.players)
        while area_players:
            group = area_players[0].current_group()
            if len(group) > 1:
                players.append(Group(group))
            else:
                players.append(group[0])
            for player in group:
                area_players.remove(player)
        return players

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
        self._event_gauge += len(self.alive_players) - self._players_at_last_event + self._time_since_last_event
        self._time_since_last_event += 2
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
        self._players_at_last_event = len(self.alive_players)
        self._time_since_last_event = 0

    def death(self, dead_player):
        try:
            self.map.remove_player(dead_player)
        except ValueError as e:
            Narrator().tell()
            raise ValueError(
                f'{dead_player.name} has {dead_player.health}hp, is_alive={dead_player.is_alive}, '
                f'is_in_players={dead_player in self.alive_players}'
            ) from e
