from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date
from apps.identity.models import Clan
from apps.financials.models import Contribution, Fine
from apps.financials.constants import ContributionStatus, FineStatus


class Command(BaseCommand):
    help = 'Mark overdue contributions as late and issue fines'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clan',
            type=str,
            default='BUBABI',
            help='Clan name (default: BUBABI)'
        )
        parser.add_argument(
            '--fine-amount',
            type=float,
            default=10.00,
            help='Fine amount for late payment (default: 10.00)'
        )
        parser.add_argument(
            '--issue-fines',
            action='store_true',
            help='Also issue fines for late contributions'
        )

    def handle(self, *args, **options):
        try:
            clan = Clan.objects.get(name=options['clan'])
        except Clan.DoesNotExist:
            self.stdout.write(self.style.ERROR(
                f"Clan '{options['clan']}' not found."
            ))
            return

        today = date.today()
        self.stdout.write(
            f"\nChecking overdue contributions as of {today}...\n"
        )

        # Find overdue DUE contributions
        overdue = Contribution.objects.filter(
            member__clan=clan,
            status=ContributionStatus.DUE,
            due_date__lt=today
        ).select_related('member__person')

        if not overdue.exists():
            self.stdout.write(self.style.SUCCESS(
                'No overdue contributions found.'
            ))
            return

        late_count = 0
        fine_count = 0

        for contribution in overdue:
            name = contribution.member.person.full_name

            # Mark as late
            contribution.status = ContributionStatus.LATE
            contribution.save()
            late_count += 1

            self.stdout.write(
                f"  LATE: {name} — "
                f"{contribution.period_label} "
                f"(was due {contribution.due_date})"
            )

            # Issue fine if requested
            if options['issue_fines']:
                already_fined = Fine.objects.filter(
                    member=contribution.member,
                    linked_contribution=contribution,
                    status=FineStatus.UNPAID
                ).exists()

                if not already_fined:
                    Fine.objects.create(
                        member=contribution.member,
                        reason=(
                            f"Late contribution — "
                            f"{contribution.period_label}"
                        ),
                        amount=options['fine_amount'],
                        issued_by=contribution.member,
                        linked_contribution=contribution,
                        status=FineStatus.UNPAID
                    )
                    fine_count += 1
                    self.stdout.write(
                        f"    FINE: GHS {options['fine_amount']} issued"
                    )

        self.stdout.write(self.style.SUCCESS(
            f"\nDone. Marked late: {late_count} | "
            f"Fines issued: {fine_count}"
        ))