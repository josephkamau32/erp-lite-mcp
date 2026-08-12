import subprocess
import json
import time
import sys

proc = subprocess.Popen(
    ['C:\\Users\\HP\\Documents\\Projects\\erp-lite-mcp\\.venv\\Scripts\\python.exe', '-m', 'src.server'],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=1
)

init_msg = json.dumps({
    "jsonrpc": "2.0", 
    "id": 1, 
    "method": "initialize", 
    "params": {
        "protocolVersion": "2024-11-05", 
        "capabilities": {}, 
        "clientInfo": {"name": "claude-desktop", "version": "1.0"}
    }
})

print("Sending init...")
proc.stdin.write(init_msg + "\n")
proc.stdin.flush()

time.sleep(1)

out = proc.stdout.readline()
print("STDOUT:", out.strip())
err = proc.stderr.read()
print("STDERR:", err)
proc.terminate()
