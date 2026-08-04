from const import WIDTH,HEIGHT,EMPTY_SYMB

class PowerFour():
    def __init__(self):
        self.grid = [[EMPTY_SYMB for _ in range(WIDTH)]for _ in range(HEIGHT)] 
        self.last_chip_played = (-1,-1)

    def get_formated_last_chip(self):
        x = self.last_chip_played[1]+1
        y = 6 - (self.last_chip_played[0])
        return (x,y)
    def add_chip(self,no_player, col):
        print(bool(0<= int(col) < WIDTH))
        print(f"add chip({no_player}, {col})")
        if bool(0<= int(col) <WIDTH):
            for j in range(HEIGHT-1, -1,-1):
                print(f"j={j}")
                if self.grid[j][col] == EMPTY_SYMB:
                    self.grid[j][col] = str(no_player)
                    self.last_chip_played = (j,col)
                    print("valid")
                    return True
        print('invalid')
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