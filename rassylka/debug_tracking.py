"""Manually push campaigns.py and campaign_sender.py to VPS."""
import paramiko
import os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('155.212.223.142', username='root', password='zF%&SZUqSm1k', timeout=30)

sftp = ssh.open_sftp()

local_dir = r'c:\Users\user\Downloads\rassylka\rassylka'

# Push campaigns.py
local_file = os.path.join(local_dir, 'backend', 'routers', 'campaigns.py')
remote_file = '/opt/bidroute/backend/routers/campaigns.py'
sftp.put(local_file, remote_file)
print(f"Uploaded {local_file} -> {remote_file}")

# Push campaign_sender.py
local_file = os.path.join(local_dir, 'backend', 'services', 'campaign_sender.py')
remote_file = '/opt/bidroute/backend/services/campaign_sender.py'
sftp.put(local_file, remote_file)
print(f"Uploaded {local_file} -> {remote_file}")

# Push main.js
local_file = os.path.join(local_dir, 'frontend', 'assets', 'main.js')
remote_file = '/opt/bidroute/frontend/assets/main.js'
sftp.put(local_file, remote_file)
print(f"Uploaded {local_file} -> {remote_file}")

sftp.close()

# Restart service
stdin, stdout, stderr = ssh.exec_command('systemctl restart bidroute && systemctl is-active bidroute', timeout=15)
print("Service status:", stdout.read().decode('utf-8', errors='replace').strip())

# Verify preview route is now registered
import time
time.sleep(2)
stdin, stdout, stderr = ssh.exec_command(
    'grep -n "preview" /opt/bidroute/backend/routers/campaigns.py',
    timeout=10
)
print("Preview in campaigns.py:", stdout.read().decode('utf-8', errors='replace'))

stdin, stdout, stderr = ssh.exec_command(
    'curl -s -X POST http://127.0.0.1:8000/api/campaigns/4/preview | head -3',
    timeout=10
)
print("Preview response:", stdout.read().decode('utf-8', errors='replace'))

ssh.close()
print("Done!")
