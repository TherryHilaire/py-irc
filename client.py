import socket
import threading
import time
import select
import sys
import readline

class IRCClient:
    def __init__(self):
        self.sock = None
        self.nick = "guest" + str(int(time.time()) % 1000)
        self.active_channel = None
        self.running = True
        self.input_prompt = "> "
        self.message_history = []
        self.server_host = None
        self.server_port = None

    def connect(self, host, port):
        self.server_host = host
        self.server_port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        try:
            self.sock.connect((host, port))
            print(f"🔌 Connected to {host}:{port}")
            self.send_command(f"NICK {self.nick}")
            self.send_command(f"USER {self.nick} 0 * :{self.nick}")
            
            # Start receive thread
            threading.Thread(target=self.receive_messages, daemon=True).start()
            
            # Start input loop
            self.input_loop()
            
        except ConnectionRefusedError:
            print(f"❌ Connection refused by {host}:{port}")
        except Exception as e:
            print(f"⚠️ Connection error: {e}")
        finally:
            self.disconnect()

    def send_command(self, command):
        try:
            if not command.endswith('\r\n'):
                command += '\r\n'
            self.sock.send(command.encode('utf-8'))
            self.log_message("OUT", command.strip())
        except Exception as e:
            print(f"⚠️ Failed to send command: {e}")
            self.running = False

    def receive_messages(self):
        buffer = ""
        while self.running:
            try:
                ready, _, _ = select.select([self.sock], [], [], 1)
                if not ready:
                    continue
                    
                data = self.sock.recv(4096).decode('utf-8')
                if not data:
                    raise ConnectionError("Server disconnected")
                
                buffer += data
                while '\r\n' in buffer:
                    line, buffer = buffer.split('\r\n', 1)
                    self.handle_message(line.strip())
                    
            except ConnectionError as e:
                print(f"\n⚠️ Connection lost: {e}")
                self.running = False
                break
            except Exception as e:
                print(f"\n⚠️ Receive error: {e}")
                continue

    def handle_message(self, message):
        self.message_history.append(message)
        self.log_message("IN", message)
        
        try:
            if message.startswith(":"):
                # Server message with prefix
                prefix, _, trailing = message[1:].partition(' ')
                command, _, params = trailing.partition(' ')
                
                if command == "PRIVMSG":
                    target, _, content = params.partition(' :')
                    sender = prefix.split('!')[0]
                    
                    if target.startswith('#'):
                        print(f"\n[#{target}] <{sender}> {content}")
                    else:
                        print(f"\n[PM from {sender}] {content}")
                        
                elif command == "JOIN":
                    channel = params.lstrip(':')
                    sender = prefix.split('!')[0]
                    print(f"\n[+] {sender} joined {channel}")
                    
                elif command == "PART":
                    channel = params.lstrip(':')
                    sender = prefix.split('!')[0]
                    print(f"\n[-] {sender} left {channel}")
                    
                elif command == "NOTICE":
                    target, _, content = params.partition(' :')
                    print(f"\n[NOTICE] {content}")
                    
                elif command == "TOPIC":
                    channel, _, topic = params.partition(' :')
                    print(f"\n[TOPIC] {channel}: {topic}")
                    
                else:
                    print(f"\n[SERVER] {message}")
            else:
                # Server message without prefix
                if message.startswith("PING"):
                    self.send_command(f"PONG {message[5:]}")
                else:
                    print(f"\n[SERVER] {message}")
                    
        except Exception as e:
            print(f"\n⚠️ Error parsing message: {e}\nRaw: {message}")
            
        sys.stdout.write(self.input_prompt)
        sys.stdout.flush()

    def log_message(self, direction, message):
        with open('irc_client.log', 'a') as f:
            f.write(f"[{time.ctime()}] {direction}: {message}\n")

    def input_loop(self):
        while self.running:
            try:
                command = input(self.input_prompt).strip()
                if not command:
                    continue
                    
                if command.startswith('/'):
                    self.handle_command(command[1:])
                else:
                    if self.active_channel:
                        self.send_command(f"PRIVMSG {self.active_channel} :{command}")
                    else:
                        print("❌ Not in any channel. Join one first with /join")
            except KeyboardInterrupt:
                print("\n🛑 Disconnecting...")
                self.send_command("QUIT")
                self.running = False
                break
            except Exception as e:
                print(f"⚠️ Input error: {e}")

    def handle_command(self, command):
        cmd, *args = command.split(' ', 1)
        cmd = cmd.lower()
        
        try:
            if cmd == 'join':
                channel = args[0] if args else '#general'
                if not channel.startswith('#'):
                    channel = '#' + channel
                self.send_command(f"JOIN {channel}")
                self.active_channel = channel
                self.input_prompt = f"[{channel}]> "
                
            elif cmd == 'nick':
                new_nick = args[0] if args else "guest" + str(int(time.time()) % 1000)
                self.send_command(f"NICK {new_nick}")
                self.nick = new_nick
                print(f"Nickname changed to {new_nick}")
                
            elif cmd == 'msg' and args:
                target, *msg = args[0].split(' ', 1)
                if msg:
                    self.send_command(f"PRIVMSG {target} :{msg[0]}")
                
            elif cmd == 'list':
                self.send_command("LIST")
                
            elif cmd == 'part':
                channel = args[0] if args else self.active_channel
                if channel:
                    self.send_command(f"PART {channel}")
                    if channel == self.active_channel:
                        self.active_channel = None
                        self.input_prompt = "> "
                        
            elif cmd == 'quit':
                self.send_command("QUIT")
                self.running = False
                
            elif cmd == 'help':
                print("\nIRC Client Commands:")
                print("/join <channel> - Join a channel")
                print("/nick <nickname> - Change nickname")
                print("/msg <#channel|nick> <message> - Send message")
                print("/list - List channels")
                print("/part [channel] - Leave channel")
                print("/quit - Disconnect")
                print("/help - Show this help")
                
            elif cmd == 'time':
                self.send_command("TIME")
                
            elif cmd == 'stats':
                self.send_command("STATS")
                
            else:
                print(f"❌ Unknown command: /{cmd}")
        except Exception as e:
            print(f"⚠️ Command error: {e}")

    def disconnect(self):
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
        print("🔌 Disconnected from server")

if __name__ == "__main__":
    print("""
       _____ _____   _____
      |_   _|  __ \ / ____|
        | | | |__) | |
        | | |  _  /| |
       _| |_| | \ \| |____
      |_____|_|  \_\\_____|
    """)
    
    client = IRCClient()
    
    try:
        host = input("Server address [127.0.0.1]: ") or "127.0.0.1"
        port = int(input("Server port [6667]: ") or 6667)
        nick = input(f"Nickname [{client.nick}]: ") or client.nick
        client.nick = nick
        
        client.connect(host, port)
    except Exception as e:
        print(f"⚠️ Failed to start client: {e}")
