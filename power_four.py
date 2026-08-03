from const import WIDTH,HEIGHT,EMPTY_SYMB

class PowerFour():
    def __init__(self):
        self.grid = [[EMPTY_SYMB]*WIDTH]*HEIGHT
        self.last_chip_played = (-1,-1)

    def add_chip(self,no_player, col):
        if 0<= col <WIDTH:
            for j in range(WIDTH-1, 0,-1):
                if self.grid[j,col] == EMPTY_SYMB:
                    self.grid[j,col] = no_player
                    self.last_chip_played = (j,col)
                    return True
        return False

    def is_won(self):
        start_r, start_c = self.last_chip_played
        player = self.grid[start_r][start_c]

        axes = [
            ((0, -1), (0, 1)),    # horizontal
            ((-1, 0), (1, 0)),    # vertical
            ((-1, -1), (1, 1)),   # diagonale \
            ((-1, 1), (1, -1)),   # diagonale /
        ]

        for direction_1, direction_2 in axes:
            count = 1  # Le dernier jeton joué

            for dr, dc in (direction_1, direction_2):
                r = start_r + dr
                c = start_c + dc

                while (
                    0 <= r < HEIGHT
                    and 0 <= c < WIDTH
                    and self.grid[r][c] == player
                ):
                    count += 1
                    r += dr
                    c += dc

            if count >= 4:
                return True

        return False