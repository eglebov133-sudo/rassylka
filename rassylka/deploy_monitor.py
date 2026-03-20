"""Deploy all updated files to VPS and restart service."""
import paramiko
import os

VPS_IP = "87.236.22.182"
VPS_USER = "root"
VPS_PASS = "eivnkt5S!kjT"
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
    
    # Ensure remote directories exist
    dirs_to_create = [
        f"{REMOTE_APP}/backend/services/browser_tests",
    ]
    for d in dirs_to_create:
        run_cmd(ssh, f"mkdir -p {d}", f"Ensure dir: {d}")
    
    uploads = [
        # Backend core
        ("backend/models.py", f"{REMOTE_APP}/backend/models.py"),
        ("backend/schemas.py", f"{REMOTE_APP}/backend/schemas.py"),
        ("backend/main.py", f"{REMOTE_APP}/backend/main.py"),
        # Routers
        ("backend/routers/monitor.py", f"{REMOTE_APP}/backend/routers/monitor.py"),
        ("backend/routers/dashboard.py", f"{REMOTE_APP}/backend/routers/dashboard.py"),
        ("backend/routers/bids.py", f"{REMOTE_APP}/backend/routers/bids.py"),
        ("backend/routers/logs.py", f"{REMOTE_APP}/backend/routers/logs.py"),
        # Services
        ("backend/services/mail_engine.py", f"{REMOTE_APP}/backend/services/mail_engine.py"),
        ("backend/services/matching.py", f"{REMOTE_APP}/backend/services/matching.py"),
        ("backend/services/auto_supplier_search.py", f"{REMOTE_APP}/backend/services/auto_supplier_search.py"),
        ("backend/services/monitor_engine.py", f"{REMOTE_APP}/backend/services/monitor_engine.py"),
        # Browser test engine + all test modules
        ("backend/services/browser_test_engine.py", f"{REMOTE_APP}/backend/services/browser_test_engine.py"),
        ("backend/services/browser_tests/__init__.py", f"{REMOTE_APP}/backend/services/browser_tests/__init__.py"),
        ("backend/services/browser_tests/public_tests.py", f"{REMOTE_APP}/backend/services/browser_tests/public_tests.py"),
        ("backend/services/browser_tests/auth_tests.py", f"{REMOTE_APP}/backend/services/browser_tests/auth_tests.py"),
        ("backend/services/browser_tests/buyer_bids_tests.py", f"{REMOTE_APP}/backend/services/browser_tests/buyer_bids_tests.py"),
        ("backend/services/browser_tests/buyer_stock_tests.py", f"{REMOTE_APP}/backend/services/browser_tests/buyer_stock_tests.py"),
        ("backend/services/browser_tests/seller_tests.py", f"{REMOTE_APP}/backend/services/browser_tests/seller_tests.py"),
        ("backend/services/browser_tests/messaging_tests.py", f"{REMOTE_APP}/backend/services/browser_tests/messaging_tests.py"),
        # Frontend
        ("frontend/index.html", f"{REMOTE_APP}/frontend/index.html"),
        ("frontend/assets/main.js", f"{REMOTE_APP}/frontend/assets/main.js"),
        # DB migration
        ("migrate_batching.py", f"{REMOTE_APP}/migrate_batching.py"),
        # Requirements
        ("requirements.txt", f"{REMOTE_APP}/requirements.txt"),
    ]
    
    for local, remote in uploads:
        print(f"  Upload: {local} -> {remote}")
        sftp.put(local, remote)
    
    sftp.close()
    print(f"\n{len(uploads)} files uploaded!\n")
    
    # Install new dependencies
    run_cmd(ssh, f"cd {REMOTE_APP} && pip install -r requirements.txt 2>&1 | tail -5", "Installing dependencies")
    
    # Run DB migration for new batching columns
    run_cmd(ssh, f"cd {REMOTE_APP} && python3 migrate_batching.py data/bidroute.db", "DB migration (batching)")
    
    # Add subgroup column to DB if missing
    run_cmd(ssh, f'cd {REMOTE_APP} && python3 -c "import sqlite3; c=sqlite3.connect(\'data/bidroute.db\'); c.execute(\'ALTER TABLE monitor_tests ADD COLUMN subgroup TEXT DEFAULT \\\"\\\"\')" 2>/dev/null; echo "DB column check done"', "DB migration (monitor)")
    
    # Clean stale SKIP results for B-tests
    run_cmd(ssh, f'cd {REMOTE_APP} && python3 -c "import sqlite3; c=sqlite3.connect(\'data/bidroute.db\'); r=c.execute(\'DELETE FROM monitor_results WHERE status=\\\"skip\\\" AND test_id IN (SELECT id FROM monitor_tests WHERE code LIKE \\\"B%\\\")\'); c.commit(); print(f\\\"Cleaned {{r.rowcount}} stale SKIPs\\\")"', "Clean stale SKIPs")
    
    # Install Playwright browser
    run_cmd(ssh, "playwright install chromium 2>&1 | tail -3", "Installing Playwright Chromium")
    
    # Restart service
    run_cmd(ssh, f"systemctl restart {SERVICE}", "Restarting bidroute")
    
    import time
    time.sleep(3)
    
    run_cmd(ssh, f"systemctl is-active {SERVICE}", "Checking status")
    run_cmd(ssh, f"journalctl -u {SERVICE} -n 15 --no-pager", "Recent logs")
    
    ssh.close()
    print("\nDeploy complete!")

if __name__ == "__main__":
    deploy()
