with open('apps/financials/views.py', 'r') as f:
    content = f.read()

# Find the context in record_payment_view
old = "'contribution': contribution, 'balance_due': balance_due, 'current_user_name': current_user_name"
new = "'contribution': contribution, 'balance_due': balance_due, 'current_user_name': current_user_name, 'can_use_cash': request.user.is_superuser or request.user.is_treasurer"

if old in content:
    content = content.replace(old, new)
    print("✅ can_use_cash added to view context")
else:
    print("❌ Context pattern not found - check the view manually")

with open('apps/financials/views.py', 'w') as f:
    f.write(content)
