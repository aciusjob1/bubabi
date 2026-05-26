from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from io import BytesIO
from datetime import datetime


# ── Brand Colors ───────────────────────────────
GREEN  = colors.HexColor('#10b981')
DARK   = colors.HexColor('#0f172a')
GRAY   = colors.HexColor('#64748b')
LIGHT  = colors.HexColor('#f1f5f9')
RED    = colors.HexColor('#ef4444')
YELLOW = colors.HexColor('#f59e0b')
WHITE  = colors.white


def get_styles():
    styles = getSampleStyleSheet()
    return {
        'title': ParagraphStyle(
            'title',
            fontSize=20,
            fontName='Helvetica-Bold',
            textColor=DARK,
            spaceAfter=4,
        ),
        'subtitle': ParagraphStyle(
            'subtitle',
            fontSize=11,
            fontName='Helvetica',
            textColor=GRAY,
            spaceAfter=2,
        ),
        'section': ParagraphStyle(
            'section',
            fontSize=10,
            fontName='Helvetica-Bold',
            textColor=DARK,
            spaceBefore=14,
            spaceAfter=6,
            borderPad=4,
        ),
        'body': ParagraphStyle(
            'body',
            fontSize=9,
            fontName='Helvetica',
            textColor=DARK,
            spaceAfter=3,
        ),
        'small': ParagraphStyle(
            'small',
            fontSize=8,
            fontName='Helvetica',
            textColor=GRAY,
        ),
        'right': ParagraphStyle(
            'right',
            fontSize=9,
            fontName='Helvetica',
            textColor=DARK,
            alignment=TA_RIGHT,
        ),
        'center': ParagraphStyle(
            'center',
            fontSize=9,
            fontName='Helvetica',
            textColor=DARK,
            alignment=TA_CENTER,
        ),
    }


def make_header(clan_name, report_title, subtitle=''):
    styles  = get_styles()
    content = []

    # Top bar
    header_data = [[
        Paragraph(f'<b>{clan_name}</b>', ParagraphStyle(
            'h', fontSize=14, fontName='Helvetica-Bold',
            textColor=WHITE
        )),
        Paragraph(
            f'Generated: {datetime.now().strftime("%d %b %Y %H:%M")}',
            ParagraphStyle(
                'hr', fontSize=8, fontName='Helvetica',
                textColor=WHITE, alignment=TA_RIGHT
            )
        ),
    ]]

    header_table = Table(header_data, colWidths=[10*cm, 7.5*cm])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), DARK),
        ('PADDING',    (0,0), (-1,-1), 10),
        ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
    ]))
    content.append(header_table)
    content.append(Spacer(1, 0.4*cm))

    content.append(Paragraph(report_title, styles['title']))
    if subtitle:
        content.append(Spacer(1, 0.3*cm))
        content.append(Paragraph(subtitle, styles['subtitle']))
    content.append(HRFlowable(
        width='100%', thickness=2,
        color=GREEN, spaceAfter=10
    ))
    return content


def make_table(headers, rows, col_widths=None):
    data = [headers] + rows
    if not col_widths:
        col_widths = [17.5*cm / len(headers)] * len(headers)

    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        # Header row
        ('BACKGROUND',  (0,0), (-1,0),  DARK),
        ('TEXTCOLOR',   (0,0), (-1,0),  WHITE),
        ('FONTNAME',    (0,0), (-1,0),  'Helvetica-Bold'),
        ('FONTSIZE',    (0,0), (-1,0),  8),
        ('PADDING',     (0,0), (-1,0),  8),
        ('ALIGN',       (0,0), (-1,0),  'LEFT'),

        # Data rows
        ('FONTNAME',    (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE',    (0,1), (-1,-1), 8),
        ('PADDING',     (0,1), (-1,-1), 6),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [WHITE, LIGHT]),
        ('GRID',        (0,0), (-1,-1), 0.3, colors.HexColor('#e2e8f0')),
        ('VALIGN',      (0,0), (-1,-1), 'MIDDLE'),
    ]))
    return t


def tsh(value):
    try:
        value = float(value)
        if value >= 1_000_000_000:
            return f'TSh {value/1_000_000_000:.1f}B'
        elif value >= 1_000_000:
            return f'TSh {value/1_000_000:.1f}M'
        elif value >= 1_000:
            return f'TSh {value/1_000:.1f}K'
        return f'TSh {value:,.0f}'
    except Exception:
        return f'TSh {value}'


