"""
Update DNS records for pochtamt.online via Beget API.
1. Improve SPF record
2. Add DMARC subdomain  
3. Add DKIM subdomain (try)
"""
import httpx, json, sys

LOGIN = "egleboxr"
PASSW = "&rA%S0AnHqy!"
DOMAIN = "pochtamt.online"

def api(method, params=None):
    q = {"login": LOGIN, "passwd": PASSW, "input_format": "json", "output_format": "json"}
    if params is not None:
        q["input_data"] = json.dumps(params)
    r = httpx.get(f"https://api.beget.com/api/{method}", params=q, timeout=15)
    return r.json()

def show(label, result):
    status = result.get("answer", {}).get("status", "?")
    print(f"  [{status.upper()}] {label}")
    if status != "success":
        errors = result.get("answer", {}).get("errors", [])
        for e in errors:
            print(f"    Error: {e.get('error_text', e)}")
    return status == "success"

print("=" * 60)
print("DNS ANTI-SPAM CONFIGURATION FOR", DOMAIN)
print("=" * 60)

# ─── STEP 1: Update main domain — improve SPF ───
print("\n[1] Updating main domain SPF record...")

# Write format uses: {value, priority} for A/MX/TXT
result = api("dns/changeRecords", {
    "fqdn": DOMAIN,
    "records": {
        "A": [{"priority": 10, "value": "155.212.223.142"}],
        "MX": [
            {"priority": 10, "value": "mx1.beget.com"},
            {"priority": 20, "value": "mx2.beget.com"}
        ],
        "TXT": [
            {"priority": 10, "value": "v=spf1 include:beget.com ~all"}
        ]
    }
})
show("Main domain SPF update", result)

# ─── STEP 2: Add _dmarc subdomain ───
print("\n[2] Creating _dmarc subdomain with DMARC policy...")

# First, create the subdomain
result = api("domain/addSubdomainVirtual", {"subdomain": "_dmarc", "domain_id": 13986380})
show("Create _dmarc subdomain", result)

# Then set DNS records for it
result = api("dns/changeRecords", {
    "fqdn": f"_dmarc.{DOMAIN}",
    "records": {
        "TXT": [
            {"priority": 10, "value": "v=DMARC1; p=none; rua=mailto:1@pochtamt.online; adkim=r; aspf=r"}
        ]
    }
})
show("DMARC TXT record", result)

# ─── STEP 3: Try to add DKIM ───
print("\n[3] Attempting DKIM configuration...")

# Try creating default._domainkey subdomain
result = api("domain/addSubdomainVirtual", {"subdomain": "default._domainkey", "domain_id": 13986380})
show("Create default._domainkey subdomain", result)

# ─── STEP 4: Verify ───
print("\n[4] Verifying DNS records...")

result = api("dns/getData", {"fqdn": DOMAIN})
answer = result.get("answer", {}).get("result", {})
records = answer.get("records", {})
print(f"  Main domain records:")
for rtype, recs in records.items():
    if rtype in ("TXT", "A", "MX"):
        print(f"    {rtype}: {json.dumps(recs, ensure_ascii=False)}")

result = api("dns/getData", {"fqdn": f"_dmarc.{DOMAIN}"})
answer = result.get("answer", {})
if answer.get("status") == "success":
    recs = answer.get("result", {}).get("records", {})
    print(f"  _dmarc subdomain: {json.dumps(recs, ensure_ascii=False)}")
else:
    print(f"  _dmarc subdomain: {json.dumps(answer, ensure_ascii=False)}")

print("\n" + "=" * 60)
print("DONE")
print("=" * 60)
