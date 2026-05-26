from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.identity.models import Clan, Member
from apps.identity.constants import MemberStatus
from apps.financials.models import Contribution
from apps.financials.constants import ContributionStatus
import calendar


class Command(BaseCommand):
    help = 'Generate monthly contribution records for all active members'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clan',
            type=str,
            default='BUBABI',
            help='Clan name (default: BUBABI)'
        )
        parser.add_argument(
            '--amount',
            type=float,
            default=50.00,
            help='Contribution amount (default: 50.00)'
        )
        parser.add_argument(
            '--month',
            type=int,
            default=None,
            help='Month number 1-12 (default: current month)'
        )
        parser.add_argument(
            '--year',
            type=int,
            default=None,
            help='Year (default: current year)'
        )
        parser.add_argument(
            '--day-due',
            type=int,
            default=28,
            help='Day of month contributions are due (default: 28)'
        )

    def handle(self, *args, **options):
        # Get clan
        try:
            clan = Clan.objects.get(name=options['clan'])
        except Clan.DoesNotExist:
            self.stdout.write(self.style.ERROR(
                f"Clan '{options['clan']}' not found."
            ))
            return

        # Determine period
        now   = timezone.now()
        month = options['month'] or now.month
        year  = options['year']  or now.year

        month_name   = calendar.month_name[month]
        period_label = f"{month_name} {year}"

        # Calculate due date
        last_day = calendar.monthrange(year, month)[1]
        day_due  = min(options['day_due'], last_day)

        from datetime import date
        due_date = date(year, month, day_due)
        amount   = options['amount']

        self.stdout.write(
            f"\nGenerating contributions for {period_label}..."
        )
        self.stdout.write(
            f"Clan: {clan.name} | "
            f"Amount: GHS {amount} | "
            f"Due: {due_date}\n"
        )

        # Get active members
        active_members = Member.objects.filter(
            clan=clan,
            status=MemberStatus.ACTIVE
        ).select_related('person')

        if not active_members.exists():
            self.stdout.write(self.style.WARNING(
                'No active members found.'
            ))
            return

        created_count  = 0
        skipped_count  = 0

        for member in active_members:
            # Check if already exists for this period
            exists = Contribution.objects.filter(
                member=member,
                period_label=period_label
            ).exists()

            if exists:
                self.stdout.write(
                    f"  SKIP: {member.person.full_name} "
                    f"— already has {period_label} contribution"
                )
                skipped_count += 1
                continue

            Contribution.objects.create(
                member=member,
                amount_due=amount,
                amount_paid=0,
                due_date=due_date,
                period_label=period_label,
                status=ContributionStatus.DUE
            )

            self.stdout.write(
                f"  CREATED: {member.person.full_name} "
                f"— GHS {amount} due {due_date}"
            )
            created_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"\nDone. Created: {created_count} | "
            f"Skipped: {skipped_count}"
        ))