# ══════════════════════════════════════════════
# REPORT 1 — Monthly Financial Statement
# ══════════════════════════════════════════════

def generate_monthly_statement(clan, period_label):
    from apps.financials.models import Contribution, Expense
    from apps.financials.constants import ContributionStatus
    from apps.financials.services.financial_service import FinancialService

    svc     = FinancialService()
    buffer  = BytesIO()
    styles  = get_styles()

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=1.5*cm, leftMargin=1.5*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm
    )

    content = make_header(
        clan.name,
        f'Financial Statement — {period_label}',
        f'Period: {period_label}'
    )

    # ── Summary Stats ──
    # balance = svc.get_clan_balance(clan)  # Removed - was showing entire clan balance
    paid       = Contribution.objects.filter(
                   member__clan=clan,
                   period_label=period_label,
                   status=ContributionStatus.PAID
                 ).count()
    due        = Contribution.objects.filter(
                   member__clan=clan,
                   period_label=period_label
                 ).count()
    collected  = Contribution.objects.filter(
                   member__clan=clan,
                   period_label=period_label,
                   status=ContributionStatus.PAID
                 )
    from django.db.models import Sum
    total_in   = collected.aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
    period_balance = total_in  # Money collected this period only
    total_out  = Expense.objects.filter(clan=clan).aggregate(
                   Sum('amount'))['amount__sum'] or 0

    summary_data = [
        ['Period Balance',  tsh(period_balance), 'Collection Rate', f'{round(paid/due*100 if due else 0, 1)}%'],
        ['Total Collected',  tsh(total_in),   'Total Expenses',  tsh(total_out)],
        ['Members Paid',     str(paid),       'Members Due',     str(due)],
    ]

    summary_table = Table(summary_data, colWidths=[4.5*cm, 4*cm, 4.5*cm, 4*cm])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND',  (0,0), (0,-1), LIGHT),
        ('BACKGROUND',  (2,0), (2,-1), LIGHT),
        ('FONTNAME',    (0,0), (-1,-1), 'Helvetica'),
        ('FONTNAME',    (1,0), (1,-1), 'Helvetica-Bold'),
        ('FONTNAME',    (3,0), (3,-1), 'Helvetica-Bold'),
        ('FONTSIZE',    (0,0), (-1,-1), 9),
        ('PADDING',     (0,0), (-1,-1), 8),
        ('GRID',        (0,0), (-1,-1), 0.3, colors.HexColor('#e2e8f0')),
        ('TEXTCOLOR',   (0,0), (0,-1), GRAY),
        ('TEXTCOLOR',   (2,0), (2,-1), GRAY),
    ]))

    content.append(Paragraph('Summary', styles['section']))
    content.append(summary_table)
    content.append(Spacer(1, 0.4*cm))

    # ── Contributions Detail ──
    content.append(Paragraph(
        f'Contributions — {period_label}', styles['section']
    ))

    contributions = Contribution.objects.filter(
        member__clan=clan,
        period_label=period_label
    ).select_related('member__person').order_by(
        'member__person__full_name'
    )

    rows = []
    for c in contributions:
        status_color = '#065f46' if c.status == 'paid' else '#991b1b'
        rows.append([
            c.member.person.full_name if c.member.person else c.member.email,
            tsh(c.amount_due),
            tsh(c.amount_paid),
            tsh(c.balance_due),
            c.status.upper(),
            c.due_date.strftime('%d %b %Y') if c.due_date else '—',
        ])

    if rows:
        t = make_table(
            ['Member', 'Due', 'Paid', 'Balance', 'Status', 'Due Date'],
            rows,
            [5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2*cm, 3*cm]
        )
        content.append(t)
    else:
        content.append(Paragraph(
            'No contributions for this period.', styles['body']
        ))

    content.append(Spacer(1, 0.4*cm))

    # ── Expenses ──
    content.append(Paragraph('Expenses', styles['section']))

    expenses = Expense.objects.filter(clan=clan).order_by('-expense_date')[:20]
    if expenses.exists():
        exp_rows = [
            [
                e.description,
                e.category.upper(),
                tsh(e.amount),
                e.expense_date.strftime('%d %b %Y'),
                e.approved_by.person.full_name if e.approved_by.person else '—',
            ]
            for e in expenses
        ]
        content.append(make_table(
            ['Description', 'Category', 'Amount', 'Date', 'Approved By'],
            exp_rows,
            [5.5*cm, 2.5*cm, 3*cm, 2.5*cm, 4*cm]
        ))
    else:
        content.append(Paragraph('No expenses recorded.', styles['body']))

    # ── Footer ──
    content.append(Spacer(1, 0.5*cm))
    content.append(HRFlowable(width='100%', thickness=0.5, color=LIGHT))
    content.append(Spacer(1, 0.2*cm))
    content.append(Paragraph(
        f'{clan.name} · Confidential Financial Document · '
        f'Generated {datetime.now().strftime("%d %b %Y %H:%M")}',
        styles['small']
    ))

    doc.build(content)
    buffer.seek(0)
    return buffer


