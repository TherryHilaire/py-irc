import socket
import threading
import time
import readline

class IRCClient:
    COLOR_CODES = {
        'white': '00',
        'black': '01',
        'blue': '02',
        'green': '03',
        'red': '04',
        'brown': '05',
        'purple': '06',
        'orange': '07',
        'yellow': '08',
        'light_green': '09',
        'cyan': '10',
        'light_cyan': '11',
        'light_blue': '12',
        'pink': '13',
        'gray': '14',
        'light_gray': '15',
        'reset': '\x0F'
    }

    def __init__(self):
        self.sock = None
        self.nick = f"guest{time.time() % 1000:.0f}"
        self.active_channel = None
        self.running = False
        self.input_prompt = "> "

    def connect(self, host, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect((host, port))
            self.running = True
            print(f"Connected to {host}:{port}")
            self.send_command(f"NICK {self.nick}")
            self.send_command(f"USER {self.nick} 0 * :{self.nick}")
            
            receive_thread = threading.Thread(target=self.receive_loop)
            receive_thread.daemon = True
            receive_thread.start()
            
            self.input_loop()
        except Exception as e:
            print(f"Connection error: {e}")
        finally:
            self.disconnect()

    def colorize(self, text, color):
        if color in self.COLOR_CODES:
            return f"\x03{self.COLOR_CODES[color]}{text}{self.COLOR_CODES['reset']}"
        return text

    def send_command(self, command):
        try:
            self.sock.send(f"{command}\r\n".encode('utf-8'))
        except Exception as e:
            print(f"Send error: {e}")
            self.running = False

    def receive_loop(self):
        buffer = ""
        while self.running:
            try:
                data = self.sock.recv(4096).decode('utf-8')
                if not data:
                    break
                    
                buffer += data
                while '\r\n' in buffer:
                    line, buffer = buffer.split('\r\n', 1)
                    self.handle_server_message(line.strip())
            except Exception as e:
                print(f"Receive error: {e}")
                break

    def handle_server_message(self, message):
        if message.startswith('PING'):
            self.send_command(f"PONG {message[5:]}")
            return
            
        # Handle NOTICE messages
        if message.startswith('NOTICE'):
            _, content = message.split(':', 1)
            print(f"\n{self.colorize('NOTICE', 'yellow')}: {content.strip()}")
            return
            
        # Handle PRIVMSG formatting
        if 'PRIVMSG' in message:
            try:
                prefix, content = message.split(':', 1)
                nick = prefix.split('!')[0][1:]
                target = prefix.split()[2]
                
                if '\x01ACTION' in content:  # Handle /me actions
                    action = content.replace('\x01ACTION', '').replace('\x01', '')
                    print(f"\n* {nick} {action}")
                elif target.startswith('#'):
                    print(f"\n{self.colorize(nick, 'green')} in {self.colorize(target, 'blue')}: {content}")
                else:
                    print(f"\n{self.colorize('PM from ' + nick, 'red')}: {content}")
                return
            except Exception as e:
                print(f"Error parsing message: {e} - {message}")
                
        # Handle other messages
        print(f"\n{message}")

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
                        print("Not in any channel. Use /join #channel")
            except KeyboardInterrupt:
                self.send_command("QUIT")
                break
            except Exception as e:
                print(f"Input error: {e}")

    def handle_command(self, command):
        parts = command.split()
        if not parts:
            return
            
        cmd = parts[0].lower()
        
        if cmd == 'join':
            if len(parts) > 1:
                channel = parts[1]
                if not channel.startswith('#'):
                    channel = '#' + channel
                self.send_command(f"JOIN {channel}")
                self.active_channel = channel
                self.input_prompt = f"{self.colorize(channel, 'blue')}> "
            else:
                print("Usage: /join #channel")
                
        elif cmd == 'nick':
            if len(parts) > 1:
                self.send_command(f"NICK {parts[1]}")
            else:
                print("Usage: /nick newname")
                
        elif cmd == 'mode':
            if len(parts) > 2:
                self.send_command(f"MODE {' '.join(parts[1:])}")
            else:
                print("Usage: /mode #channel [+/-mode] [args]")
                
        elif cmd == 'whois':
            if len(parts) > 1:
                self.send_command(f"WHOIS {parts[1]}")
            else:
                print("Usage: /whois nickname")
                
        elif cmd == 'me':
            if len(parts) > 1 and self.active_channel:
                action = ' '.join(parts[1:])
                self.send_command(f"PRIVMSG {self.active_channel} :\x01ACTION {action}\x01")
                
        elif cmd == 'list':
            self.send_command("LIST")
            
        elif cmd == 'part':
            channel = parts[1] if len(parts) > 1 else self.active_channel
            if channel:
                self.send_command(f"PART {channel}")
                if channel == self.active_channel:
                    self.active_channel = None
                    self.input_prompt = "> "
                    
        elif cmd == 'quit':
            self.send_command("QUIT")
            self.running = False
            
        else:
            print(f"Unknown command: /{cmd}")

    def disconnect(self):
        self.running = False
        if self.sock:
            self.sock.close()
        print("Disconnected")

if __name__ == "__main__":
    print("""
       _____ _____   _____
      |_   _|  __ \ / ____|
        | | | |__) | |
        | | |  _  /| |
       _| |_| | \ \| |____
      |_____|_|  \_\\_____|
    """)
    
    host = input("Server address [127.0.0.1]: ") or "127.0.0.1"
    port = int(input("Server port [6667]: ") or 6667)
    
    client = IRCClient()
    client.connect(host, port)

