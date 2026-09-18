import re

path = r'C:\RestoOps\apps\api\app\api\v1\endpoints\quotes.py'
with open(path, 'r') as f:
    content = f.read()

# Replace:
# return await service.METHOD(
#     ...
# )
# With:
# res = await service.METHOD(...)
# await db.commit()
# return res

def replacer(match):
    prefix = match.group(1)
    call = match.group(2)
    # The return statement is wrapped in the prefix group
    return f"{prefix}res = {call}\n        await db.commit()\n        return res"

# create_quote doesn't have a try block, but it already assigns to quote and returns it.
# We just need to add await db.commit() before return quote
content = re.sub(r'(quote = await service\.create_quote\(.*?\)\n)(\s*return quote)', r'\1    await db.commit()\n\2', content)

# update_quote
content = re.sub(r'(\s+)return (await service\.update_quote\([\s\S]*?\))', replacer, content)

# add_item
content = re.sub(r'(\s+)return (await service\.add_item\([\s\S]*?\))', replacer, content)

# submit_for_approval
content = re.sub(r'(\s+)return (await service\.submit_for_approval\([\s\S]*?\))', replacer, content)

# approve_quote
content = re.sub(r'(\s+)return (await service\.approve_quote\([\s\S]*?\))', replacer, content)

# send_quote
content = re.sub(r'(\s+)return (await service\.send_quote\([\s\S]*?\))', replacer, content)

# accept_quote
content = re.sub(r'(\s+)order = (await service\.accept_quote\([\s\S]*?\))\n(\s*return order)', r'\1order = \2\n\1await db.commit()\n\3', content)

# reject_quote
content = re.sub(r'(\s+)return (await service\.reject_quote\([\s\S]*?\))', replacer, content)

# remove_item
content = re.sub(r'(\s+)(await service\.remove_item\([\s\S]*?\))\n', r'\1\2\n\1await db.commit()\n', content)

with open(path, 'w') as f:
    f.write(content)
print("Patched correctly")
