import os, sys, datetime, django
from io import BytesIO
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db.models import Sum, Count
from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable
)
from reportlab.lib.enums import TA_CENTER

PRIMARY = colors.HexColor('#10b981')
DARK    = colors.HexColor('#0f172a')

class Command(BaseCommand):
    help = 'Generate a full system report PDF'

    def add_arguments(self, parser):
        parser.add_argument('--output', type=str, default='bubabi_system_report.pdf')

    def handle(self, *args, **options):
        output_path = options['output']
        self.stdout.write(f'📄 Generating system report: {output_path}')

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            leftMargin=2*cm, rightMargin=2*cm,
            topMargin=2*cm, bottomMargin=2*cm
        )
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle('Title2', parent=styles['Title'],
                                     fontSize=20, spaceAfter=6,
                                     textColor=colors.white, alignment=TA_CENTER)
        body = ParagraphStyle('Body', parent=styles['Normal'],
                              fontSize=9, leading=14, spaceAfter=6,
                              textColor=colors.HexColor('#374151'))
        h1 = ParagraphStyle('H1', parent=styles['Heading1'],
                            fontSize=14, spaceBefore=16, spaceAfter=8, textColor=DARK)

        story = []

        def add_section(title, content):
            story.append(Paragraph(title, h1))
            story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0')))
            story.append(Spacer(1, 6))
            for line in content:
                if isinstance(line, str):
                    story.append(Paragraph(line, body))
                elif isinstance(line, list):
                    story.append(Spacer(1, 4))
                    tbl = Table(line)
                    tbl.setStyle(TableStyle([
                        ('BACKGROUND', (0,0), (-1,0), DARK),
                        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                        ('FONTSIZE', (0,0), (-1,0), 8),
                        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                        ('BACKGROUND', (0,1), (-1,-1), colors.white),
                        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
                        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                        ('FONTSIZE', (0,1), (-1,-1), 8),
                        ('LEFTPADDING', (0,0), (-1,-1), 6),
                        ('RIGHTPADDING', (0,0), (-1,-1), 6),
                    ]))
                    story.append(tbl)
                    story.append(Spacer(1, 6))
            story.append(Spacer(1, 10))

        # Title page
        story.append(Spacer(1, 2*cm))
        story.append(Paragraph("BUBABI Clan Management System", title_style))
        story.append(Paragraph("Complete System Report", ParagraphStyle('Sub', parent=body, fontSize=10, textColor=colors.HexColor('#94a3b8'), alignment=TA_CENTER)))
        story.append(Spacer(1, 1*cm))
        story.append(Paragraph(f"Generated: {timezone.now().strftime('%d %B %Y, %H:%M')}", body))
        story.append(Paragraph(f"Django {django.__version__} | Python {sys.version.split()[0]}", body))
        story.append(Spacer(1, 1*cm))
        story.append(PageBreak())

        # Model imports
        from apps.identity.models import Member, Clan, Person, Post, PostReport, Notification
        from apps.financials.models import Contribution, Loan, Fine, Expense, LedgerEntry
        from apps.events.models import ClanEvent
        from apps.audit.models import AuditLog
        from apps.governance.models import Role, MemberRole, Vote
        from apps.genealogy.models import Relationship, Family

        # Stats
        total_members = Member.objects.count()
        active_members = Member.objects.filter(status='active').count()
        total_clans = Clan.objects.count()
        total_persons = Person.objects.count()
        total_audit = AuditLog.objects.count()
        total_posts = Post.objects.filter(is_active=True).count()
        total_reports = PostReport.objects.filter(is_resolved=False).count()
        total_families = Family.objects.count()
        total_roles = Role.objects.count()

        add_section("1. System Overview", [
            [["Metric", "Count"],
             ["Total Members", str(total_members)],
             ["Active Members", str(active_members)],
             ["Total Clans", str(total_clans)],
             ["Persons (Genealogy)", str(total_persons)],
             ["Families", str(total_families)],
             ["Active Posts", str(total_posts)],
             ["Pending Reports", str(total_reports)],
             ["Audit Logs", str(total_audit)],
             ["Roles Defined", str(total_roles)]]
        ])

        # Clans
        clan_data = [["Clan", "Code", "Members", "Public"]]
        for clan in Clan.objects.all():
            member_count = Member.objects.filter(clan=clan).count()
            clan_data.append([clan.name, clan.code or '', str(member_count), 'Yes' if clan.is_public else 'No'])
        add_section("2. Registered Clans", [clan_data])

        # Roles
        roles = Role.objects.all().order_by('-hierarchy_level')
        role_data = [["Role", "Hierarchy Level"]]
        for role in roles:
            role_data.append([role.name, str(role.hierarchy_level)])
        add_section("3. Role Hierarchy", [role_data])

        # Financial
        total_contrib = Contribution.objects.aggregate(t=Sum('amount_due'))['t'] or 0
        total_paid = Contribution.objects.filter(status='paid').aggregate(t=Sum('amount_paid'))['t'] or 0
        fin = [["Metric", "Amount (TSh)"],
               ["Total Expected", f"{total_contrib:,.0f}"],
               ["Total Collected", f"{total_paid:,.0f}"]]
        add_section("4. Financial Overview", [fin])

        # Config
        conf = [["Setting", "Value"],
                ["DEBUG", str(settings.DEBUG)],
                ["Database", settings.DATABASES['default']['ENGINE']],
                ["Language", settings.LANGUAGE_CODE],
                ["Time Zone", str(settings.TIME_ZONE)],
                ["Clan Currency", getattr(settings, 'CLAN_CURRENCY', 'TSh')]]
        add_section("5. Configuration", [conf])

        # Apps
        apps_list = [["App"]]
        for app in settings.INSTALLED_APPS:
            apps_list.append([app])
        add_section("6. Installed Applications", [apps_list])

        # Build PDF
        doc.build(story)
        pdf_data = buffer.getvalue()
        buffer.close()
        with open(output_path, 'wb') as f:
            f.write(pdf_data)
        self.stdout.write(self.style.SUCCESS(f'✅ Report saved to {output_path} ({len(pdf_data)//1024} KB)'))
