import random
import logging
import socketio
import uvicorn
import asyncio
from power_four import PowerFour

from typing import Any

logging.basicConfig(
    filename="server.log",
    format="{asctime} - {levelname} - {message}",
    style="{",
    datefmt="%Y-%m-%d %H:%M",
)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

sio = socketio.AsyncServer(
    async_mode="asgi",
    ping_interval=20,  # en secondes
    ping_timeout=15,   # en secondes
) #ASG = asynchronous getway app

app = socketio.ASGIApp(sio)

id_room = 0

clients: dict[str,dict[str,Any]] = {}#sid,user,idroom
rooms: dict[int,set[str]] = {0:set()}
games: dict[int,asyncio.Task[Any]] = {}#{id_room:0, task:play()}

@sio.on('NEW_MESSAGE')
async def treat_player_msg(sid: str, msg: str) -> None:
    #print(f"message recu: {msg}")
    logger.info(f'Received message: {msg}| Tranfer to players')

    id_room = clients[sid]["idroom"]
    username = clients[sid]["user"]

    await sio.emit('NOTIFY',{
        "username": username, 
        "message": msg},
    room = id_room)

@sio.event
async def connect(sid: str, environement: dict[str,str], auth: dict[str,str]) -> None:
    global id_room
    logger.info('Asking client for username')
    clients[sid] = {"user":auth.get('username'),"idroom":id_room}
    await sio.emit("NOTIFY",{"username":"system", "message":f"your username = {auth.get('username')}"},to=sid)

    logger.info(f'Client responded with {auth.get('username')}')
    rooms.setdefault(id_room,set())
    rooms[id_room].add(sid)
    await sio.enter_room(sid, id_room)

    logger.info(f'User {auth.get('username')} placed in room {id_room}')
    #print(f'{auth.get('username')} - {sid}c\'est connecté à la room{id_room}')

    if len(rooms[id_room]) == 2:
        logger.info(f'Two players in room {id_room}')
        games[id_room] = asyncio.create_task(play(id_room))

        logger.info('Starting Game')
        #print("game start")
        id_room+=1

@sio.event
async def disconnect(sid: str, reason: str) -> None:
    global id_room

    logger.info(f'Client {sid} disconnected - reason: {reason}')
    #print(f"{clients[sid]["user"]} - {reason}")

    id_room_sid = clients.pop(sid)["idroom"]
    if id_room_sid in rooms:
        logger.info(f'Clearing room {id_room_sid}')
        rooms[id_room_sid].discard(sid)
        task = games.pop(id_room_sid,None)

        if task is not None:
            logger.info(f'Cancelling task: {task.get_name()}')
            task.cancel

        # Old case to prevent empty room
        # if id_room_sid == id_room:
        #     id_room += 1
        
        if len(rooms[id_room_sid]) > 0:
            p2 = rooms[id_room_sid].pop()
            rooms.pop(id_room_sid)

            logger.info(f'Disconnecting last player in room {id_room_sid}')
            await sio.disconnect(p2)
        else: 
            rooms.pop(id_room_sid)
    
async def play(id_room: int) -> None:
    p1, p2 = rooms[id_room]

    coin = random.randint(1,2)
    if coin %2 ==0:
        p1, p2 = p2, p1
    
    game = PowerFour()
    active_name = ""
    is_won = False
    turn = 0

    logger.info('Game Start')
    #print("game start")
    await sio.emit("NOTIFY",{"username":"system", "message":f"Game start! {clients[p1]["user"]} vs {clients[p2]["user"]}"},room= id_room)
    while not is_won:
        await sio.emit('SHOW_GRID', game.grid, room=id_room) 

        if turn %2== 1:
            active_player = p2
            no_player = 2
        else:
            active_player = p1
            no_player = 1
        active_name = clients[active_player]["user"]
        
        #get response active_player
        await sio.emit("NOTIFY", {
            "username":"system", 
            "message":f"turn = {turn+1} - active player = {active_name}"
        }, room= id_room)

        logger.info("Ask active player his move")
        col = -1
        while True:
            try:
                col = await sio.call(
                    "ASK_COL",
                    to=active_player,
                    timeout=60,
                )
            except socketio.exceptions.TimeoutError:
                logger.warning("Timeout before receiving response from client")
                await sio.emit(
                    "NOTIFY",
                    {
                        "username": "system",
                        "message": f"{active_name} did'nt respond in time - disconnecting both player",
                        
                    },
                    room=id_room,
                )
                await sio.disconnect(p2)
                return

            logger.info(f"Player move: {col}")
            #print(col)
            is_valid = game.add_chip(no_player, col)
            #print(is_valid) 

            if not(is_valid):
                logger.info("Invalid move, ask active player again")
                #print("col not valid")
                await sio.emit('NOTIFY',{"username":"system", "message":"Col not valid"}, to = active_player)
                continue

            logger.info("Notify players of the active player move")
            await sio.emit('NOTIFY',{"username":"system", "message":f"{active_name} played {game.get_formated_last_chip()}"}, room = id_room)
            break
            
        if turn >= 6:
            is_won = game.is_won() 
            if is_won:
                logger.info("Game won by active player, notify the players")
                await sio.emit('SHOW_GRID', game.grid, room=id_room)
                await sio.emit('NOTIFY',{"username":"system", "message": f"player: {active_name} has won"},room = id_room)
                
        turn+=1

if __name__ == '__main__':
    logger.info('Starting server...')
    uvicorn.run('main:app', host='127.0.0.1', port=8000, reload=True)