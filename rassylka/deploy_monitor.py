"""Deploy updated monitor_engine.py + main.js to VPS and trigger test run."""
import paramiko

VPS_IP = "155.212.223.142"
VPS_USER = "root"
VPS_PASS = "zF%&SZUqSm1k"
REMOTE_APP = "/opt/bidroute"
SERVICE = "bidroute"

def run_cmd(ssh, cmd, desc=""):
    if desc:
        print(f"[{desc}]")
    print(f"  $ {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    if out:
        print(f"  {out}")
    if err:
        print(f"  stderr: {err}")
    return out

def deploy():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    print(f"Connecting to {VPS_IP}...")
    ssh.connect(VPS_IP, username=VPS_USER, password=VPS_PASS,
                timeout=30, banner_timeout=60)
    print("Connected!\n")
    
    sftp = ssh.open_sftp()
    
    uploads = [
        ("backend/services/monitor_engine.py", f"{REMOTE_APP}/backend/services/monitor_engine.py"),
        ("frontend/assets/main.js", f"{REMOTE_APP}/frontend/assets/main.js"),
        (".env", f"{REMOTE_APP}/.env"),
    ]
    
    for local, remote in uploads:
        print(f"  Upload: {local} -> {remote}")
        sftp.put(local, remote)
    
    sftp.close()
    print("Files uploaded!\n")
    
    # Restart
    run_cmd(ssh, f"systemctl restart {SERVICE}", "Restarting bidroute")
    run_cmd(ssh, f"systemctl is-active {SERVICE}", "Checking status")
    
    ssh.close()
    print("\nDeploy complete!")

if __name__ == "__main__":
    deploy()
