import socket
import threading
import time
import select
from collections import defaultdict

class IRCServer:
    def __init__(self, host='0.0.0.0', port=6667):
        self.host = host
        self.port = port
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.channels = defaultdict(set)  # channel: set of clients
        self.clients = {}  # client: {'nick': nick, 'channels': set}
        self.nicknames = {}  # nick: client
        self.running = True
        self.start_time = time.time()

    def start(self):
        self.server.bind((self.host, self.port))
        self.server.listen()
        print(f"🚀 Server started at {self.host}:{self.port}")
        print(f"🕒 Server uptime: {self.get_uptime()}")
        
        try:
            while self.running:
                readable, _, _ = select.select([self.server] + list(self.clients.keys()), [], [], 1)
                for sock in readable:
                    if sock is self.server:
                        self.accept_connection()
                    else:
                        self.handle_client(sock)
        except KeyboardInterrupt:
            print("\n🛑 Server shutting down...")
        finally:
            self.shutdown()

    def get_uptime(self):
        uptime = int(time.time() - self.start_time)
        hours, remainder = divmod(uptime, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours}h {minutes}m {seconds}s"

    def accept_connection(self):
        client, addr = self.server.accept()
        print(f"🔌 New connection from {addr}")
        self.clients[client] = {'nick': None, 'channels': set()}
        client.send("NOTICE Welcome to PyIRC Server!\r\n".encode('utf-8'))
        client.send("NOTICE Please set your nickname with: /nick <nickname>\r\n".encode('utf-8'))

    def handle_client(self, client):
        try:
            data = client.recv(1024).decode('utf-8').strip()
            if not data:
                raise ConnectionError("Client disconnected")
                
            print(f"📩 Received: {data}")
            
            if data.startswith('NICK '):
                self.handle_nick(client, data[5:])
            elif data.startswith('JOIN '):
                self.handle_join(client, data[5:])
            elif data.startswith('PRIVMSG '):
                self.handle_message(client, data[8:])
            elif data == 'LIST':
                self.handle_list(client)
            elif data == 'QUIT':
                self.remove_client(client)
            elif data == 'TIME':
                client.send(f"NOTICE Server time: {time.ctime()}\r\n".encode('utf-8'))
            elif data == 'STATS':
                stats = (
                    f"NOTICE ⚡ Server Stats ⚡\r\n"
                    f"NOTICE Uptime: {self.get_uptime()}\r\n"
                    f"NOTICE Clients: {len(self.clients)}\r\n"
                    f"NOTICE Channels: {len(self.channels)}\r\n"
                )
                client.send(stats.encode('utf-8'))
            else:
                client.send("NOTICE Unknown command\r\n".encode('utf-8'))
        except Exception as e:
            print(f"⚠️ Error: {e}")
            self.remove_client(client)

    def handle_nick(self, client, nick):
        if nick in self.nicknames:
            client.send(f"NOTICE Nickname '{nick}' is already in use\r\n".encode('utf-8'))
            return
            
        old_nick = self.clients[client]['nick']
        self.clients[client]['nick'] = nick
        self.nicknames[nick] = client
        
        if old_nick:
            del self.nicknames[old_nick]
            self.broadcast(f"NOTICE {old_nick} is now known as {nick}", None)
        client.send(f"NOTICE Your nickname is now {nick}\r\n".encode('utf-8'))

    def handle_join(self, client, channel):
        if not channel.startswith('#'):
            channel = '#' + channel
            
        nick = self.clients[client]['nick']
        if not nick:
            client.send("NOTICE Set your nickname first with /nick\r\n".encode('utf-8'))
            return
            
        self.channels[channel].add(client)
        self.clients[client]['channels'].add(channel)
        
        # Notify channel
        self.broadcast(f"NOTICE {nick} joined {channel}", channel)
        client.send(f"JOIN {channel}\r\n".encode('utf-8'))
        
        # Send topic
        client.send(f"TOPIC {channel} :Welcome to {channel}!\r\n".encode('utf-8'))

    def handle_message(self, client, data):
        nick = self.clients[client]['nick']
        if not nick:
            client.send("NOTICE Set your nickname first with /nick\r\n".encode('utf-8'))
            return
            
        target, _, message = data.partition(' ')
        if not message:
            return
            
        if target.startswith('#'):
            # Channel message
            if target in self.channels and client in self.channels[target]:
                self.broadcast(f"PRIVMSG {nick} :{message}", target)
            else:
                client.send(f"NOTICE You're not in {target}\r\n".encode('utf-8'))
        else:
            # Private message
            if target in self.nicknames:
                self.nicknames[target].send(
                    f"PRIVMSG {nick} :{message}\r\n".encode('utf-8')
                )
            else:
                client.send(f"NOTICE User {target} not found\r\n".encode('utf-8'))

    def handle_list(self, client):
        response = "NOTICE 🟢 Active Channels:\r\n"
        for channel, members in self.channels.items():
            response += f"NOTICE {channel} ({len(members)} users)\r\n"
        client.send(response.encode('utf-8'))

    def broadcast(self, message, channel, exclude=None):
        targets = []
        if channel:
            targets = self.channels[channel]
        else:
            targets = self.clients.keys()
        
        for target in targets:
            if target != exclude:
                try:
                    target.send(f"{message}\r\n".encode('utf-8'))
                except:
                    self.remove_client(target)

    def remove_client(self, client):
        if client not in self.clients:
            return
            
        nick = self.clients[client]['nick']
        channels = self.clients[client]['channels'].copy()
        
        if nick:
            del self.nicknames[nick]
            self.broadcast(f"NOTICE {nick} has quit", None)
            
        for channel in channels:
            self.channels[channel].discard(client)
            if not self.channels[channel]:
                del self.channels[channel]
            self.broadcast(f"NOTICE {nick} left {channel}", channel)
        
        del self.clients[client]
        client.close()
        print(f"🔌 Client disconnected: {nick if nick else 'Unknown'}")

    def shutdown(self):
        self.broadcast("NOTICE Server is shutting down!", None)
        for client in list(self.clients.keys()):
            self.remove_client(client)
        self.server.close()
        print("🛑 Server stopped")

if __name__ == "__main__":
    import sys
    host = sys.argv[1] if len(sys.argv) > 1 else '0.0.0.0'
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 6667
    
    server = IRCServer(host, port)
    server.start()
