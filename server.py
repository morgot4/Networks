import selectors, socket, sys, sqlite3, random
from datetime import datetime


sel = selectors.DefaultSelector()
connections = {}
params = []
db = sqlite3.connect('server.db')
sql = db.cursor()
sql.execute("""CREATE TABLE IF NOT EXISTS users (login TEXT, password TEXT, room TEXT)""")
sql.execute("""CREATE TABLE IF NOT EXISTS rooms (name TEXT, password TEXT)""")
db.commit()

for param in sys.argv:
    if param != 'server.py':
        params.append(param)

IP = params[0]
PORT = params[1]

def command_handler(connection, data):
    words = data.split(' ')
    if words[0] == '/create':
        name = words[1]
        # name_to_check = sql.execute(f'SELECT name FROM rooms WHERE name = "{name}"')
        if sql.fetchone() is None:
            password = code_generator()
            sql.execute('INSERT INTO rooms VALUES (?,?)', (name, password))
            connection.send(f'{name} successfully created.\n Your password => {password}'.encode())
            sql.execute(f'UPDATE users SET room = "{name}" WHERE login = "{connections[connection][1]}"')
            db.commit()
        else:
            connection.send('This name is already exist:'.encode())

    elif words[0] == '/join':
        name = words[1]
        password = words[2]
        really_password = sql.execute(f'SELECT password FROM rooms WHERE name = "{name}"').fetchone()
        if sql.fetchone() is None:
            connection.send('This name doesn`t exist:'.encode())
        else:
            print(password, really_password)
            if str(password) == really_password[0]:
                connection.send('You joined in room'.encode())
                sql.execute(f'UPDATE users SET room = "{name}" WHERE login = "{connections[connection][1]}"')
                db.commit()

    elif words[0] == '/exit':
        sql.execute(f'UPDATE users SET room = "{0}" WHERE login = "{connections[connection][1]}"')
        db.commit()
    else:
        connection.send('Unknown command'.encode())

def code_generator():
    symbols = ['A', 'B', 'C', 'D','E', 'F', 'G', 'H','Q', 'W', 'R', 'T','Y', 'U', 'I', 'O','P', 'S', 'J', 'K','L', 'Z', 'X', 'V', 'N', 'M', '1', '2', '3', '4', '5','6', '7', '8', '9']
    code = ''
    for i in range(6):
        symbol = random.choice(symbols)
        code+=symbol
    return code


def log_in(connection):
    username = connection.recv(1024).decode().replace('\n','')
    really_username = sql.execute(f'SELECT login FROM users WHERE login = "{username}"')
    if sql.fetchone() is None:
        sel.unregister(connection)
        sel.register(connection, selectors.EVENT_READ, registration)
        connection.send('This account has not been created. Please register\n'.encode())
        message = 'Registration\n'
        connection.send(message.encode())
        connection.send('Username:'.encode())
    else:
        connection.send('Password:'.encode())
        password = connection.recv(1024).decode().replace('\n','')
        really_password = sql.execute(f'SELECT password FROM users WHERE login = "{username}"').fetchone()
        if str(password) == really_password[0]:
            connection.send('Log in successfully\n'.encode())
            connection.setblocking(False)
            connections[connection].append(username)
            sel.unregister(connection)
            sel.register(connection, selectors.EVENT_READ, read)
            message = f'{username} has entered the chat'
            message = '$' + message + '$'
            for connection in connections.keys():
                try:
                    connection.send(message.encode())
                except BrokenPipeError:
                    pass
        else:
            connection.close()
    
            

def registration(connection):
    username = connection.recv(1024).decode().replace('\n','')
    connection.send('Password:'.encode())
    password = connection.recv(1024).decode().replace('\n','')
    connection.send('Repeat password:'.encode())
    reapet_password = connection.recv(1024).decode().replace('\n','')
    
    if password == reapet_password:
        connection.send('Registration successfully\n'.encode())
        sql.execute(f'INSERT INTO users VALUES (?,?,?)', (username,password, '0'))
        db.commit()
        sel.unregister(connection)
        sel.register(connection, selectors.EVENT_READ, log_in)
        message = 'Log in\n'
        connection.send(message.encode())
        connection.send('Username:'.encode())
    else:
        connection.close()
    

def start(socket):
    global connections
    connection, address = socket.accept()
    address = address[0]
    connections[connection] = [address]
    sel.register(connection, selectors.EVENT_READ, accept)
    message = 'Registration or Log in. Write [ Log / Reg ]\n'
    connection.send(message.encode())

def accept(connection):
    global connections
    
    # message = 'Registration or Log in. Write [ Log / Reg ]\n'
    # connection.send(message.encode())
    data = connection.recv(1024).decode().replace('\n','')
    if data.lower() == 'log':
        sel.unregister(connection)
        sel.register(connection, selectors.EVENT_READ, log_in)
        message = 'Log in\n'
        connection.send(message.encode())
        connection.send('Username:'.encode())
        
    elif data.lower() == 'reg':
        sel.unregister(connection)
        sel.register(connection, selectors.EVENT_READ, registration)
        message = 'Registration\n'
        connection.send(message.encode())
        connection.send('Username:'.encode())
    else:
        connection.close()
    
    


def read(connection):
    # try:
        room = sql.execute(f'SELECT room FROM users WHERE login = "{connections[connection][1]}"').fetchone()
        data = connection.recv(1024).decode().strip('\n')
        if data:
            
                
            print('from', connection.getpeername(), 'received', repr(data))
            for client, address in connections.items():
                if data[0] == '/':
                    command_handler(connection, data)
                    break
                room2 = sql.execute(f'SELECT room FROM users WHERE login = "{address[1]}"').fetchone()
                print(room[0], room2[0])
                if room[0] == room2[0]:
                    if client != connection:
                        message = connections[connection][1]+'(' + datetime.now().strftime('%H:%M') + ')' + data
                        client.send(message.encode())

    # except:

    #     message = f'{connections[connection][1]} has left the chat'
    #     message = '$' + message + '$'
    #     for connection in connections.keys():
    #         try:
    #             connection.send(message.encode())
    #         except BrokenPipeError:
    #             pass
        # sock.close()
                

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind((IP, int(PORT)))
sock.listen(100)
sock.setblocking(False)
sel.register(sock, selectors.EVENT_READ, start)

while True:
    events = sel.select()
    for key, mask in events:
        callback = key.data
        try:
            callback(key.fileobj)
        except BrokenPipeError:
            pass