# ══════════════════════════════════════════════
# REPORT 2 — Members Owing List
# ══════════════════════════════════════════════

def generate_owing_list(clan):
    from apps.financials.models import Contribution, Fine
    from apps.financials.constants import ContributionStatus, FineStatus
    from django.db.models import Sum

    buffer  = BytesIO()
    styles  = get_styles()

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=1.5*cm, leftMargin=1.5*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm
    )

    content = make_header(
        clan.name,
        'Members Owing Report',
        f'As of {datetime.now().strftime("%d %B %Y")}'
    )

    # Outstanding contributions
    content.append(Paragraph('Outstanding Contributions', styles['section']))

    owing = Contribution.objects.filter(
        member__clan=clan,
        status__in=[
            ContributionStatus.DUE,
            ContributionStatus.LATE,
            ContributionStatus.PENALIZED
        ]
    ).select_related('member__person').order_by(
        'member__person__full_name', '-due_date'
    )

    if owing.exists():
        rows = []
        for c in owing:
            rows.append([
                c.member.person.full_name if c.member.person else c.member.email,
                c.period_label,
                tsh(c.amount_due),
                tsh(c.amount_paid),
                tsh(c.balance_due),
                c.status.upper(),
            ])

        content.append(make_table(
            ['Member', 'Period', 'Due', 'Paid', 'Balance', 'Status'],
            rows,
            [4.5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 3*cm]
        ))

        total_owing = owing.aggregate(
            total=Sum('amount_due')
        )['total'] or 0
        content.append(Spacer(1, 0.3*cm))
        content.append(Paragraph(
            f'<b>Total Outstanding: {tsh(total_owing)}</b>',
            styles['body']
        ))
    else:
        content.append(Paragraph(
            '✅ All members are up to date.', styles['body']
        ))

    # Unpaid Fines
    content.append(Paragraph('Unpaid Fines', styles['section']))

    fines = Fine.objects.filter(
        member__clan=clan,
        status=FineStatus.UNPAID
    ).select_related('member__person', 'issued_by__person')

    if fines.exists():
        fine_rows = [
            [
                f.member.person.full_name if f.member.person else f.member.email,
                f.reason[:40],
                tsh(f.amount),
                f.created_at.strftime('%d %b %Y'),
            ]
            for f in fines
        ]
        content.append(make_table(
            ['Member', 'Reason', 'Amount', 'Issued'],
            fine_rows,
            [5*cm, 6*cm, 3*cm, 3.5*cm]
        ))
    else:
        content.append(Paragraph('No unpaid fines.', styles['body']))

    # Footer
    content.append(Spacer(1, 0.5*cm))
    content.append(HRFlowable(width='100%', thickness=0.5, color=LIGHT))
    content.append(Spacer(1, 0.2*cm))
    content.append(Paragraph(
        f'{clan.name} · Confidential · '
        f'Generated {datetime.now().strftime("%d %b %Y %H:%M")}',
        styles['small']
    ))

    doc.build(content)
    buffer.seek(0)
    return buffer


# ══════════════════════════════════════════════
# REPORT 3 — Annual Summary
# ══════════════════════════════════════════════

