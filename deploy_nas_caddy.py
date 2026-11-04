#!/usr/bin/env python3
"""Deploy studio.hackerlife.fun on Cloudflare DNS and NAS Caddy reverse proxy."""
import subprocess
import sys

SSH_KEY = r"C:\Users\Liang\.ssh\id_ed25519_nopass"
NAS_HOST = "root@192.168.2.200"

REMOTE_PY = r'''
import json, pathlib, re, subprocess, urllib.request

config = pathlib.Path("/etc/caddy/Caddyfile").read_text()
m = re.search(r"(?m)^\s*dns\s+cloudflare\s+(\S+)\s*$", config)
if not m:
    raise SystemExit("Cannot find Cloudflare DNS token in /etc/caddy/Caddyfile")
token = m.group(1).strip('"')

def cf_api(path, data=None, method=None):
    req = urllib.request.Request(
        "https://api.cloudflare.com/client/v4/" + path,
        data=json.dumps(data).encode() if data else None,
        headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json",
        },
        method=method or ("POST" if data else "GET"),
    )
    with urllib.request.urlopen(req, timeout=25) as resp:
        res = json.load(resp)
    if not res.get("success"):
        raise SystemExit(f"Cloudflare API error: {res}")
    return res["result"]

zones = cf_api("zones?name=hackerlife.fun")
zone_id = zones[0]["id"]
records = cf_api(f"zones/{zone_id}/dns_records?per_page=100")
for r in records:
    if r["type"] in ("A", "AAAA", "CNAME"):
        print(f"EXISTING DNS: {r['type']:5s} {r['name']:30s} -> {r['content']} (proxied={r.get('proxied')})")

# Find octendra.hackerlife.fun or hackerlife.fun as reference
ref = next((r for r in records if r["name"] == "octendra.hackerlife.fun"), None)
if not ref:
    ref = next((r for r in records if r["name"] == "hackerlife.fun" and r["type"] in ("A", "CNAME")), None)
if not ref:
    ref = records[0]

desired = {
    "type": "CNAME",
    "name": "studio.hackerlife.fun",
    "content": "hackerlife.fun",
    "ttl": 120,
    "proxied": False,
}
# If octendra uses CNAME or A, match its proxied setting
if ref["name"] == "octendra.hackerlife.fun":
    desired["type"] = ref["type"]
    desired["content"] = ref["content"]
    desired["proxied"] = ref.get("proxied", False)

existing_studio = [r for r in records if r["name"] == "studio.hackerlife.fun"]
if not existing_studio:
    cf_api(f"zones/{zone_id}/dns_records", desired, method="POST")
    print(f"âœ?Created DNS {desired['type']} studio.hackerlife.fun -> {desired['content']} (proxied={desired['proxied']})")
else:
    rec_id = existing_studio[0]["id"]
    cf_api(f"zones/{zone_id}/dns_records/{rec_id}", desired, method="PUT")
    print(f"âœ?Updated DNS {desired['type']} studio.hackerlife.fun -> {desired['content']} (proxied={desired['proxied']})")

# Write /etc/caddy/sites/sanguo-studio.caddy
site_path = pathlib.Path("/etc/caddy/sites/sanguo-studio.caddy")
site_content = """# Sanguo Director Studio (Rust L1-L5 Family AI Video Production Platform)
studio.hackerlife.fun {
    import cloudflare_dns
    encode zstd gzip
    reverse_proxy 192.168.2.222:18443 {
        flush_interval -1
        header_up Host {host}
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-For {remote_host}
        header_up X-Forwarded-Proto {scheme}
    }
}
"""
site_path.write_text(site_content)
site_path.chmod(0o644)
print(f"âœ?Wrote {site_path}")

# Validate and reload Caddy
caddy_bin = "/usr/local/bin/caddy" if pathlib.Path("/usr/local/bin/caddy").exists() else "caddy"
subprocess.run([caddy_bin, "validate", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"], check=True)
subprocess.run(["systemctl", "reload", "caddy"], check=True)
print("âœ?Caddy validated and reloaded successfully!")
'''

def main():
    proc = subprocess.run(
        ["ssh", "-i", SSH_KEY, "-o", "BatchMode=yes", NAS_HOST, "python3", "-"],
        input=REMOTE_PY,
        text=True,
        encoding="utf-8",
    )
    sys.exit(proc.returncode)

if __name__ == "__main__":
    main()
