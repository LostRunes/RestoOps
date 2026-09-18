from sqlalchemy.orm import selectinload
from sqlalchemy import select
from app.models.call import Call

calls_path = r'C:\RestoOps\apps\api\app\api\v1\endpoints\calls.py'
with open(calls_path, 'r') as f:
    content = f.read()

replacement = '''        call = await service.start_call(
            org_id=current_user.organization_id,
            lead_id=payload.lead_id,
            provider_type=payload.provider,
            from_identifier=payload.from_number,
            to_identifier=payload.to,
            initiated_by=current_user.id,
            restaurant_id=payload.restaurant_id,
            conversation_id=payload.conversation_id,
        )
        from sqlalchemy.orm import selectinload
        from sqlalchemy import select
        from app.models.call import Call
        stmt = select(Call).options(selectinload(Call.events)).where(Call.id == call.id)
        result = await db.execute(stmt)
        return result.scalar_one()'''

old_str = '''        call = await service.start_call(
            org_id=current_user.organization_id,
            lead_id=payload.lead_id,
            provider_type=payload.provider,
            from_identifier=payload.from_number,
            to_identifier=payload.to,
            initiated_by=current_user.id,
            restaurant_id=payload.restaurant_id,
            conversation_id=payload.conversation_id,
        )
        return call'''

if 'selectinload(Call.events)' not in content:
    content = content.replace(old_str, replacement)
    with open(calls_path, 'w') as f:
        f.write(content)


test_path = r'C:\RestoOps\apps\api\tests\phase10_test.py'
with open(test_path, 'r') as f:
    t_content = f.read()

# Fix Quote title check (title doesn't exist in QuoteResponse)
t_content = t_content.replace('check("Quote title matches", quote.get("title") == "RestoOps Pro Package")', 'check("Quote event date matches", quote.get("event_date") == "2026-10-10")')

# Fix Quote items payload
# Currently: {"description": "Setup", "quantity": 1, "unit_price": 500}
# QuoteItemCreate needs "name"
t_content = t_content.replace('{"description": "Setup Fee", "quantity": 1, "unit_price": 500.00}', '{"name": "Setup Fee", "quantity": 1, "unit_price": 500.00}')

with open(test_path, 'w') as f:
    f.write(t_content)

print("Patched calls.py and phase10_test.py")
