import re

path = r'C:\RestoOps\apps\api\app\api\v1\endpoints\quotes.py'
with open(path, 'r') as f:
    content = f.read()

# I will just insert await db.commit() before EVERY return in the try block
# But for simplicity, let's just do a string replacement for the specific lines.

replacements = [
    ("return await service.update_quote(", "res = await service.update_quote(\n            quote_id, current_user.organization_id, **payload.model_dump(exclude_unset=True)\n        )\n        await db.commit()\n        return res\n        #"),
    ("return await service.add_item(", "res = await service.add_item(\n            quote_id, current_user.organization_id, **payload.model_dump()\n        )\n        await db.commit()\n        return res\n        #"),
    ("return await service.submit_for_approval(quote_id, current_user.organization_id)", "res = await service.submit_for_approval(quote_id, current_user.organization_id)\n        await db.commit()\n        return res"),
    ("return await service.approve_quote(", "res = await service.approve_quote(\n            quote_id, current_user.organization_id, user_id=current_user.id\n        )\n        await db.commit()\n        return res\n        #"),
    ("return await service.send_quote(", "res = await service.send_quote(\n            quote_id, current_user.organization_id, user_id=current_user.id\n        )\n        await db.commit()\n        return res\n        #"),
    ("return await service.reject_quote(", "res = await service.reject_quote(\n            quote_id, current_user.organization_id, user_id=current_user.id\n        )\n        await db.commit()\n        return res\n        #")
]

for old, new in replacements:
    content = content.replace(old, new)

# Fix the list_quotes mess
content = re.sub(r'(await db\.commit\(\)\n    )+', '', content)

with open(path, 'w') as f:
    f.write(content)
print("Patched quotes.py properly")
