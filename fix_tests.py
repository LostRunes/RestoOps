import os

test_path = r'C:\RestoOps\apps\api\tests\phase10_test.py'
with open(test_path, 'r') as f:
    t_content = f.read()

if 'import uuid' not in t_content:
    t_content = t_content.replace('import sys\n', 'import sys\nimport uuid\n')

quotes_section = '# ─── 8. QUOTES'
restaurant_setup = '''
# ─── SETUP RESTAURANT FOR QUOTES ──────────────────────────────────────────────
if token and not state.get("restaurant_id"):
    try:
        r_payload = {"name": "Quote Test Restaurant", "address": "123 Test"}
        res = session.post(f"{API}/restaurants", headers=headers, json=r_payload)
        if res.status_code == 201:
            state["restaurant_id"] = res.json().get("id")
    except Exception:
        pass

'''

if 'SETUP RESTAURANT FOR QUOTES' not in t_content:
    t_content = t_content.replace(quotes_section, restaurant_setup + quotes_section)

t_content = t_content.replace('state.get("restaurant_id", str(uuid.uuid4()))', 'state.get("restaurant_id")')

with open(test_path, 'w') as f:
    f.write(t_content)

print('Fixed test script')
