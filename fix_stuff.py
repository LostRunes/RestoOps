import os

def fix_imports(filepath, class_imports):
    with open(filepath, 'r') as f:
        content = f.read()
    
    if 'from typing import TYPE_CHECKING' not in content:
        import_block = 'from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n'
        for cls, mod in class_imports:
            import_block += f'    from {mod} import {cls}\n'
        
        lines = content.split('\n')
        last_import = 0
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                last_import = i
        
        lines.insert(last_import + 1, '\n' + import_block)
        
        with open(filepath, 'w') as f:
            f.write('\n'.join(lines))
        print(f'Fixed {filepath}')

base_dir = r'C:\RestoOps\apps\api\app\models'

fix_imports(os.path.join(base_dir, 'campaign.py'), [('CampaignStep', 'app.models.campaign_step'), ('CampaignLead', 'app.models.campaign_lead')])
fix_imports(os.path.join(base_dir, 'conversation.py'), [('Message', 'app.models.message'), ('Lead', 'app.models.lead')])
fix_imports(os.path.join(base_dir, 'job_event.py'), [('Job', 'app.models.job')])
fix_imports(os.path.join(base_dir, 'lead_activity.py'), [('Lead', 'app.models.lead')])
fix_imports(os.path.join(base_dir, 'lead_contact.py'), [('Lead', 'app.models.lead')])
fix_imports(os.path.join(base_dir, 'lead_verification.py'), [('Lead', 'app.models.lead')])
fix_imports(os.path.join(base_dir, 'lead.py'), [('LeadContact', 'app.models.lead_contact'), ('LeadVerification', 'app.models.lead_verification'), ('CampaignLead', 'app.models.campaign_lead')])
fix_imports(os.path.join(base_dir, 'message.py'), [('Conversation', 'app.models.conversation')])

# Fix verification.py
verify_path = r'C:\RestoOps\apps\api\app\api\v1\endpoints\verification.py'
with open(verify_path, 'r') as f:
    v_content = f.read()
v_content = v_content.replace('        created_at=datetime.now(timezone.utc),\n        updated_at=datetime.now(timezone.utc),\n', '')
with open(verify_path, 'w') as f:
    f.write(v_content)
print('Fixed verification.py')

# Fix phase10_test.py
test_path = r'C:\RestoOps\apps\api\tests\phase10_test.py'
with open(test_path, 'r') as f:
    t_content = f.read()

t_content = t_content.replace('"order": 1, "type": "EMAIL", "delay_hours": 0, "template":', '"step_number": 1, "step_type": "EMAIL", "delay_days": 0, "body":')
t_content = t_content.replace('"order": 2, "type": "EMAIL", "delay_hours": 48, "template":', '"step_number": 2, "step_type": "EMAIL", "delay_days": 2, "body":')

old_quote = """    quote_payload = {
        "lead_id": state["lead_id"],
        "restaurant_id": state.get("restaurant_id"),
        "title": "RestoOps Pro Package",
        "notes": "Custom proposal for Test Restaurant",
        "valid_until": "2027-01-01T00:00:00Z",
        "items": [
            {"description": "Monthly Subscription", "quantity": 1, "unit_price": 499.00, "discount_pct": 10.0},
            {"description": "Onboarding & Setup", "quantity": 1, "unit_price": 199.00, "discount_pct": 0.0}
        ]
    }"""

new_quote = """    quote_payload = {
        "lead_id": state["lead_id"],
        "restaurant_id": state.get("restaurant_id", "dummy-uuid"),
        "title": "RestoOps Pro Package",
        "notes": "Custom proposal for Test Restaurant",
        "event_date": "2026-10-10",
        "valid_until": "2027-01-01",
        "items": [
            {"name": "Monthly Subscription", "quantity": 1, "unit_price": 499.00},
            {"name": "Onboarding & Setup", "quantity": 1, "unit_price": 199.00}
        ]
    }"""
t_content = t_content.replace(old_quote, new_quote)

old_call = '        "direction": "OUTBOUND",'
new_call = '        "from_number": "+1234567890",\n        "direction": "OUTBOUND",'
t_content = t_content.replace(old_call, new_call)

with open(test_path, 'w') as f:
    f.write(t_content)
print('Fixed phase10_test.py')
