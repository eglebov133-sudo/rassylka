"""
Probe umit.pro API to discover real endpoints.
Tries common DRF patterns, Swagger, root API, and path variations.
"""
import httpx
import json
import sys

BASE_API = "https://umit-prod.purpleplane-it.com"
BASE_SITE = "https://umit.pro"
TOKEN_URL = f"{BASE_API}/api/token/"
USERNAME = "+79822880268"
PASSWORD = "ANBp3Gnuq88jwrj!!"

def get_token(client):
    r = client.post(TOKEN_URL, json={"username": USERNAME, "password": PASSWORD})
    if r.status_code == 200:
        data = r.json()
        return data.get("access") or data.get("token") or data.get("key")
    print(f"Auth failed: {r.status_code} {r.text[:200]}")
    return None

def probe(client, method, url, headers, label=""):
    try:
        if method == "GET":
            r = client.get(url, headers=headers, follow_redirects=True, timeout=10)
        elif method == "OPTIONS":
            r = client.options(url, headers=headers, timeout=10)
        else:
            r = client.get(url, headers=headers, follow_redirects=True, timeout=10)
        
        status = r.status_code
        ct = r.headers.get("content-type", "")

        if status == 404:
            return status  # skip 404s silently
        
        icon = "OK" if status == 200 else "!!" if status in (301, 302, 403, 401) else "??"
        print(f"  {icon} {status:3d} {method:7s} {url}")
        if status == 200 and "json" in ct:
            try:
                data = r.json()
                if isinstance(data, dict):
                    keys = list(data.keys())[:15]
                    print(f"       JSON keys: {keys}")
                    if all(isinstance(v, str) and v.startswith("http") for v in list(data.values())[:3] if isinstance(v, str)):
                        print(f"       DRF API ROOT FOUND!")
                        for k, v in data.items():
                            print(f"         {k}: {v}")
                elif isinstance(data, list):
                    print(f"       JSON list: {len(data)} items")
                    if data and isinstance(data[0], dict):
                        print(f"       First item keys: {list(data[0].keys())[:10]}")
            except:
                pass
        elif status == 200:
            print(f"       Content-Type: {ct}, size: {len(r.text)}")
        elif status in (301, 302):
            print(f"       Redirect -> {r.headers.get('location','?')}")
        elif status in (401, 403):
            print(f"       Auth: {r.text[:100]}")
        return status
    except Exception as e:
        print(f"  ERR {method:7s} {url} -> {type(e).__name__}: {str(e)[:80]}")
        return 0

def main():
    client = httpx.Client(verify=True, timeout=15)
    
    print("=" * 60)
    print("UMIT.PRO API DISCOVERY")
    print("=" * 60)
    
    print("\n[1] Authentication")
    token = get_token(client)
    if not token:
        print("FATAL: Cannot authenticate")
        sys.exit(1)
    print(f"  OK Token: {token[:20]}...")
    h = {"Authorization": f"Bearer {token}"}
    
    print("\n[2] API Root / Docs (showing only non-404)")
    for url in [
        f"{BASE_API}/api/", f"{BASE_API}/api/v2/", f"{BASE_API}/api/v1/", f"{BASE_API}/api/v3/",
        f"{BASE_API}/docs/", f"{BASE_API}/swagger/", f"{BASE_API}/swagger.json", f"{BASE_API}/swagger.yaml",
        f"{BASE_API}/redoc/", f"{BASE_API}/api/schema/", f"{BASE_API}/api/docs/",
        f"{BASE_API}/openapi.json", f"{BASE_API}/openapi/", f"{BASE_API}/api/openapi/",
        f"{BASE_SITE}/api/", f"{BASE_SITE}/api/v2/",
    ]:
        probe(client, "GET", url, h)
    
    all_paths = [
        # Bids
        "/api/v2/bids/", "/api/bids/", "/api/v1/bids/",
        # Products
        "/api/v2/products/", "/api/v2/product/", "/api/v2/catalog/",
        "/api/v2/marketplace/", "/api/v2/marketplace/products/",
        "/api/v2/goods/", "/api/v2/items/", "/api/v2/offers/",
        "/api/v2/listings/", "/api/v2/stock/", "/api/v2/warehouse/",
        "/api/products/", "/api/catalog/", "/api/v1/products/",
        # Cart
        "/api/v2/cart/", "/api/v2/basket/", "/api/v2/shopping-cart/",
        "/api/cart/", "/api/basket/", "/api/v1/cart/",
        # Orders
        "/api/v2/orders/", "/api/v2/order/", "/api/v2/my-orders/",
        "/api/v2/purchases/", "/api/orders/", "/api/v1/orders/",
        # Profile
        "/api/v2/profile/", "/api/v2/me/", "/api/v2/user/",
        "/api/v2/users/me/", "/api/v2/account/", "/api/v2/my/",
        "/api/v2/auth/user/", "/api/v2/auth/me/",
        "/api/profile/", "/api/me/", "/api/user/", "/api/account/",
        "/api/v1/profile/", "/api/v1/me/", "/api/v2/users/profile/",
        # Favorites
        "/api/v2/favorites/", "/api/v2/favourite/", "/api/v2/bookmarks/",
        "/api/v2/wishlist/", "/api/v2/saved/",
        "/api/favorites/", "/api/v1/favorites/",
        # Folders
        "/api/v2/folders/", "/api/v2/collections/", "/api/v2/lists/",
        "/api/folders/", "/api/v1/folders/",
        # Technique
        "/api/v2/technique-cards/", "/api/v2/technique/", "/api/v2/vehicles/",
        "/api/v2/vehicle/", "/api/v2/cars/", "/api/v2/garage/",
        "/api/v2/machinery/", "/api/v2/equipment/", "/api/v2/transport/",
        "/api/v2/tech/", "/api/v2/techniques/",
        "/api/vehicles/", "/api/v1/vehicles/",
        # Reviews
        "/api/v2/reviews/", "/api/v2/ratings/", "/api/v2/feedback/",
        "/api/v2/comments/", "/api/reviews/",
        # Partner
        "/api/v2/partner/", "/api/v2/partners/", "/api/v2/referral/",
        "/api/partner/",
        # Seller
        "/api/v2/seller/", "/api/v2/sellers/", "/api/v2/seller/products/",
        "/api/v2/my-products/", "/api/v2/my/products/",
        "/api/v2/seller/orders/", "/api/v2/storefront/",
        "/api/seller/",
        # Notifications
        "/api/v2/notifications/", "/api/v2/messages/", "/api/v2/chat/",
        # Categories / Brands
        "/api/v2/categories/", "/api/v2/brands/", "/api/v2/regions/",
        "/api/categories/", "/api/brands/",
        # Misc
        "/api/v2/search/", "/api/v2/support/", "/api/v2/help/",
        "/api/v2/settings/", "/api/v2/config/",
    ]
    
    print(f"\n[3] Scanning {len(all_paths)} endpoint paths (only showing non-404)...")
    found = []
    for path in all_paths:
        st = probe(client, "GET", BASE_API + path, h)
        if st != 404 and st != 0:
            found.append((path, st))
    
    print(f"\n{'=' * 60}")
    print(f"RESULTS: Found {len(found)} non-404 endpoints")
    for path, st in found:
        print(f"  {st} {path}")
    print("=" * 60)
    
    client.close()

if __name__ == "__main__":
    main()
