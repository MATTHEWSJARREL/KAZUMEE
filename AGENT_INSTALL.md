# Kazumee Agent - Installation & Setup

**The easiest way to set up autonomous clip capture for your stream.**

## Download & Install

1. **Download**: [KazumeeAgent.exe](https://github.com/MATTHEWSJARREL/KAZUMEE/releases/latest)
2. **Save** to Desktop or Program Files
3. **Double-click** to run

That's it. No Python install, no terminal, no configuration files needed.

## First Run (Setup)

**First time you run the agent:**

1. **Login popup appears** → Click the link or it opens automatically
2. **Browser opens** to Kazumee login
3. **Log in** with your Kazumee account
4. **Authorize** the agent
5. **Redirect happens** → Token saved automatically
6. **Tray icon turns green** → Ready to go

Done. Agent is now set up permanently.

## How It Works

1. **Agent runs in your system tray** (Windows taskbar lower right)
2. **Green dot** = Connected and ready
3. **Red dot** = Not connected to cloud
4. **Click tray icon** → Quit option

## OBS Setup (One-time)

Before running the agent, enable these in OBS:

### 1. Enable WebSocket Server

- **Tools** → **WebSocket Server Settings**
- Check **"Enable WebSocket server"**
- Note the password (shown on screen)

### 2. Enable Replay Buffer

- **Settings** → **Output**
- Check **"Replay Buffer"** checkbox
- Set duration to **60 seconds** (or your preference)
- Click **OK**

That's it. You only do this once.

## Using the Agent

**While streaming:**

1. Kazumee cloud **detects a hype moment** (high chat activity)
2. Cloud sends command to your agent
3. Agent **automatically saves** the last 60s from OBS
4. Clip **uploads** to Kazumee cloud
5. Cloud **processes** and **exports** to TikTok/YouTube

Everything is automatic. You just stream.

## Troubleshooting

### "Red dot stays red"

**Solution**: Check your internet connection and that OBS is running.

### "Agent won't start"

**Solution**: 
- Make sure OBS is open first
- Check that WebSocket server is enabled (Tools → WebSocket Server Settings)
- Restart OBS
- Try running the agent again

### "Login didn't work"

**Solution**:
- Open the agent again
- It will ask to log in again
- Make sure you have internet connection

### "My token expired"

The agent will ask you to log in again automatically. Just open the app and follow the login flow.

## Advanced

### Manual Token (if needed)

If you want to use the agent from terminal:

```bash
# Option 1: Set environment variable
export STREAMER_TOKEN="your_token_here"
python kazumee-agent.py

# Option 2: Let it prompt for login
python kazumee-agent.py
```

Your token is saved to: `~/.kazumee_agent_token`

### Custom OBS Settings

If OBS is running on a different computer:

```bash
export OBS_HOST="192.168.1.100"
export OBS_PORT="4455"
python kazumee-agent.py
```

## Security

- [SECURE] Token is saved locally in `~/.kazumee_agent_token`
- [PROTECTED] Only accessible from your computer
- [WARNING] Never share your token
- [CAUTION] Only run on trusted computers

## Support

Having issues? Check:

1. **OBS WebSocket enabled** (Tools → WebSocket Server Settings)
2. **OBS Replay Buffer enabled** (Settings → Output)
3. **Internet connection** working
4. **Kazumee agent is green** (not red)

For more help, check the Kazumee dashboard → Monitoring → Errors.

---

**Ready to auto-clip?** Double-click `KazumeeAgent.exe` and get started!
