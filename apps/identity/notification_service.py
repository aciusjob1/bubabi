from apps.identity.models import Notification, Member
from apps.identity.constants import MemberStatus


class NotificationService:

    @staticmethod
    def notify(recipient, notif_type, title,
               message, link=''):
        Notification.objects.create(
            recipient=recipient,
            notif_type=notif_type,
            title=title,
            message=message,
            link=link
        )

    @staticmethod
    def notify_all_active(clan, notif_type,
                          title, message, link=''):
        members = Member.objects.filter(
            clan=clan,
            status=MemberStatus.ACTIVE
        )
        notifications = [
            Notification(
                recipient=m,
                notif_type=notif_type,
                title=title,
                message=message,
                link=link
            )
            for m in members
        ]
        Notification.objects.bulk_create(notifications)

    @staticmethod
    def notify_contribution_due(contribution):
        NotificationService.notify(
            recipient=contribution.member,
            notif_type='contribution_due',
            title='Contribution Due',
            message=(
                f"Your contribution of {contribution.member.clan.currency} {contribution.amount_due} "
                f"for {contribution.period_label} is due on "
                f"{contribution.due_date}."
            ),
            link='/contributions/'
        )

    @staticmethod
    def notify_fine_issued(fine):
        NotificationService.notify(
            recipient=fine.member,
            notif_type='fine_issued',
            title='Fine Issued',
            message=(
                f"A fine of GHS {fine.amount} has been issued to you. "
                f"Reason: {fine.reason}"
            ),
            link='/fines/'
        )

    @staticmethod
    def notify_loan_status(loan, status):
        messages = {
            'approved':  f"Your loan of {loan.borrower.clan.currency} {loan.amount_approved} has been approved.",
            'rejected':  f"Your loan request of {loan.borrower.clan.currency} {loan.amount_requested} was rejected.",
            'disbursed': f"{loan.borrower.clan.currency} {loan.amount_approved} has been disbursed to you.",
        }
        NotificationService.notify(
            recipient=loan.borrower,
            notif_type=f'loan_{status}',
            title=f'Loan {status.capitalize()}',
            message=messages.get(status, ''),
            link='/loans/'
        )

    @staticmethod
    def notify_vote_opened(vote):
        NotificationService.notify_all_active(
            clan=vote.clan,
            notif_type='vote_opened',
            title='New Vote Open',
            message=(
                f"A new vote has been opened: '{vote.topic}'. "
                f"Closes on {vote.closes_at.strftime('%d %b %Y')}."
            ),
            link='/dashboard/'
        )

    @staticmethod
    def notify_announcement(announcement):
        members = Member.objects.filter(
            clan=announcement.clan,
            status=MemberStatus.ACTIVE
        )
        notifications = [
            Notification(
                recipient=m,
                notif_type='announcement',
                title=announcement.title,
                message=announcement.content[:200],
                link=f'/announcements/{announcement.id}/'
            )
            for m in members
            if m != announcement.author
        ]
        Notification.objects.bulk_create(notifications)

    @staticmethod
    def get_unread_count(member):
        return Notification.objects.filter(
            recipient=member,
            is_read=False
        ).count()

    @staticmethod
    def mark_all_read(member):
        Notification.objects.filter(
            recipient=member,
            is_read=False
        ).update(is_read=True)
        
@classmethod
def notify_post_hidden(cls, post):
    """Notify post author that their post was hidden by reports."""
    Notification.objects.create(
        recipient=post.author,
        title="Post Hidden by Community Reports",
        message=f"Your post has been hidden after receiving {post.report_count} reports. A moderator will review it.",
        notification_type='moderation',
        link=f'/posts/#post-{post.id}'
    )