from django.conf import settings
import json

DEFAULT_BANNER = 'https://images.unsplash.com/photo-1511632765486-a01980e01a18?w=1920&q=80'
DEFAULT_LOGO = None  # We'll use text-based logo fallback in templates


def clan_settings(request):
    """Pass dynamic clan branding variables to all templates."""
    clan = None
    if request.user.is_authenticated:
        clan = getattr(request.user, 'clan', None)

    # Get banner with fallback
    clan_banner = None
    if clan and clan.banner_image:
        clan_banner = clan.banner_image
    else:
        # Create a fake URL object for the default banner
        clan_banner = type('FakeBanner', (), {'url': DEFAULT_BANNER})()

    # Get logo (keep None if not set - templates handle this)
    clan_logo = getattr(clan, 'logo', None) if clan else None

    return {
        'clan_primary_color': getattr(clan, 'primary_color', settings.CLAN_PRIMARY_COLOR) if clan else settings.CLAN_PRIMARY_COLOR,
        'clan_accent_color': getattr(clan, 'accent_color', settings.CLAN_ACCENT_COLOR) if clan else settings.CLAN_ACCENT_COLOR,
        'clan_sidebar_color': getattr(clan, 'sidebar_color', '#3d1a1a') if clan else '#3d1a1a',
        'clan_blur_intensity': getattr(clan, 'blur_intensity', '16px') if clan else '16px',
        'clan_currency': getattr(clan, 'currency', settings.CLAN_CURRENCY) if clan else settings.CLAN_CURRENCY,
        'clan_name': clan.name if clan else 'BUBABI',
        'clan_logo': clan_logo,
        'clan_banner': clan_banner,
        'clan_motto': getattr(clan, 'motto', ''),
    }


def payment_methods(request):
    """Add clan payment methods to template context."""
    default_methods = {
        'cash_enabled': True,
        'mobile_money_enabled': True,
        'bank_transfer_enabled': True,
        'default_method': 'mobile_money',
        'mobile_providers': [
            {'code': 'mpesa', 'name': 'M-Pesa (Vodacom)', 'prefixes': ['074','075','076','25574','25575','25576']},
            {'code': 'tigo', 'name': 'Tigo Pesa', 'prefixes': ['065','067','071','25565','25567','25571']},
            {'code': 'airtel', 'name': 'Airtel Money', 'prefixes': ['068','069','078','25568','25569','25578']},
            {'code': 'halotel', 'name': 'Halotel', 'prefixes': ['061','062','25561','25562']},
            {'code': 'ttcl', 'name': 'TTCL', 'prefixes': ['073','25573']},
            {'code': 'zantel', 'name': 'Zantel', 'prefixes': ['077','25577']},
        ],
        'banks': [
            {'code': 'crdb', 'name': 'CRDB Bank'},
            {'code': 'nmb', 'name': 'NMB Bank'},
            {'code': 'nbc', 'name': 'NBC Bank'},
            {'code': 'equity', 'name': 'Equity Bank'},
        ]
    }

    if not request.user.is_authenticated:
        return {'payment_methods': default_methods}

    clan = getattr(request.user, 'clan', None)
    if not clan:
        return {'payment_methods': default_methods}

    stored = getattr(clan, 'payment_methods', None)
    if stored:
        try:
            methods = json.loads(stored)
            default_methods.update(methods)
        except (json.JSONDecodeError, TypeError):
            pass

    return {'payment_methods': default_methods}
