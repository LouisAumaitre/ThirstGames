from random import random

START_AREA = 'the cornucopea'


class Map:
    def __init__(self, size=4):
        possible_parts = [
            'the green forest', 'the red forest', 'the white forest', 'the rocks', 'the jungle', 'the river', 'the hill'
        ]
        possible_parts.sort(key=lambda x: random())
        self.areas = {area_name: [] for area_name in possible_parts[0:size-1]}
        self.areas[START_AREA] = []

    def add_player(self, player):
        player.current_area = START_AREA
        self.areas[START_AREA].append(player)

    def move_player(self, player, new_area):
        self.areas[player.current_area].remove(player)
        self.areas[new_area].append(player)
        player.current_area = new_area
        print(f'{player.first_name} moves to {new_area}')
