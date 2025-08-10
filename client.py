import socket
import threading
import time
import sys
import readline
import select
import ssl  # SSL ADDITION
import argparse

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

class IRCClient:
    def __init__(self):
        self.sock = None
        self.nick = f"guest{int(time.time() % 1000)}"
        self.active_channel = None
        self.running = False
        self.input_prompt = "> "
        self.commands = {
            'join': "Join a channel: /join #channel",
            'nick': "Change nickname: /nick newname",
            'msg': "Send message: /msg target message",
            'mode': "Set channel mode: /mode #channel [+/-mode] [args]",
            'whois': "Get user info: /whois nickname",
            'me': "Send action: /me action",
            'list': "List channels: /list",
            'part': "Leave channel: /part [#channel]",
            'quit': "Disconnect: /quit",
            'help': "Show this help: /help"
        }

    def show_welcome(self):
        print("="*50)
        print(f"{Colors.BLUE} Welcome to py-IRC {Colors.RESET}".center(60, '#'))
        print("="*50)
        print(f"{Colors.GREEN}●{Colors.RESET} Connected to server")
        print(f"{Colors.GREEN}●{Colors.RESET} Your nickname: {Colors.YELLOW}{self.nick}{Colors.RESET}")
        print(f"{Colors.GREEN}●{Colors.RESET} Type {Colors.CYAN}/help{Colors.RESET} to see available commands")
        print("="*50)

    def show_help(self):
        print("="*50)
        print(f"{Colors.BLUE} Available Commands {Colors.RESET}".center(50))
        print("="*50)
        for cmd, desc in self.commands.items():
            print(f"{Colors.CYAN}{desc}{Colors.RESET}")
        print("="*50)

    def parse_message(self, raw):
        if not raw:
            return None
        
        if raw.startswith('PING'):
            self.send_command(f"PONG {raw[5:]}")
            return None
        
        timestamp = f"{Colors.GRAY}[{time.strftime('%H:%M:%S')}]{Colors.RESET}"
        
        if raw.startswith('ERROR'):
            try:
                reason = raw.split(':', 1)[1].strip()
                return f"{timestamp} {Colors.RED}*** ERROR: {reason}{Colors.RESET}"
            except:
                return f"{timestamp} {Colors.RED}{raw}{Colors.RESET}"
        
        if 'KICK' in raw:
            try:
                parts = raw.split()
                nick = parts[3]
                channel = parts[2]
                reason = raw.split(':', 1)[1] if ':' in raw else "No reason given"
                return f"{timestamp} {Colors.RED}*** You have been kicked from {channel}: {reason}{Colors.RESET}"
            except:
                return f"{timestamp} {Colors.RED}{raw}{Colors.RESET}"
        
        if raw.split()[0].isdigit():
            parts = raw.split()
            code = parts[0]
            message = raw[raw.find(':', 1)+1:] if ':' in raw else ' '.join(parts[3:])
            if code in ('001', '002', '003', '004', '005'):
                return f"{timestamp} {Colors.GREEN}●{Colors.RESET} {message}"
            elif code in ('372', '375', '376'):
                return f"{timestamp} {Colors.BLUE}●{Colors.RESET} {message}"
            elif code == '353':
                channel = parts[4]
                names = message
                return f"{timestamp} {Colors.CYAN}Users in {channel}:{Colors.RESET} {names}"
            elif code == '366':
                return None
            else:
                return f"{timestamp} {Colors.YELLOW}●{Colors.RESET} {message}"
        
        if 'NOTICE' in raw:
            try:
                if ':' in raw:
                    message = raw.split(':', 1)[1].strip()
                else:
                    message = raw
                return f"{timestamp} {Colors.GRAY}-NOTICE- {message}{Colors.RESET}"
            except:
                return f"{timestamp} {Colors.RED}{raw}{Colors.RESET}"
        
        if 'PRIVMSG' in raw:
            try:
                sender_start = raw.find(':') + 1
                prefix_end = raw.find(' ', sender_start)
                if prefix_end == -1:
                    prefix_end = len(raw)
                prefix = raw[sender_start:prefix_end]
                nick_end = prefix.find('!')
                if nick_end == -1:
                    sender = prefix
                else:
                    sender = prefix[:nick_end]
                
                msg_start = raw.find('PRIVMSG ') + 8
                target_end = raw.find(' ', msg_start)
                if target_end == -1:
                    target_end = raw.find(':', msg_start)
                target = raw[msg_start:target_end].strip()
                
                content_start = raw.find(':', target_end) + 1
                message = raw[content_start:]
                
                if message.startswith('\x01ACTION') and message.endswith('\x01'):
                    action = message[7:-1]
                    return f"{timestamp} {Colors.MAGENTA}*{Colors.RESET} {Colors.YELLOW}{sender}{Colors.RESET} {action}"
                
                if target.startswith('#'):
                    return f"{timestamp} {Colors.BLUE}<{target}>{Colors.RESET} {Colors.YELLOW}<{sender}>{Colors.RESET}: {message}"
                else:
                    return f"{timestamp} {Colors.MAGENTA}*{sender}*{Colors.RESET} {message}"
            except Exception:
                return f"{timestamp} {Colors.RED}{raw}{Colors.RESET}"
        
        elif 'JOIN' in raw:
            try:
                sender_start = raw.find(':') + 1
                sender_end = raw.find('!', sender_start)
                if sender_end == -1:
                    sender_end = raw.find(' ', sender_start)
                sender = raw[sender_start:sender_end]
                
                channel_start = raw.find('JOIN') + 5
                channel = raw[channel_start:].strip()
                if channel.startswith(':'):
                    channel = channel[1:]
                return f"{timestamp} {Colors.GREEN}-->{Colors.RESET} {Colors.YELLOW}{sender}{Colors.RESET} joined {Colors.BLUE}{channel}{Colors.RESET}"
            except:
                return f"{timestamp} {Colors.RED}{raw}{Colors.RESET}"
        
        elif 'PART' in raw:
            try:
                sender_start = raw.find(':') + 1
                sender_end = raw.find('!', sender_start)
                if sender_end == -1:
                    sender_end = raw.find(' ', sender_start)
                sender = raw[sender_start:sender_end]
                
                channel_start = raw.find('PART') + 5
                channel = raw[channel_start:].strip()
                if channel.startswith(':'):
                    channel = channel[1:]
                return f"{timestamp} {Colors.RED}<--{Colors.RESET} {Colors.YELLOW}{sender}{Colors.RESET} left {Colors.BLUE}{channel}{Colors.RESET}"
            except:
                return f"{timestamp} {Colors.RED}{raw}{Colors.RESET}"
        
        elif 'QUIT' in raw:
            try:
                sender_start = raw.find(':') + 1
                sender_end = raw.find('!', sender_start)
                if sender_end == -1:
                    sender_end = raw.find(' ', sender_start)
                sender = raw[sender_start:sender_end]
                return f"{timestamp} {Colors.RED}<--{Colors.RESET} {Colors.YELLOW}{sender}{Colors.RESET} disconnected"
            except:
                return f"{timestamp} {Colors.RED}{raw}{Colors.RESET}"
        
        elif 'NICK' in raw:
            try:
                sender_start = raw.find(':') + 1
                sender_end = raw.find('!', sender_start)
                if sender_end == -1:
                    sender_end = raw.find(' ', sender_start)
                old_nick = raw[sender_start:sender_end]
                
                new_nick = raw.split(':')[-1]
                return f"{timestamp} {Colors.YELLOW}{old_nick}{Colors.RESET} is now known as {Colors.YELLOW}{new_nick}{Colors.RESET}"
            except:
                return f"{timestamp} {Colors.RED}{raw}{Colors.RESET}"
        
        if raw.strip().startswith(':') and len(raw.strip().split()) == 1:
            return None
        return f"{timestamp} {raw}"

    def handle_server_message(self, message):
        formatted = self.parse_message(message)
        if not formatted:
            return
    
        try:
            current_buf = readline.get_line_buffer()
        except Exception:
            current_buf = ''
    
        sys.stdout.write('\r')
        sys.stdout.write(' ' * (len(self.input_prompt) + len(current_buf)))
        sys.stdout.write('\r')
    
        print(formatted)
    
        if formatted and any(x in formatted for x in [Colors.RED + "*** ERROR", Colors.RED + "*** You have been kicked"]):
            print(f"{Colors.RED}Disconnecting from server...{Colors.RESET}")
            self.running = False
            return
    
        sys.stdout.write(self.input_prompt + current_buf)
        sys.stdout.flush()

    def send_command(self, command):
        try:
            if not command.endswith('\r\n'):
                command += '\r\n'
            self.sock.send(command.encode('utf-8'))
        except Exception as e:
            print(f"{Colors.RED}[ERROR] Send error: {e}{Colors.RESET}")
            self.running = False

    def receive_loop(self):
        buffer = ""
        while self.running:
            try:
                data = self.sock.recv(4096).decode('utf-8')
                if not data:
                    self.running = False
                    print(f"{Colors.RED}Connection closed by server{Colors.RESET}")
                    break
                    
                buffer += data
                while '\r\n' in buffer:
                    line, buffer = buffer.split('\r\n', 1)
                    self.handle_server_message(line)
            except Exception as e:
                if self.running:
                    print(f"{Colors.RED}[ERROR] Receive error: {e}{Colors.RESET}")
                self.running = False
                break

    def handle_command(self, command):
        parts = command.split()
        if not parts:
            return
            
        cmd = parts[0].lower()
        
        if cmd == 'help':
            self.show_help()
        elif cmd == 'join':
            if len(parts) > 1:
                channel = parts[1]
                if not channel.startswith('#'):
                    channel = '#' + channel
                self.send_command(f"JOIN {channel}")
                self.active_channel = channel
                self.input_prompt = f"{Colors.BLUE}[{channel}]{Colors.RESET}> "
                print(f"{Colors.GREEN}Joined {channel}{Colors.RESET}")
            else:
                print(f"{Colors.RED}Usage: /join #channel{Colors.RESET}")
        elif cmd == 'nick':
            if len(parts) > 1:
                new_nick = parts[1]
                self.send_command(f"NICK {new_nick}")
                self.nick = new_nick
                print(f"{Colors.GREEN}Nickname changed to {new_nick}{Colors.RESET}")
            else:
                print(f"{Colors.RED}Usage: /nick newname{Colors.RESET}")
        elif cmd == 'mode':
            if len(parts) > 2:
                self.send_command(f"MODE {' '.join(parts[1:])}")
            else:
                print(f"{Colors.RED}Usage: /mode #channel [+/-mode] [args]{Colors.RESET}")
        elif cmd == 'whois':
            if len(parts) > 1:
                self.send_command(f"WHOIS {parts[1]}")
            else:
                print(f"{Colors.RED}Usage: /whois nickname{Colors.RESET}")
        elif cmd == 'me':
            if len(parts) > 1 and self.active_channel:
                action = ' '.join(parts[1:])
                self.send_command(f"PRIVMSG {self.active_channel} :\x01ACTION {action}\x01")
            else:
                print(f"{Colors.RED}Usage: /me action{Colors.RESET}")
        elif cmd == 'list':
            self.send_command("LIST")
            print(f"{Colors.GREEN}Requested channel list{Colors.RESET}")
        elif cmd == 'part':
            channel = parts[1] if len(parts) > 1 else self.active_channel
            if channel:
                self.send_command(f"PART {channel}")
                if channel == self.active_channel:
                    self.active_channel = None
                    self.input_prompt = "> "
                print(f"{Colors.GREEN}Left {channel}{Colors.RESET}")
            else:
                print(f"{Colors.RED}Not in any channel to part{Colors.RESET}")
        elif cmd == 'quit':
            self.send_command("QUIT")
            self.running = False
            print(f"{Colors.GREEN}Disconnecting...{Colors.RESET}")
        else:
            print(f"{Colors.RED}Unknown command: /{cmd}{Colors.RESET}")

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
                        print(f"{Colors.RED}Not in any channel. Use /join #channel{Colors.RESET}")
            except KeyboardInterrupt:
                self.send_command("QUIT")
                print(f"\n{Colors.GREEN}Disconnecting...{Colors.RESET}")
                self.running = False
                break
            except Exception as e:
                print(f"{Colors.RED}Input error: {e}{Colors.RESET}")

    def connect(self, host, port, use_ssl=False, ssl_verify=False, ssl_cert=None):  # SSL PARAMS ADDED
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            if use_ssl:
                context = ssl.create_default_context()
                if not ssl_verify:  # Skip verification for self-signed certs
                    context.check_hostname = False
                    context.verify_mode = ssl.CERT_NONE
                elif ssl_cert:  # Use custom CA cert
                    context.load_verify_locations(cafile=ssl_cert)
                self.sock = context.wrap_socket(self.sock, server_hostname=host)
            
            nickname = input(f"Nickname [{self.nick}]: ") or self.nick
            self.nick = nickname
            self.sock.connect((host, port))
            self.running = True
            self.show_welcome()
            self.send_command(f"NICK {self.nick}")
            self.send_command(f"USER {self.nick} 0 * :{self.nick}")
            
            receive_thread = threading.Thread(target=self.receive_loop)
            receive_thread.daemon = True
            receive_thread.start()
            
            self.input_loop()
        except Exception as e:
            print(f"{Colors.RED}Connection error: {e}{Colors.RESET}")
        finally:
            self.disconnect()

    def disconnect(self):
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
        print(f"{Colors.GREEN}Disconnected from server{Colors.RESET}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ssl", action="store_true", help="Enable SSL/TLS")
    parser.add_argument("--no-ssl-verify", action="store_true", help="Disable SSL certificate verification (for testing)")
    parser.add_argument("--ssl-cert", help="Path to custom CA cert (e.g., self-signed cert.pem)")
    args = parser.parse_args()

    client = IRCClient()
    host = input("Server address [127.0.0.1]: ") or "127.0.0.1"
    port = int(input("Server port [6667]: ") or 6667)
    client.connect(
        host=host,
        port=port,
        use_ssl=args.ssl,
        ssl_verify=not args.no_ssl_verify,
        ssl_cert=args.ssl_cert
    )