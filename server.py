import socket
import threading
import time
import datetime
import sys
import select
import ssl

# ANSI color codes
class Colors:
    RESET = '\033[0m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    GRAY = '\033[90m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class Channel:
    def __init__(self, name):
        self.name = name
        self.members = set()
        self.created = datetime.datetime.now()

class IRCServer:
    def __init__(self, host='0.0.0.0', port=6667, ssl_cert=None, ssl_key=None):  # SSL PARAMS ADDED
        self.host = host
        self.port = port
        self.ssl_cert = ssl_cert
        self.ssl_key = ssl_key
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # SSL CONTEXT ADDED
        if self.ssl_cert and self.ssl_key:
            self.context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            self.context.load_cert_chain(certfile=self.ssl_cert, keyfile=self.ssl_key)
            
        self.channels = {}
        self.default_channels = ['#main', '#general', '#help']
        for channel in self.default_channels:
            self.channels[channel] = Channel(channel)
            
        self.clients = {}
        self.nicknames = {}
        self.banned_ips = set()
        self.running = True
        self.log_file = "server.log"
        self.admin_password = input("Set admin password [admin123]:") or "admin123"
        
        with open(self.log_file, 'a') as f:
            f.write(f"\n\n=== Server started at {datetime.datetime.now()} ===\n")

    def log(self, message, show=True):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        
        with open(self.log_file, 'a') as f:
            f.write(log_entry + "\n")
            
        if show:
            print(f"{Colors.GRAY}{log_entry}{Colors.RESET}")

    def start(self):
        # SSL WRAP ADDED
        if self.ssl_cert and self.ssl_key:
            self.server = self.context.wrap_socket(self.server, server_side=True)
        
        self.server.bind((self.host, self.port))
        self.server.listen()
        print("="*70)
        print(f"{Colors.BLUE} py-IRC Server {Colors.RESET}".center(70, '#'))
        print("="*70)
        ssl_status = f"{Colors.GREEN}Enabled{Colors.RESET}" if self.ssl_cert else f"{Colors.RED}Disabled{Colors.RESET}"
        print(f"{Colors.GREEN}●{Colors.RESET} Server started on {Colors.CYAN}{self.host}:{self.port}{Colors.RESET}")
        print(f"{Colors.GREEN}●{Colors.RESET} SSL/TLS: {ssl_status}")
        print(f"{Colors.GREEN}●{Colors.RESET} Default channels: {Colors.BLUE}{', '.join(self.default_channels)}{Colors.RESET}")
        print(f"{Colors.GREEN}●{Colors.RESET} Logging to: {Colors.YELLOW}{self.log_file}{Colors.RESET}")
        print(f"{Colors.GREEN}●{Colors.RESET} Admin password: {Colors.RED}{self.admin_password}{Colors.RESET}")
        print(f"{Colors.GREEN}●{Colors.RESET} Available admin commands: /kick, /ban, /unban, /channels, /addchannel, /removechannel, /msg, /broadcast, /shutdown")
        print("="*70)
        
        admin_thread = threading.Thread(target=self.admin_console)
        admin_thread.daemon = True
        admin_thread.start()
        
        self.log(f"Server started on {self.host}:{self.port}")
        self.accept_connections()

    def accept_connections(self):
        while self.running:
            try:
                client, addr = self.server.accept()
                ip = addr[0]
                
                if ip in self.banned_ips:
                    client.send(f"ERROR :Your IP has been banned from this server\r\n".encode())
                    client.close()
                    self.log(f"Banned IP tried to connect: {ip}")
                    continue
                    
                self.log(f"New connection from {ip}")
                threading.Thread(target=self.handle_client, args=(client, ip)).start()
            except OSError:
                break

    def handle_client(self, client, ip):
        self.clients[client] = {'nick': None, 'channels': set(), 'ip': ip}
        
        nick = None
        try:
            while self.running:
                rlist, _, _ = select.select([client], [], [], 1.0)
                if not rlist:
                    continue
                    
                data = client.recv(4096).decode('utf-8').strip()
                if not data:
                    break
                    
                self.log(f"RECV [{ip}]: {data}")

                if data.startswith('NICK '):
                    nick = self.handle_nick(client, data[5:], ip)
                    if nick:
                        client.send(f":server 001 {nick} :Welcome to the IRC server!\r\n".encode())
                        client.send(f":server 422 {nick} :MOTD file is missing\r\n".encode())
                elif data.startswith('USER '):
                    pass
                elif data.startswith('JOIN '):
                    self.handle_join(client, data[5:], ip)
                elif data.startswith('PRIVMSG '):
                    self.handle_privmsg(client, data[8:], ip)
                elif data.startswith('PING'):
                    client.send(f"PONG {data[5:]}\r\n".encode())
                elif data == 'QUIT':
                    break
                elif data.startswith('PART'):
                    channel = data.split()[1] if len(data.split()) > 1 else None
                    if channel:
                        self.handle_part(client, channel, ip)
        except Exception as e:
            self.log(f"Client error: {e}")
        finally:
            self.remove_client(client, nick, ip)

    def handle_nick(self, client, nick, ip):
        if nick in self.nicknames:
            client.send(f":server 433 * {nick} :Nickname is already in use\r\n".encode())
            return None
        
        if client in self.clients:
            old_nick = self.clients[client].get('nick')
            if old_nick and old_nick in self.nicknames:
                del self.nicknames[old_nick]
        
        self.clients[client]['nick'] = nick
        self.nicknames[nick] = client
        self.log(f"Nick registered: {nick} ({ip})")
        return nick

    def handle_join(self, client, channel_name, ip):
        if not channel_name.startswith('#'):
            channel_name = '#' + channel_name

        if client not in self.clients:
            return

        nick = self.clients[client]['nick'] or ip
        
        if channel_name not in self.channels:
            self.channels[channel_name] = Channel(channel_name)
            self.log(f"New channel created: {channel_name} by {nick}")
        
        channel = self.channels[channel_name]
        channel.members.add(client)
        self.clients[client]['channels'].add(channel_name)
        
        for member in channel.members:
            member.send(f":{nick} JOIN {channel_name}\r\n".encode())
        
        names = ' '.join([self.clients[m]['nick'] or self.clients[m]['ip'] for m in channel.members])
        client.send(f":server 353 {nick} = {channel_name} :{names}\r\n".encode())
        client.send(f":server 366 {nick} {channel_name} :End of /NAMES list\r\n".encode())
        
        self.log(f"{nick} joined {channel_name}")

    def handle_privmsg(self, client, data, ip):
        if client not in self.clients:
            return

        nick = self.clients[client]['nick'] or ip
        target, _, message = data.partition(' :')
        
        if target.startswith('#'):
            if target in self.channels and client in self.channels[target].members:
                for member in self.channels[target].members:
                    member.send(f":{nick} PRIVMSG {target} :{message}\r\n".encode())
                self.log(f"{nick} => {target}: {message}")
        else:
            if target in self.nicknames:
                target_client = self.nicknames[target]
                target_client.send(f":{nick} PRIVMSG {target} :{message}\r\n".encode())
                if client != target_client:
                    client.send(f":{nick} PRIVMSG {target} :{message}\r\n".encode())
                self.log(f"{nick} => {target}: {message}")

    def handle_part(self, client, channel_name, ip):
        if client not in self.clients:
            return
            
        nick = self.clients[client]['nick'] or ip
        if channel_name in self.channels and client in self.channels[channel_name].members:
            self.channels[channel_name].members.remove(client)
            self.clients[client]['channels'].remove(channel_name)
            
            for member in self.channels[channel_name].members:
                member.send(f":{nick} PART {channel_name}\r\n".encode())
            client.send(f":{nick} PART {channel_name}\r\n".encode())
            
            self.log(f"{nick} left {channel_name}")

    def remove_client(self, client, nick, ip):
        if client in self.clients:
            if not nick:
                nick = self.clients[client].get('nick', ip)
                
            for channel in list(self.clients[client]['channels']):
                if channel in self.channels and client in self.channels[channel].members:
                    self.channels[channel].members.remove(client)
                    for member in self.channels[channel].members:
                        if member != client:
                            member.send(f":{nick} QUIT :Connection closed\r\n".encode())
                            
            if 'nick' in self.clients[client] and self.clients[client]['nick'] in self.nicknames:
                del self.nicknames[self.clients[client]['nick']]
                
            del self.clients[client]
            client.close()
            self.log(f"Client disconnected: {nick} ({ip})")

    def admin_console(self):
        print()
        
        while self.running:
            try:
                cmd = input(f"{Colors.RED}ADMIN> {Colors.RESET}").strip()
                if not cmd:
                    continue
                    
                if cmd.startswith('/'):
                    parts = cmd[1:].split()
                    if not parts:
                        continue
                        
                    action = parts[0].lower()
                    
                    if action == 'kick':
                        if len(parts) > 1:
                            identifier = parts[1]
                            reason = ' '.join(parts[2:]) if len(parts) > 2 else "Kicked by admin"
                            self.admin_kick(identifier, reason)
                        else:
                            print(f"{Colors.RED}Usage: /kick <nick|ip> [reason]{Colors.RESET}")
                    
                    elif action == 'ban':
                        if len(parts) > 1:
                            identifier = parts[1]
                            self.admin_ban(identifier)
                        else:
                            print(f"{Colors.RED}Usage: /ban <nick|ip>{Colors.RESET}")
                    
                    elif action == 'unban':
                        if len(parts) > 1:
                            ip = parts[1]
                            self.admin_unban(ip)
                        else:
                            print(f"{Colors.RED}Usage: /unban <ip>{Colors.RESET}")
                    
                    elif action == 'channels':
                        self.admin_list_channels()
                    
                    elif action == 'addchannel':
                        if len(parts) > 1:
                            channel = parts[1]
                            self.admin_add_channel(channel)
                        else:
                            print(f"{Colors.RED}Usage: /addchannel <#channel>{Colors.RESET}")
                    
                    elif action == 'removechannel':
                        if len(parts) > 1:
                            channel = parts[1]
                            self.admin_remove_channel(channel)
                        else:
                            print(f"{Colors.RED}Usage: /removechannel <#channel>{Colors.RESET}")
                    
                    elif action == 'msg':
                        if len(parts) > 2:
                            target = parts[1]
                            message = ' '.join(parts[2:])
                            self.admin_message(target, message)
                        else:
                            print(f"{Colors.RED}Usage: /msg <target> <message>{Colors.RESET}")
                    
                    elif action == 'broadcast':
                        if len(parts) > 1:
                            message = ' '.join(parts[1:])
                            self.admin_broadcast(message)
                        else:
                            print(f"{Colors.RED}Usage: /broadcast <message>{Colors.RESET}")
                    
                    elif action == 'shutdown':
                        print(f"{Colors.RED}Shutting down server...{Colors.RESET}")
                        self.stop()
                        break
                    
                    else:
                        print(f"{Colors.RED}Unknown admin command{Colors.RESET}")
            except Exception as e:
                print(f"{Colors.RED}Admin error: {e}{Colors.RESET}")

    def admin_kick(self, identifier, reason):
        if identifier in self.nicknames:
            client = self.nicknames[identifier]
            nick = identifier
            client.send(f":server KICK {nick} :{reason}\r\n".encode())
            client.send(f"ERROR :You have been kicked from the server: {reason}\r\n".encode())
            self.remove_client(client, nick, self.clients[client]['ip'])
            self.log(f"ADMIN: Kicked {nick} - {reason}", show=False)
            print(f"{Colors.GREEN}Kicked {nick}{Colors.RESET}")
            return
            
        client_to_kick = None
        for client, info in self.clients.items():
            if info['ip'] == identifier:
                client_to_kick = client
                break
        
        if client_to_kick:
            ip = self.clients[client_to_kick]['ip']
            nick = self.clients[client_to_kick].get('nick', ip)
            client_to_kick.send(f":server KICK {nick} :{reason}\r\n".encode())
            client_to_kick.send(f"ERROR :You have been kicked from the server: {reason}\r\n".encode())
            self.remove_client(client_to_kick, nick, ip)
            self.log(f"ADMIN: Kicked {ip} - {reason}", show=False)
            print(f"{Colors.GREEN}Kicked {ip}{Colors.RESET}")
        else:
            print(f"{Colors.RED}User not found: {identifier}{Colors.RESET}")

    def admin_ban(self, identifier):
        if identifier in self.nicknames:
            client = self.nicknames[identifier]
            ip = self.clients[client]['ip']
            self.banned_ips.add(ip)
            client.send(f"ERROR :Your IP has been banned from the server\r\n".encode())
            self.remove_client(client, identifier, ip)
            self.log(f"ADMIN: Banned {identifier} ({ip})", show=False)
            print(f"{Colors.GREEN}Banned {identifier} ({ip}){Colors.RESET}")
            return
            
        client_to_ban = None
        for client, info in self.clients.items():
            if info['ip'] == identifier:
                client_to_ban = client
                break
        
        if client_to_ban:
            ip = identifier
            self.banned_ips.add(ip)
            nick = self.clients[client_to_ban].get('nick', ip)
            client_to_ban.send(f"ERROR :Your IP has been banned from the server\r\n".encode())
            self.remove_client(client_to_ban, nick, ip)
            self.log(f"ADMIN: Banned {ip}", show=False)
            print(f"{Colors.GREEN}Banned {ip}{Colors.RESET}")
        else:
            self.banned_ips.add(identifier)
            self.log(f"ADMIN: Banned IP: {identifier}", show=False)
            print(f"{Colors.GREEN}Banned IP: {identifier}{Colors.RESET}")

    def admin_unban(self, ip):
        if ip in self.banned_ips:
            self.banned_ips.remove(ip)
            self.log(f"ADMIN: Unbanned {ip}", show=False)
            print(f"{Colors.GREEN}Unbanned {ip}{Colors.RESET}")
        else:
            print(f"{Colors.RED}IP not banned: {ip}{Colors.RESET}")

    def admin_list_channels(self):
        if not self.channels:
            print(f"{Colors.YELLOW}No channels exist{Colors.RESET}")
            return
            
        print(f"{Colors.BLUE}Channels:{Colors.RESET}")
        for name, channel in self.channels.items():
            members = len(channel.members)
            created = channel.created.strftime("%Y-%m-%d %H:%M")
            print(f"  {Colors.CYAN}{name}{Colors.RESET} - Members: {Colors.GREEN}{members}{Colors.RESET}, Created: {Colors.GRAY}{created}{Colors.RESET}")

    def admin_add_channel(self, channel):
        if not channel.startswith('#'):
            channel = '#' + channel
            
        if channel in self.channels:
            print(f"{Colors.YELLOW}Channel already exists{Colors.RESET}")
            return
            
        self.channels[channel] = Channel(channel)
        self.log(f"ADMIN: Created channel {channel}", show=False)
        print(f"{Colors.GREEN}Created channel {channel}{Colors.RESET}")

    def admin_remove_channel(self, channel):
        if not channel.startswith('#'):
            channel = '#' + channel
            
        if channel in self.channels:
            if self.channels[channel].members:
                print(f"{Colors.RED}Channel has active members{Colors.RESET}")
            else:
                del self.channels[channel]
                self.log(f"ADMIN: Removed channel {channel}", show=False)
                print(f"{Colors.GREEN}Removed channel {channel}{Colors.RESET}")
        else:
            print(f"{Colors.RED}Channel not found{Colors.RESET}")

    def admin_message(self, target, message):
        if target.startswith('#'):
            if target in self.channels:
                for client in self.channels[target].members:
                    client.send(f":server PRIVMSG {target} :[ADMIN] {message}\r\n".encode())
                print(f"{Colors.GREEN}Sent to {target}{Colors.RESET}")
            else:
                print(f"{Colors.RED}Channel not found{Colors.RESET}")
        else:
            if target in self.nicknames:
                self.nicknames[target].send(f":server PRIVMSG {target} :[ADMIN] {message}\r\n".encode())
                print(f"{Colors.GREEN}Sent to {target}{Colors.RESET}")
            else:
                print(f"{Colors.RED}User not found{Colors.RESET}")

    def admin_broadcast(self, message):
        for client in self.clients.keys():
            try:
                client.send(f":server NOTICE * :[BROADCAST] {message}\r\n".encode())
            except:
                pass
        print(f"{Colors.GREEN}Broadcast sent{Colors.RESET}")

    def stop(self):
        self.running = False
        for client, info in self.clients.items():
            try:
                client.send(":server NOTICE * :Server is shutting down\r\n".encode())
                client.close()
            except:
                pass
        
        self.server.close()
        self.log("Server stopped", show=False)
        print(f"{Colors.RED}Server stopped{Colors.RESET}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="IRC Server with SSL/TLS support")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=6667, help="Port to listen on")
    parser.add_argument("--ssl-cert", help="Path to SSL certificate (cert.pem)")
    parser.add_argument("--ssl-key", help="Path to SSL private key (key.pem)")
    args = parser.parse_args()

    server = IRCServer(host=args.host, port=args.port, ssl_cert=args.ssl_cert, ssl_key=args.ssl_key)
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()
        print(f"\n{Colors.RED}Server stopped{Colors.RESET}")