def generate_annual_summary(clan, year):
    from apps.financials.models import Contribution, Expense, Loan
    from apps.financials.constants import ContributionStatus, LoanStatus
    from apps.financials.services.financial_service import FinancialService
    from apps.identity.models import Member
    from apps.identity.constants import MemberStatus
    from django.db.models import Sum, Count

    svc    = FinancialService()
    buffer = BytesIO()
    styles = get_styles()

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=1.5*cm, leftMargin=1.5*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm
    )

    content = make_header(
        clan.name,
        f'Annual Financial Summary {year}',
        f'Fiscal Year: January {year} — December {year}'
    )

    # Key Stats
    balance     = svc.get_clan_balance(clan)
    members     = Member.objects.filter(
                    clan=clan, status=MemberStatus.ACTIVE
                  ).count()
    total_in    = Contribution.objects.filter(
                    member__clan=clan,
                    status=ContributionStatus.PAID
                  ).aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
    total_out   = Expense.objects.filter(
                    clan=clan
                  ).aggregate(Sum('amount'))['amount__sum'] or 0
    active_loans = Loan.objects.filter(
                    borrower__clan=clan,
                    status=LoanStatus.DISBURSED
                  ).aggregate(Sum('amount_approved'))['amount_approved__sum'] or 0

    stats = [
        ['Fund Balance',    tsh(balance)],
        ['Active Members',  str(members)],
        ['Total Collected', tsh(total_in)],
        ['Total Expenses',  tsh(total_out)],
        ['Net Position',    tsh(total_in - total_out)],
        ['Loans Active',    tsh(active_loans)],
    ]

    stats_table = Table(stats, colWidths=[6*cm, 5*cm])
    stats_table.setStyle(TableStyle([
        ('FONTNAME',   (0,0), (0,-1), 'Helvetica'),
        ('FONTNAME',   (1,0), (1,-1), 'Helvetica-Bold'),
        ('FONTSIZE',   (0,0), (-1,-1), 10),
        ('PADDING',    (0,0), (-1,-1), 8),
        ('TEXTCOLOR',  (0,0), (0,-1), GRAY),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [WHITE, LIGHT]),
        ('GRID',       (0,0), (-1,-1), 0.3, colors.HexColor('#e2e8f0')),
    ]))

    content.append(Paragraph('Key Figures', styles['section']))
    content.append(stats_table)
    content.append(Spacer(1, 0.4*cm))

    # Monthly breakdown
    content.append(Paragraph('Monthly Collection Breakdown', styles['section']))

    from apps.financials.models import Contribution as C
    periods = C.objects.filter(
        member__clan=clan
    ).values('period_label').distinct().order_by('period_label')

    monthly_rows = []
    for p in periods:
        label    = p['period_label']
        paid     = C.objects.filter(
                     member__clan=clan,
                     period_label=label,
                     status=ContributionStatus.PAID
                   ).aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
        expected = C.objects.filter(
                     member__clan=clan,
                     period_label=label
                   ).aggregate(Sum('amount_due'))['amount_due__sum'] or 0
        rate     = round(paid/expected*100 if expected else 0, 1)
        monthly_rows.append([
            label,
            tsh(expected),
            tsh(paid),
            f'{rate}%',
        ])

    if monthly_rows:
        content.append(make_table(
            ['Period', 'Expected', 'Collected', 'Rate'],
            monthly_rows,
            [5*cm, 4*cm, 4*cm, 4.5*cm]
        ))
    else:
        content.append(Paragraph('No data for this year.', styles['body']))

    # Expense breakdown
    content.append(Paragraph('Expenses by Category', styles['section']))

    exp_cats = Expense.objects.filter(
        clan=clan
    ).values('category').annotate(
        total=Sum('amount'), count=Count('id')
    ).order_by('-total')

    if exp_cats.exists():
        exp_rows = [
            [e['category'].upper(), str(e['count']), tsh(e['total'])]
            for e in exp_cats
        ]
        content.append(make_table(
            ['Category', 'Count', 'Total'],
            exp_rows,
            [7*cm, 4*cm, 6.5*cm]
        ))
    else:
        content.append(Paragraph('No expenses recorded.', styles['body']))

    # Footer
    content.append(Spacer(1, 0.5*cm))
    content.append(HRFlowable(width='100%', thickness=0.5, color=LIGHT))
    content.append(Spacer(1, 0.2*cm))
    content.append(Paragraph(
        f'{clan.name} · Annual Report {year} · Confidential · '
        f'Generated {datetime.now().strftime("%d %b %Y")}',
        styles['small']
    ))

    doc.build(content)
    buffer.seek(0)
    return buffer


# ══════════════════════════════════════════════
# REPORT 4 — Member Statement
# ══════════════════════════════════════════════

