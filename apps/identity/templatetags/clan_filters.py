from django import template
from django.utils.html import format_html

register = template.Library()


# ══════════════════════════════════════════════
# CURRENCY FILTERS
# ══════════════════════════════════════════════

@register.filter
def tsh(value):
    """
    Format a number as Tanzanian Shillings.
    Usage: {{ value|tsh }}
    Examples:
        1500000 -> TSh 1.5M
        50000   -> TSh 50.0K
        500     -> TSh 500
    """
    try:
        value = float(value)
        if value >= 1_000_000_000:
            return f'TSh {value/1_000_000_000:.1f}B'
        elif value >= 1_000_000:
            return f'TSh {value/1_000_000:.1f}M'
        elif value >= 1_000:
            return f'TSh {value/1_000:.1f}K'
        return f'TSh {value:,.0f}'
    except (ValueError, TypeError):
        return f'TSh {value}'


@register.filter
def ghs(value):
    """
    Format a number as Ghanaian Cedis (legacy support).
    Usage: {{ value|ghs }}
    """
    try:
        value = float(value)
        if value >= 1_000_000:
            return f'GHS {value/1_000_000:.2f}M'
        elif value >= 1_000:
            return f'GHS {value/1_000:,.0f}'
        return f'GHS {value:,.2f}'
    except (ValueError, TypeError):
        return f'GHS {value}'


@register.filter
def clan_currency(value, clan=None):
    """
    Format a number in the clan's configured currency.
    Usage: {{ value|clan_currency:request.user.clan }}
    Falls back to TSh if no clan or currency configured.
    """
    try:
        value = float(value)
        
        # Determine currency symbol
        if clan and hasattr(clan, 'currency') and clan.currency:
            symbol = clan.currency
        else:
            symbol = 'TSh'
        
        if value >= 1_000_000_000:
            return f'{symbol} {value/1_000_000_000:.1f}B'
        elif value >= 1_000_000:
            return f'{symbol} {value/1_000_000:.1f}M'
        elif value >= 1_000:
            return f'{symbol} {value/1_000:.1f}K'
        return f'{symbol} {value:,.0f}'
    except (ValueError, TypeError):
        symbol = clan.currency if (clan and hasattr(clan, 'currency')) else 'TSh'
        return f'{symbol} {value}'


@register.simple_tag
def format_currency(value, clan):
    """
    Template tag version of clan_currency filter.
    Usage: {% format_currency amount request.user.clan %}
    """
    return clan_currency(value, clan)


# ══════════════════════════════════════════════
# MATH FILTERS
# ══════════════════════════════════════════════

@register.filter
def multiply(value, arg):
    """Multiply the value by the argument."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def percentage(value, total):
    """Calculate percentage."""
    try:
        if float(total) == 0:
            return 0
        return round((float(value) / float(total)) * 100, 1)
    except (ValueError, TypeError):
        return 0


@register.filter
def subtract(value, arg):
    """Subtract arg from value."""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def divide(value, arg):
    """Divide value by arg."""
    try:
        if float(arg) == 0:
            return 0
        return float(value) / float(arg)
    except (ValueError, TypeError):
        return 0


# ══════════════════════════════════════════════
# UTILITY FILTERS
# ══════════════════════════════════════════════

@register.filter
def truncate_chars(value, max_length):
    """Truncate a string to max_length characters."""
    try:
        value = str(value)
        if len(value) > max_length:
            return value[:max_length] + '...'
        return value
    except (ValueError, TypeError):
        return value


@register.filter
def first_char(value):
    """Get the first character of a string."""
    try:
        value = str(value).strip()
        return value[0].upper() if value else '?'
    except (ValueError, TypeError, IndexError):
        return '?'


# ══════════════════════════════════════════════
# CLAN BRANDING TAGS
# ══════════════════════════════════════════════

@register.simple_tag
def clan_primary_color(clan):
    """Get clan's primary color, fallback to default green."""
    if clan and hasattr(clan, 'primary_color') and clan.primary_color:
        return clan.primary_color
    return '#10b981'


@register.simple_tag
def clan_accent_color(clan):
    """Get clan's accent color, fallback to default indigo."""
    if clan and hasattr(clan, 'accent_color') and clan.accent_color:
        return clan.accent_color
    return '#6366f1'


# ══════════════════════════════════════════════
# AVATAR TAG
# ══════════════════════════════════════════════

