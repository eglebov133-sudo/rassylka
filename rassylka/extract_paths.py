"""Extract all API paths from OpenAPI schema."""
import httpx

r = httpx.get("https://umit-prod.purpleplane-it.com/api/schema/", timeout=30)
text = r.text

# Parse YAML-style paths
paths = []
for line in text.split("\n"):
    stripped = line.strip()
    if stripped.startswith("/api/") and stripped.endswith(":"):
        path = stripped[:-1]  # remove trailing ":"
        paths.append(path)

print(f"Found {len(paths)} API paths:\n")

# Group by category
groups = {}
for p in paths:
    parts = p.split("/")
    # Group by the first significant part after /api/vX/
    if len(parts) >= 4:
        version = parts[2] if parts[2] in ("v1", "v2") else ""
        category = parts[3] if version else parts[2]
        key = f"{version}/{category}" if version else category
    else:
        key = "other"
    groups.setdefault(key, []).append(p)

for key in sorted(groups.keys()):
    print(f"\n=== {key} ===")
    for p in groups[key]:
        print(f"  {p}")