def generate_member_statement(member):
    from apps.financials.models import Contribution, Fine, Loan
    from django.db.models import Sum

    buffer  = BytesIO()
    styles  = get_styles()

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=1.5*cm, leftMargin=1.5*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm
    )

    name = member.person.full_name if member.person else member.email

    content = make_header(
        member.clan.name if member.clan else 'BUBABI',
        f'Member Statement',
        f'{name} · {member.email}'
    )

    # Member info
    info = [
        ['Full Name',   name],
        ['Email',       member.email],
        ['Phone',       member.phone or '—'],
        ['Status',      member.status.upper()],
        ['Member Since', member.joined_at.strftime('%d %b %Y') if member.joined_at else '—'],
        ['Role',        member.clan_roles.first().role.name if member.clan_roles.exists() else 'Member'],
    ]

    info_table = Table(info, colWidths=[4*cm, 9*cm])
    info_table.setStyle(TableStyle([
        ('FONTNAME',   (0,0), (0,-1), 'Helvetica'),
        ('FONTNAME',   (1,0), (1,-1), 'Helvetica-Bold'),
        ('FONTSIZE',   (0,0), (-1,-1), 9),
        ('PADDING',    (0,0), (-1,-1), 7),
        ('TEXTCOLOR',  (0,0), (0,-1), GRAY),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [WHITE, LIGHT]),
        ('GRID',       (0,0), (-1,-1), 0.3, colors.HexColor('#e2e8f0')),
    ]))

    content.append(Paragraph('Member Information', styles['section']))
    content.append(info_table)
    content.append(Spacer(1, 0.4*cm))

    # Contributions
    contributions = Contribution.objects.filter(
        member=member
    ).order_by('-due_date')

    total_due  = contributions.aggregate(
        Sum('amount_due'))['amount_due__sum'] or 0
    total_paid = contributions.aggregate(
        Sum('amount_paid'))['amount_paid__sum'] or 0

    content.append(Paragraph(
        f'Contributions — Total Due: {tsh(total_due)} · '
        f'Total Paid: {tsh(total_paid)} · '
        f'Balance: {tsh(total_due - total_paid)}',
        styles['section']
    ))

    if contributions.exists():
        rows = [
            [
                c.period_label,
                tsh(c.amount_due),
                tsh(c.amount_paid),
                tsh(c.balance_due),
                c.status.upper(),
            ]
            for c in contributions
        ]
        content.append(make_table(
            ['Period', 'Due', 'Paid', 'Balance', 'Status'],
            rows,
            [4*cm, 3.5*cm, 3.5*cm, 3.5*cm, 3*cm]
        ))
    else:
        content.append(Paragraph('No contributions.', styles['body']))

    # Loans
    loans = Loan.objects.filter(borrower=member).order_by('-created_at')

    content.append(Paragraph('Loans', styles['section']))

    if loans.exists():
        loan_rows = [
            [
                tsh(l.amount_requested),
                tsh(l.amount_approved) if l.amount_approved else '—',
                l.status.upper(),
                l.purpose[:30],
                l.due_date.strftime('%d %b %Y') if l.due_date else '—',
            ]
            for l in loans
        ]
        content.append(make_table(
            ['Requested', 'Approved', 'Status', 'Purpose', 'Due'],
            loan_rows,
            [3*cm, 3*cm, 2.5*cm, 5.5*cm, 3.5*cm]
        ))
    else:
        content.append(Paragraph('No loans.', styles['body']))

    # Fines
    fines = Fine.objects.filter(member=member).order_by('-created_at')

    content.append(Paragraph('Fines', styles['section']))

    if fines.exists():
        fine_rows = [
            [f.reason[:40], tsh(f.amount), f.status.upper(),
             f.created_at.strftime('%d %b %Y')]
            for f in fines
        ]
        content.append(make_table(
            ['Reason', 'Amount', 'Status', 'Date'],
            fine_rows,
            [6*cm, 3*cm, 3*cm, 5.5*cm]
        ))
    else:
        content.append(Paragraph('No fines.', styles['body']))

    # Footer
    content.append(Spacer(1, 0.5*cm))
    content.append(HRFlowable(width='100%', thickness=0.5, color=LIGHT))
    content.append(Spacer(1, 0.2*cm))
    content.append(Paragraph(
        f'{member.clan.name if member.clan else "BUBABI"} · '
        f'Member Statement · Confidential · '
        f'Generated {datetime.now().strftime("%d %b %Y %H:%M")}',
        styles['small']
    ))

    doc.build(content)
    buffer.seek(0)
    return buffer