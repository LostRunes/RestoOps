calls_path = r'C:\RestoOps\apps\api\app\api\v1\endpoints\calls.py'
with open(calls_path, 'r') as f:
    content = f.read()

replacement = '''    call = await call_repo.create(db, obj_in=call_in, user_id=current_user.id)
    from sqlalchemy.orm import selectinload
    from sqlalchemy import select
    from app.models.call import Call
    
    stmt = select(Call).options(selectinload(Call.events)).where(Call.id == call.id)
    result = await db.execute(stmt)
    call = result.scalar_one()
    return call'''
    
if 'selectinload(Call.events)' not in content:
    content = content.replace('    call = await call_repo.create(db, obj_in=call_in, user_id=current_user.id)\n    return call', replacement)
    with open(calls_path, 'w') as f:
        f.write(content)

test_path = r'C:\RestoOps\apps\api\tests\phase10_test.py'
with open(test_path, 'r') as f:
    t_content = f.read()

old_quote_line = '"restaurant_id": state.get("restaurant_id", "dummy-uuid"),'
new_quote_line = '"restaurant_id": state.get("restaurant_id") or str(uuid.uuid4()),'
if old_quote_line in t_content:
    t_content = t_content.replace(old_quote_line, new_quote_line)
    with open(test_path, 'w') as f:
        f.write(t_content)

print('Fixed calls.py and phase10_test.py')
