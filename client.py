import os
import socketio # pyright: ignore[reportMissingTypeStubs]
import asyncio
import curses
import curses.ascii
import curses.textpad
import threading
from collections import deque

from dotenv import load_dotenv

from typing import Any

sio: socketio.AsyncClient = socketio.AsyncClient()

messages: deque[str]|None = None

grid_win: curses.window|None = None
msg_win: curses.window|None = None
input_win: curses.window|None = None

input_lock: asyncio.Lock = asyncio.Lock()
interrupt_flag = threading.Event()

def is_integer(n: str):
    try:
        float(n)
    except ValueError:
        return False
    else:
        return float(n).is_integer()

def edit_validator(ch: str|int) -> str|int:
    if interrupt_flag.is_set():
        return curses.ascii.BEL
    if ch == -1:    # timeout, personne n'a tapé
        return 0    # "if not ch: continue" dans edit() -> on reboucle proprement
    return ch

@sio.on('NOTIFY')
def handle_notify(message: dict[str,Any] = None):
    assert msg_win is not None
    assert input_win is not None

    msg_win.clear()
    msg_win.border()
    if message:
        messages.append(message)

    y=1
    for msg in messages:
        msg_win.addstr(y, 1, f"{msg.get('username')}: {msg.get('message')}\n")
        y+=1

    msg_win.refresh()

    # focus back on the input window
    input_win.clear()
    input_win.refresh()

@sio.on('SHOW_GRID')
def handle_grid(grid: list[list[str]]):
    assert grid_win is not None
    assert input_win is not None

    colors = {'1': curses.COLOR_RED, '2': curses.COLOR_YELLOW}

    grid_win.clear()
    grid_win.border()

    width = len(grid[0])
    height = len(grid)

    x,y = 1,1

    grid_win.addch(y, x, '┌')
    x += 1
    for c in range(width):
        grid_win.addstr(y, x, '───')
        x += 3
        if c != (width-1):
            grid_win.addch(y, x, '┬')
            x += 1
    grid_win.addch(y, x, '┐')
    y += 1

    for r,line in enumerate(grid):
        # row
        x = 1
        grid_win.addch(y, x, '│')
        x += 1
        for i,c in enumerate(line):
            if c in {'1','2'}:
                grid_win.addstr(y, x, ' ● ', curses.color_pair(colors.get(c, 0)))
            else:
                grid_win.addstr(y, x, ' ○ ')
            x += 3
            if i != (width-1):
                grid_win.addch(y, x, '│')
                x += 1
        grid_win.addch(y, x, '│')
        y += 1

        # row separator
        if r != height-1:
            x = 1
            grid_win.addch(y, x, '├')
            x += 1
            for c in range(width):
                grid_win.addstr(y, x, '───')
                x += 3
                if c != (width-1):
                    grid_win.addch(y, x, '┼')
                    x += 1
            grid_win.addch(y, x, '┤')
            y += 1

    x = 1
    grid_win.addch(y, x, '└')
    x += 1
    for c in range(width):
        grid_win.addstr(y, x, '───')
        x += 3
        if c != (width-1):
            grid_win.addch(y, x, '┴')
            x += 1
    grid_win.addch(y, x, '┘')

    grid_win.refresh()

    # focus back on the input window
    input_win.clear()
    input_win.refresh()

@sio.on('ASK_COL')
async def handle_ask_col():
    assert msg_win is not None
    assert input_win is not None
    interrupt_flag.set()        # signale la coupure au plus vite

    async with input_lock:
        await asyncio.sleep(0.05)
        interrupt_flag.clear()
        loop = asyncio.get_event_loop()
        input = 'None'
        while not is_integer(input):
            curses.flushinp()
            box = curses.textpad.Textbox(input_win)
            box.win.timeout(100)
            input = await loop.run_in_executor(None, box.edit, edit_validator)
        input_win.clear()
        input_win.refresh()
        return int(input)

async def listen_input():
    """ Handle textbx input when the player is waiting for his turn """
    assert msg_win is not None
    assert input_win is not None
    loop = asyncio.get_event_loop()

    while True:
        if not input_lock.locked():
            async with input_lock:
                await asyncio.sleep(0.05)
                loop = asyncio.get_event_loop()
                box = curses.textpad.Textbox(input_win)
                box.win.timeout(100)
                msg = await loop.run_in_executor(None, box.edit, edit_validator)
                if interrupt_flag.is_set():
                    interrupt_flag.clear()
                    continue
                await sio.emit('NEW_MESSAGE', msg)
                input_win.clear()
                input_win.refresh()
        else:
            await asyncio.sleep(0.05)

async def main(screen: curses.window):
    global msg_win, input_win, grid_win, messages

    screen.clear()
    screen.refresh()

    curses.init_pair(curses.COLOR_RED,
                     curses.COLOR_RED,
                     curses.COLOR_BLACK)
    curses.init_pair(curses.COLOR_YELLOW,
                     curses.COLOR_YELLOW,
                     curses.COLOR_BLACK)

    grid_win = curses.newwin(curses.LINES, curses.COLS//2, 0, 0)
    grid_win.border()
    grid_win.refresh()

    msg_win = curses.newwin(curses.LINES - 3, curses.COLS//2, 0, curses.COLS//2 + 1)
    messages = deque([], maxlen=msg_win.getmaxyx()[0] - 2)

    msg_win.border()
    msg_win.refresh()
    
    input_win = curses.newwin(1, curses.COLS//2, curses.LINES - 2, curses.COLS//2 + 1)

    await sio.connect(
        os.getenv('HOST'),
        auth = {"username": await get_username()}
    )

    asyncio.create_task(listen_input())

    await sio.wait()

async def get_username():
    messages.append({"username":"client","message":"enter a user"})
    refresh_message_window()
    while True:
        await asyncio.sleep(0.05)
        input_win.nodelay(True)
        curses.flushinp()
        box = curses.textpad.Textbox(input_win)
        box.edit()
        message = box.gather().strip()
        input_win.clear()
        input_win.refresh()
        if len(message)==0:
            continue
        try:
            messages.append({"username":"client","message":f"user choose:{message}"})
            refresh_message_window()
            return message
        except ValueError:
            message.spop()
            continue

def refresh_message_window():
    assert msg_win is not None
    msg_win.clear()
    msg_win.border()
    y=1
    for msg in messages:
        msg_win.addstr(y, 1, f"{msg.get('username')}: {msg.get('message')}\n")
        y+=1
    msg_win.refresh()

load_dotenv()
curses.wrapper(lambda screen: asyncio.run(main(screen)))