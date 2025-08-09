import socket
import threading
import time
from collections import defaultdict

class Channel:
    def __init__(self, name):
        self.name = name
        self.members = set()
        self.modes = {
            't': True,   # Topic protection
            'n': True,   # No external messages
            's': False,  # Secret channel
            'k': None,   # Password
            'l': None    # User limit
        }
        self.topic = f"Welcome to {name}!"
        self.creation_time = time.time()
        self.ops = set()

class IRCServer:
    def __init__(self, host='0.0.0.0', port=6667):
        self.host = host
        self.port = port
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.channels = {
            '#main': Channel('#main'),
            '#general': Channel('#general'),
            '#help': Channel('#help')
        }
        self.clients = {}  # {socket: {'nick': str, 'channels': set}}
        self.nicknames = {}  # {nick: socket}
        self.running = True

    def start(self):
        self.server.bind((self.host, self.port))
        self.server.listen()
        print(f"🚀 Server started on {self.host}:{self.port}")
        print(f"Default channels: {', '.join(self.channels.keys())}")
        self.accept_connections()

    def accept_connections(self):
        while self.running:
            try:
                client, addr = self.server.accept()
                threading.Thread(target=self.handle_client, args=(client,)).start()
            except OSError:
                break

    def handle_client(self, client):
        nick = None
        try:
            while True:
                data = client.recv(4096).decode('utf-8').strip()
                if not data:
                    break

                if data.startswith('NICK '):
                    nick = self.handle_nick(client, data[5:])
                elif data.startswith('USER '):
                    self.send_notice(client, "Welcome! Use /join #channel")
                elif data.startswith('JOIN '):
                    self.handle_join(client, data[5:])
                elif data.startswith('MODE '):
                    self.handle_mode(client, data[5:])
                elif data.startswith('PRIVMSG '):
                    self.handle_privmsg(client, data[8:])
                elif data.startswith('WHOIS '):
                    self.handle_whois(client, data[6:])
                elif data == 'LIST':
                    self.handle_list(client)
                elif data.startswith('TOPIC '):
                    self.handle_topic(client, data[6:])
                elif data.startswith('KICK '):
                    self.handle_kick(client, data[5:])
                elif data == 'QUIT':
                    break
                elif data.startswith('PING'):
                    client.send(f"PONG {data[5:]}\r\n".encode())
        finally:
            self.remove_client(client, nick)

    def handle_nick(self, client, nick):
        if nick in self.nicknames:
            self.send_notice(client, f"Nickname {nick} is already in use")
            return None
        
        if client in self.clients:
            old_nick = self.clients[client].get('nick')
            if old_nick:
                del self.nicknames[old_nick]
        
        self.clients[client] = {'nick': nick, 'channels': set()}
        self.nicknames[nick] = client
        return nick

    def handle_join(self, client, channel_name):
        if not channel_name.startswith('#'):
            channel_name = '#' + channel_name

        if client not in self.clients:
            self.send_notice(client, "Set your nickname first with NICK")
            return

        nick = self.clients[client]['nick']
        
        if channel_name not in self.channels:
            self.channels[channel_name] = Channel(channel_name)
        
        channel = self.channels[channel_name]
        
        # Check channel modes
        if channel.modes['k']:
            self.send_notice(client, "This channel requires a password")
            return
        if channel.modes['l'] and len(channel.members) >= channel.modes['l']:
            self.send_notice(client, "Channel is full")
            return

        channel.members.add(client)
        self.clients[client]['channels'].add(channel_name)
        
        self.send_notice(client, f"Joined {channel_name}")
        self.broadcast(f"{nick} joined {channel_name}", channel_name, exclude=client)

    def handle_mode(self, client, data):
        parts = data.split()
        if len(parts) < 2:
            return

        channel = parts[0]
        mode = parts[1]
        
        if channel not in self.channels:
            self.send_notice(client, f"Channel {channel} doesn't exist")
            return

        if mode.startswith('+'):
            if 'k' in mode and len(parts) > 2:
                self.channels[channel].modes['k'] = parts[2]  # Set password
            elif 'l' in mode and len(parts) > 2:
                self.channels[channel].modes['l'] = int(parts[2])  # Set user limit
        elif mode.startswith('-'):
            if 'k' in mode:
                self.channels[channel].modes['k'] = None  # Remove password

        self.broadcast(f"MODE {channel} {mode}", channel)

    def handle_privmsg(self, client, data):
        if client not in self.clients:
            return

        nick = self.clients[client]['nick']
        target, _, message = data.partition(' :')
        
        if target.startswith('#'):
            if target in self.channels and client in self.channels[target].members:
                self.broadcast(f"{nick} PRIVMSG {target} :{message}", target)
        else:
            if target in self.nicknames:
                self.send_privmsg(self.nicknames[target], nick, message)

    def handle_whois(self, client, nick):
        if nick in self.nicknames:
            target_client = self.nicknames[nick]
            channels = ', '.join(self.clients[target_client]['channels'])
            self.send_notice(client, f"{nick} is on channels: {channels}")
        else:
            self.send_notice(client, f"{nick}: No such user")

    def handle_list(self, client):
        for channel_name, channel in self.channels.items():
            self.send_notice(client, f"{channel_name} ({len(channel.members)} users)")

    def handle_topic(self, client, data):
        channel, _, topic = data.partition(' :')
        if channel in self.channels:
            self.channels[channel].topic = topic
            self.broadcast(f"TOPIC {channel} :{topic}", channel)

    def handle_kick(self, client, data):
        channel, _, rest = data.partition(' ')
        target, _, reason = rest.partition(' :')
        
        if (channel in self.channels and 
            client in self.channels[channel].members and
            target in self.nicknames):
            
            target_client = self.nicknames[target]
            if target_client in self.channels[channel].members:
                self.channels[channel].members.remove(target_client)
                self.send_notice(target_client, f"You were kicked from {channel}: {reason}")
                self.broadcast(f"{target} was kicked by {self.clients[client]['nick']}", channel)

    def broadcast(self, message, channel_name, exclude=None):
        if channel_name in self.channels:
            for client in self.channels[channel_name].members:
                if client != exclude:
                    try:
                        client.send(f"{message}\r\n".encode('utf-8'))
                    except:
                        self.remove_client(client)

    def send_notice(self, client, message):
        try:
            client.send(f"NOTICE :{message}\r\n".encode('utf-8'))
        except:
            self.remove_client(client)

    def send_privmsg(self, client, sender, message):
        try:
            client.send(f"{sender} PRIVMSG :{message}\r\n".encode('utf-8'))
        except:
            self.remove_client(client)

    def remove_client(self, client, nick=None):
        if client in self.clients:
            if not nick:
                nick = self.clients[client]['nick']
            for channel in list(self.clients[client]['channels']):
                if channel in self.channels and client in self.channels[channel].members:
                    self.channels[channel].members.remove(client)
                    self.broadcast(f"{nick} has left {channel}", channel)
            if nick in self.nicknames:
                del self.nicknames[nick]
            del self.clients[client]
            client.close()

    def stop(self):
        self.running = False
        self.server.close()

if __name__ == "__main__":
    server = IRCServer()
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()
        print("\nServer stopped")
