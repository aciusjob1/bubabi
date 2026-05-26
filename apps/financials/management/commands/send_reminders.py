from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.identity.models import Clan
from apps.financials.models import Contribution
from apps.financials.constants import ContributionStatus
from apps.core.sms_service import SMSService


class Command(BaseCommand):
    help = 'Send SMS reminders for upcoming and late contributions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clan', type=str, default='BUBABI'
        )
        parser.add_argument(
            '--days-before', type=int, default=7,
            help='Days before due date to remind'
        )

    def handle(self, *args, **options):
        try:
            clan = Clan.objects.get(name=options['clan'])
        except Clan.DoesNotExist:
            self.stdout.write(self.style.ERROR('Clan not found.'))
            return

        today        = timezone.now().date()
        remind_date  = today + timedelta(days=options['days_before'])

        # Upcoming reminders
        upcoming = Contribution.objects.filter(
            member__clan=clan,
            status=ContributionStatus.DUE,
            due_date=remind_date
        ).select_related('member__person')

        self.stdout.write(f'Sending {upcoming.count()} upcoming reminders...')
        for c in upcoming:
            SMSService.notify_contribution_due(c)
            self.stdout.write(f'  Sent to {c.member.person.full_name}')

        # Late reminders
        late = Contribution.objects.filter(
            member__clan=clan,
            status=ContributionStatus.LATE
        ).select_related('member__person')

        self.stdout.write(f'Sending {late.count()} late reminders...')
        for c in late:
            if c.member.phone:
                msg = (
                    f"BUBABI REMINDER: Your contribution of "
                    f"TSh {c.amount_due:,.0f} for {c.period_label} "
                    f"is OVERDUE. Please pay immediately to avoid fines."
                )
                SMSService.send([c.member.phone], msg)
                self.stdout.write(f'  Sent to {c.member.person.full_name}')

        self.stdout.write(self.style.SUCCESS('Done.'))