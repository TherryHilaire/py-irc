# py-IRC - Python IRC Client and Server

py-IRC is an IRC (Internet Relay Chat) solution implemented in Python, featuring both a client and server with modern. This project brings the classic chat experience to life with an okay interface, basic administration tools, and comprehensive logging. It's mostly vibecoded so it there are any issues or security concerns feel free to open a pull request.

## Key Features

### Client Features
- 🎨 **Colorful Interface**: ANSI color-coded messages for better readability
- 💬 **Full IRC Command Support**: 
  - `/join`, `/part`, `/nick`, `/msg`, `/me`, `/list`, `/quit`, `/help`
- ⏱️ **Timestamps**: All messages include timestamps
- 🔄 **Real-time Updates**: Join/part notifications, nick changes, and more
- 📝 **Input Preservation**: Messages don't interrupt your typing
- 🛠️ **Error Handling**: Clear error messages with color coding
- 🌐 **Cross-platform**: Works on Windows, macOS, and Linux

### Server Features
- 👑 **Admin Console**: Powerful server management interface
- 📊 **Comprehensive Logging**: All server activity logged to file
- ⚔️ **User Management**: 
  - Kick users with custom messages
  - Ban/unban users by nickname
- 🧩 **Channel Management**:
  - Create new channels
  - Remove empty channels
  - List all active channels with member counts
- 📢 **Messaging Tools**:
  - Send messages as server to channels/users
  - Broadcast messages to all connected users
- 🛡️ **Ban System**: Prevents banned users from connecting
- ⏱️ **Channel Tracking**: Records channel creation time
- **SSL/TLS support**: More or so secure chat using SSL.

### Prerequisites
- Python 3.6 or higher

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/TherryHilaire/py-irc.git
   cd py-irc
   ```

## Quick Start

### 1. Generate SSL Certificates (for testing)
```bash
mkdir -p certs
openssl req -x509 -newkey rsa:4096 -keyout certs/key.pem -out certs/cert.pem -days 365 -nodes -subj "/CN=localhost"
```

### 2. Run the Server
```bash
python server.py --host 0.0.0.0 --port 6667 --ssl-cert certs/cert.pem --ssl-key certs/key.pem
```

### 3. Run the Client
```bash
python client.py --ssl --no-ssl-verify
```

## Production Setup
For production, replace the self-signed certificates with ones from Let's Encrypt:
```bash
certbot certonly --standalone -d yourdomain.com
```

You'll be prompted to enter:
- Server address (default: 127.0.0.1)
- Server port (default: 6667)
- Nickname (default randomly generated)

## Client Commands
| Command         | Description                          | Example                     |
|-----------------|--------------------------------------|-----------------------------|
| `/join #channel`| Join a channel                       | `/join #python`             |
| `/nick name`    | Change your nickname                 | `/nick alice`               |
| `/msg target m` | Send message to user/channel         | `/msg bob Hello!`           |
| `/me action`    | Send action message                  | `/me dances`                |
| `/list`         | List available channels              | `/list`                     |
| `/part [#chan]` | Leave current or specified channel   | `/part #python`             |
| `/quit`         | Disconnect from server               | `/quit`                     |
| `/help`         | Show available commands              | `/help`                     |

## Server Admin Commands
| Command                  | Description                          | Example                         |
|--------------------------|--------------------------------------|---------------------------------|
| `/kick nick [reason]`    | Kick a user                          | `/kick bob Being rude`          |
| `/ban nick`              | Ban a user                           | `/ban spammer123`               |
| `/unban nick`            | Unban a user                         | `/unban reformed_user`          |
| `/channels`              | List all channels                    | `/channels`                     |
| `/addchannel #channel`   | Create a new channel                 | `/addchannel #new_chat`         |
| `/removechannel #channel`| Remove an empty channel              | `/removechannel #old_chat`      |
| `/msg target message`    | Send message as server               | `/msg #announcements Important!`|
| `/broadcast message`     | Broadcast to all users               | `/broadcast Server restart!`    |
| `/shutdown`              | Shut down the server                 | `/shutdown`                     |

## Logging
The server logs all activity to `server.log` with timestamps, including:
- New connections and disconnections
- Channel joins and parts
- Private messages
- Admin actions
- Server events

## Technical Details
- **Client-Server Protocol**: Custom IRC-like protocol
- **Concurrency**: Multi-threaded architecture
- **Data Encoding**: UTF-8
- **Color System**: ANSI escape sequences
- **Input Handling**: Readline library for advanced input

## Contributing
Contributions are welcome! Please open an issue or pull request for:
- Bug reports
- Feature requests
- Code improvements

## License
This project is licensed under the GNU GPL License - see the [LICENSE](LICENSE) file for details.