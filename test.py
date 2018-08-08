from thirst_games.game import Game
from thirst_games.player.player import Player

game = Game([
    Player('Tutur', 1, 'he'),
    Player('Tapus', 1, 'he'),
    # Player('Sebou', 2, 'he'),
    # Player('Florence', 2, 'she'),
    Player('Rabbit', 3, 'he'),
    Player('Magou', 3, 'she'),
    Player('Powner', 4, 'he'),
    Player('Yunne', 4, 'he'),
    # Player('The Sheep', 5, 'he'),
    # Player('Claire', 5, 'she'),
    # Player('Pierre', 6, 'he'),
    # Player('Foxy', 6, 'she'),
    Player('Yah', 7, 'he'),
    Player('Bakablue', 7, 'she'),
    Player('Piou', 8, 'he'),
    Player('Meggie', 8, 'she'),
    Player('Penguin', 9, 'he'),
    Player('Wajanatrabu', 9, 'he'),
    # Player('Nathan', 10, 'he'),
    # Player('Delphine', 10, 'she'),
    # Player('Romain', 11, 'he'),
    # Player('Polukranos', 11, 'he'),
    Player('Antonin', 12, 'he'),
    Player('Tygrec', 12, 'she'),
])

game.run()
print(game.map.test)
