import re

path = r'C:\RestoOps\apps\api\app\api\v1\endpoints\quotes.py'
with open(path, 'r') as f:
    content = f.read()

# Replace return patterns in all mutation endpoints with a commit first
endpoints = [
    'create_quote', 'update_quote', 'add_quote_item', 'submit_quote',
    'approve_quote', 'send_quote', 'accept_quote', 'reject_quote'
]

for ep in endpoints:
    # find the block for the endpoint
    match = re.search(f'async def {ep}\\(.*?return (\\w+)', content, flags=re.DOTALL)
    if match:
        var_name = match.group(1)
        if var_name == "order":
            content = content.replace(f"return {var_name}", f"await db.commit()\n        return {var_name}", 1)
        else:
            content = content.replace(f"return {var_name}", f"await db.commit()\n    return {var_name}", 1)

# For remove_quote_item, it doesn't return anything.
if "await service.remove_item(" in content:
    content = content.replace(
        "await service.remove_item(quote_id, current_user.organization_id, item_id)",
        "await service.remove_item(quote_id, current_user.organization_id, item_id)\n        await db.commit()"
    )

with open(path, 'w') as f:
    f.write(content)
print("Patched quotes.py")