@register.simple_tag
def avatar(member, size=40):
    """
    Display member avatar - profile_image if available, otherwise colored initials.
    Usage: {% avatar member 42 %}
           {% avatar request.user 30 %}
    """
    # Check if member has a person with profile_image
    if (member and 
        hasattr(member, 'person') and 
        member.person and 
        member.person.profile_image and
        hasattr(member.person.profile_image, 'url')):
        return format_html(
            '<img src="{}" style="width:{}px;height:{}px;border-radius:50%;'
            'object-fit:cover;flex-shrink:0;border:2px solid #e2e8f0;" alt="Avatar">',
            member.person.profile_image.url,
            size,
            size
        )
    
    # Fallback: colored circle with initials
    initial = '?'
    if member:
        if hasattr(member, 'person') and member.person and member.person.full_name:
            initial = member.person.full_name[0].upper()
        elif hasattr(member, 'email') and member.email:
            initial = member.email[0].upper()
        elif hasattr(member, 'full_name') and member.full_name:
            initial = member.full_name[0].upper()
    
    # Different colors based on name for variety
    colors = [
        '#10b981',  # Green
        '#6366f1',  # Indigo
        '#f59e0b',  # Amber
        '#ef4444',  # Red
        '#3b82f6',  # Blue
        '#8b5cf6',  # Violet
        '#ec4899',  # Pink
        '#14b8a6',  # Teal
        '#f97316',  # Orange
        '#06b6d4',  # Cyan
    ]
    
    # Use member ID or string representation for consistent color
    if member and hasattr(member, 'id'):
        color_key = hash(str(member.id))
    elif member:
        color_key = hash(str(member))
    else:
        color_key = hash(initial)
    
    color = colors[color_key % len(colors)]
    font_size = size / 40 * 1.1
    
    return format_html(
        '<div style="width:{}px;height:{}px;background:{};border-radius:50%;'
        'display:flex;align-items:center;justify-content:center;'
        'font-weight:700;color:#fff;font-size:{}rem;flex-shrink:0;'
        'border:2px solid {};">{}</div>',
        size, size, color, font_size, color, initial
    )


# ══════════════════════════════════════════════
# STATUS BADGE TAG
# ══════════════════════════════════════════════

@register.simple_tag
def status_badge(status):
    """Display a colored status badge."""
    colors = {
        'active':    '#d1fae5',
        'paid':      '#d1fae5',
        'approved':  '#d1fae5',
        'disbursed': '#fef3c7',
        'due':       '#dbeafe',
        'late':      '#fee2e2',
        'suspended': '#fef3c7',
        'pending':   '#dbeafe',
        'invited':   '#ede9fe',
        'penalized': '#ffe4e6',
        'removed':   '#f1f5f9',
        'rejected':  '#f1f5f9',
        'unpaid':    '#fee2e2',
        'defaulted': '#fee2e2',
    }
    
    text_colors = {
        'active':    '#065f46',
        'paid':      '#065f46',
        'approved':  '#065f46',
        'disbursed': '#92400e',
        'due':       '#1e40af',
        'late':      '#991b1b',
        'suspended': '#92400e',
        'pending':   '#1e40af',
        'invited':   '#5b21b6',
        'penalized': '#9f1239',
        'removed':   '#475569',
        'rejected':  '#475569',
        'unpaid':    '#991b1b',
        'defaulted': '#991b1b',
    }
    
    bg = colors.get(status, '#f1f5f9')
    tc = text_colors.get(status, '#475569')
    
    return format_html(
        '<span style="background:{};color:{};padding:0.18rem 0.6rem;'
        'border-radius:20px;font-size:0.68rem;font-weight:600;'
        'text-transform:uppercase;">{}</span>',
        bg, tc, status
    )
@register.simple_tag
def detect_provider(phone, payment_methods):
    """Detect mobile money provider from phone number."""
    if not phone or not payment_methods:
        return None
    
    # Normalize phone
    phone = phone.strip().replace(' ', '').replace('-', '')
    if phone.startswith('+'):
        phone = phone[1:]
    if phone.startswith('0'):
        phone = '255' + phone[1:]
    
    providers = payment_methods.get('mobile_providers', [])
    for provider in providers:
        for prefix in provider.get('prefixes', []):
            if phone.startswith(prefix):
                return provider
    return None
