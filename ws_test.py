import websocket
import ssl

TOKEN = "XsF1VxOzaGvt2MB6felCoA4I7kt-WflDsoZxxnCYsWE"   # v@gmail.com agent token
URL   = "wss://kazumee-production.up.railway.app/ws/agent"

# Skip SSL cert verification (Railway cert expired; test-only workaround)
ssl_opts = {"cert_reqs": ssl.CERT_NONE, "check_hostname": False}

ws = websocket.create_connection(URL, header=[f"Authorization: Bearer {TOKEN}"], sslopt=ssl_opts)
ws.send('{"type":"agent_online"}')
print("CONNECTED — waiting for clip commands... (leave this running)")
while True:
    print("<<<", ws.recv())
