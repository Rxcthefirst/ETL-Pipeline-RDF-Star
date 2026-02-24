"""Quick test of the class explorer API endpoints."""
import urllib.request
import json

BASE = "http://localhost:7878"

def get(path):
    r = urllib.request.urlopen(BASE + path)
    return json.loads(r.read().decode())

# 1. Check ontologies
print("=== /ontologies ===")
data = get("/ontologies")
print(f"  Classes: {data['counts']['classes']}")
if data['classes']:
    first = data['classes'][0]
    print(f"  First class URI: {repr(first['uri'])}")
    print(f"  First class label: {repr(first['label'])}")
    test_uri = first['uri']
else:
    print("  NO CLASSES FOUND")
    exit(1)

# Pick a class that should have neighbors (Movie)
movie_uri = None
for c in data['classes']:
    if 'Movie' in c['uri'] and 'movieApp' in c['uri']:
        movie_uri = c['uri']
        break

if not movie_uri:
    movie_uri = test_uri
print(f"\n  Using test URI: {movie_uri}")

# 2. Test neighbors
print("\n=== /api/class/neighbors ===")
try:
    ndata = get(f"/api/class/neighbors?uri={urllib.request.quote(movie_uri, safe='')}")
    print(f"  Neighbors: {len(ndata['neighbors'])}")
    for n in ndata['neighbors'][:5]:
        print(f"    {n['label']} ({n['direction']}) via {n.get('propertyLabel','?')}")
except Exception as e:
    print(f"  ERROR: {e}")

# 3. Test properties
print("\n=== /api/class/properties ===")
try:
    pdata = get(f"/api/class/properties?uri={urllib.request.quote(movie_uri, safe='')}")
    print(f"  Datatype: {len(pdata['datatype'])}, Object: {len(pdata['object'])}")
    for p in pdata['datatype'][:3]:
        print(f"    DT: {p['label']}")
    for p in pdata['object'][:3]:
        print(f"    OBJ: {p['label']}")
except Exception as e:
    print(f"  ERROR: {e}")

# 4. Test individuals
print("\n=== /api/class/individuals ===")
try:
    idata = get(f"/api/class/individuals?uri={urllib.request.quote(movie_uri, safe='')}")
    print(f"  Individuals: {idata['count']}")
    for ind in idata['individuals'][:3]:
        print(f"    {ind['label']} - {len(ind['properties'])} props")
except Exception as e:
    print(f"  ERROR: {e}")

print("\n=== DONE ===")

