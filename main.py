import socketio
import uvicorn
import asyncio
from power_four import PowerFour

sio = socketio.AsyncServer(async_mode='asgi') #ASG = asynchronous getway app
app = socketio.ASGIApp(sio)
clients={}#sid,name,idroom
id_room =0
rooms={0:[]}
games={}#{id_room:0, task:play()}

@sio.event
async def connect(sid, environement, auth):
    global id_room
    #username = await sio.emit('LOGIN',{"username":"system", "message":"Please enter a username"})
    clients[sid]={"user":auth.get('username'),"idroom":id_room}
    await sio.emit("NOTIFY",{"username":"system", "message":f"your username = {auth.get('username')}"},to=sid)
    rooms.setdefault(id_room,[])
    rooms[id_room].append(sid)
    await sio.enter_room(sid, id_room)
    print(f'{auth.get('username')} - {sid}c\'est connecté à la room{id_room}')
    if len(rooms[id_room])==2:
        games[id_room] = asyncio.create_task(play(id_room))
        print("game start")
        id_room+=1

@sio.event
async def disconnect(sid):
    global id_room
    id_room_to_disc = clients[sid]["idroom"]
    for c in rooms[id_room_to_disc]:
        await sio.leave_room(c, room = id_room_to_disc)
        print(f"{clients.get(c)} - {c} c'est deconnecté de la room {id_room_to_disc}")
    if id_room_to_disc == id_room:
        id_room+=1
    rooms.pop(id_room_to_disc)
    games[id_room_to_disc].cancel()
    games.pop(id_room_to_disc)
    
    clients.pop(sid)
    
    

async def play(id_room):
    p1,p2 = rooms[id_room]
    game = PowerFour()
    active_name=""
    is_won = False
    turn=0
    print("game start")
    await sio.emit("NOTIFY",{"username":"system", "message":f"Game start! {clients[p1]["user"]} vs {clients[p2]["user"]}"},room= id_room)
    while not is_won:
        await sio.emit('SHOW_GRID', game.grid, room=id_room) 
        if turn%2==1:
            active_player = p2
            active_name = clients[p2]["user"]
            no_player =2
        else:
            active_player = p1
            active_name = clients[p1]["user"]
            no_player = 1
        #get response active_player
        print(f"turn: {active_player}")

        col = -1
        while True:
            col=await sio.call('ASK_COL', to=active_player)
            print(col)
            is_valid =game.add_chip(no_player, col)
            print(is_valid) 
            if not(is_valid):
                print("col not valid")
                await sio.emit('NOTIFY',{"username":"system", "message":"Col not valid"}, to = active_player)
                continue
            await sio.emit('NOTIFY',{"username":"system", "message":f"{active_name} played {game.get_formated_last_chip()}"}, room = id_room)
            break
            
        if turn>=6:
            is_won =game.is_won() 
            if is_won:
                await sio.emit('SHOW_GRID', game.grid, room=id_room)
                await sio.emit('NOTIFY',{"username":"system", "message": f"player: {active_name} has won"},room = id_room)
                
        turn+=1


@sio.on('NEW_MESSAGE')
async def treat_player_msg(sid,msg):
    print(f"message recu: {msg}")
    id_room = clients[sid]["idroom"]
    username = clients[sid]["user"]
    await sio.emit('NOTIFY',{
        "username":username, 
        "message": msg},
    room = id_room)
    
    

if __name__ == '__main__':
    uvicorn.run('main:app', host='127.0.0.1', port=8000, reload=True)