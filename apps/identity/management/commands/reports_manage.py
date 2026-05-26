from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.identity.models import Post, PostReport
from apps.identity.notification_service import NotificationService
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Manage post reports - list, resolve, dismiss, or delete reported posts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--list', action='store_true',
            help='List all unresolved reports'
        )
        parser.add_argument(
            '--resolve', type=int,
            help='Resolve a specific report by ID'
        )
        parser.add_argument(
            '--dismiss', type=int,
            help='Dismiss a report by ID (restore post if threshold not met)'
        )
        parser.add_argument(
            '--delete-post', type=int,
            help='Delete the post associated with a report ID'
        )
        parser.add_argument(
            '--resolve-all', action='store_true',
            help='Dismiss all unresolved reports'
        )
        parser.add_argument(
            '--resolver', type=str, default='superuser',
            help='Email of the moderator resolving reports'
        )
        parser.add_argument(
            '--note', type=str, default='',
            help='Resolution note'
        )
        parser.add_argument(
            '--stats', action='store_true',
            help='Show report statistics'
        )
        parser.add_argument(
            '--cleanup', action='store_true',
            help='Auto-resolve reports for deleted/inactive posts'
        )

    def handle(self, *args, **options):
        # Get resolver
        try:
            if options['resolver'] == 'superuser':
                resolver = User.objects.filter(is_superuser=True).first()
            else:
                resolver = User.objects.get(email=options['resolver'])
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Resolver '{options['resolver']}' not found"))
            return

        if not resolver:
            self.stdout.write(self.style.ERROR("No resolver found"))
            return

        # --stats
        if options['stats']:
            self.show_stats()
            return

        # --list
        if options['list']:
            self.list_reports()
            return

        # --cleanup
        if options['cleanup']:
            self.cleanup_reports(resolver)
            return

        # --resolve-all
        if options['resolve_all']:
            self.resolve_all(resolver, options['note'])
            return

        # --resolve
        if options['resolve']:
            self.resolve_report(options['resolve'], resolver, options['note'])
            return

        # --dismiss
        if options['dismiss']:
            self.dismiss_report(options['dismiss'], resolver, options['note'])
            return

        # --delete-post
        if options['delete_post']:
            self.delete_reported_post(options['delete_post'], resolver, options['note'])
            return

        # Default: show help
        self.stdout.write("Use --list, --resolve, --dismiss, --delete-post, --resolve-all, --stats, or --cleanup")
        self.stdout.write("Example: python manage.py reports_manage --list")

    def show_stats(self):
        """Display report statistics."""
        unresolved = PostReport.objects.filter(is_resolved=False)
        total = unresolved.count()
        by_reason = {}
        for report in unresolved:
            reason = report.get_reason_display()
            by_reason[reason] = by_reason.get(reason, 0) + 1

        hidden_posts = Post.objects.filter(is_hidden_by_reports=True, is_active=True).count()

        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('📊 POST REPORT STATISTICS'))
        self.stdout.write('='*60)
        self.stdout.write(f'  Unresolved Reports: {total}')
        self.stdout.write(f'  Hidden Posts:       {hidden_posts}')
        self.stdout.write(f'\n  By Reason:')
        for reason, count in by_reason.items():
            self.stdout.write(f'    {reason}: {count}')
        self.stdout.write('='*60 + '\n')

    def list_reports(self):
        """List all unresolved reports."""
        reports = PostReport.objects.filter(is_resolved=False).select_related(
            'post__author__person', 'reported_by__person'
        ).order_by('-created_at')

        if not reports:
            self.stdout.write(self.style.SUCCESS('✅ No unresolved reports'))
            return

        self.stdout.write('\n' + '='*80)
        self.stdout.write(self.style.WARNING('🚨 UNRESOLVED POST REPORTS'))
        self.stdout.write('='*80)

        for r in reports:
            post = r.post
            self.stdout.write(f'\n  📌 Report #{r.id}')
            self.stdout.write(f'     Post ID: {post.id} | Author: {post.author.person.full_name if post.author.person else post.author.email}')
            self.stdout.write(f'     Content: {post.content[:80]}...')
            self.stdout.write(f'     Reported by: {r.reported_by.person.full_name if r.reported_by.person else r.reported_by.email}')
            self.stdout.write(f'     Reason: {r.get_reason_display()}')
            self.stdout.write(f'     Details: {r.details[:100] if r.details else "N/A"}')
            self.stdout.write(f'     Date: {r.created_at.strftime("%Y-%m-%d %H:%M")}')
            self.stdout.write(f'     Post Hidden: {"Yes" if post.is_hidden_by_reports else "No"}')
            self.stdout.write(f'     Total Reports on Post: {PostReport.objects.filter(post=post, is_resolved=False).count()}')

        self.stdout.write('\n' + '='*80)
        self.stdout.write(f'  Total: {reports.count()} unresolved reports')
        self.stdout.write('='*80 + '\n')

    def resolve_report(self, report_id, resolver, note):
        """Resolve a specific report by dismissing it."""
        try:
            report = PostReport.objects.get(id=report_id, is_resolved=False)
        except PostReport.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Report #{report_id} not found or already resolved'))
            return

        post = report.post
        report.is_resolved = True
        report.resolved_by = resolver
        report.resolved_at = timezone.now()
        report.resolution_note = note or 'Resolved via management command'
        report.save()

        # Update post report count
        unresolved_count = PostReport.objects.filter(post=post, is_resolved=False).count()
        post.report_count = unresolved_count

        # Restore post if under threshold
        if post.is_hidden_by_reports and unresolved_count < Post.REPORT_THRESHOLD:
            post.is_hidden_by_reports = False
            self.stdout.write(self.style.SUCCESS(f'  Post #{post.id} restored (reports below threshold)'))

        post.save()

        self.stdout.write(self.style.SUCCESS(f'✅ Report #{report_id} resolved'))
        self.stdout.write(f'   Post: #{post.id} | Remaining reports: {unresolved_count}')
        self.stdout.write(f'   Resolver: {resolver.person.full_name if resolver.person else resolver.email}')

    def dismiss_report(self, report_id, resolver, note):
        """Alias for resolve_report."""
        self.resolve_report(report_id, resolver, note or 'Dismissed via management command')

    def delete_reported_post(self, report_id, resolver, note):
        """Delete the post and resolve all its reports."""
        try:
            report = PostReport.objects.get(id=report_id)
        except PostReport.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Report #{report_id} not found'))
            return

        post = report.post
        post_title = post.content[:50]
        post.is_active = False
        post.save()

        # Resolve all reports for this post
        resolved_count = PostReport.objects.filter(post=post, is_resolved=False).update(
            is_resolved=True,
            resolved_by=resolver,
            resolved_at=timezone.now(),
            resolution_note=note or f'Post deleted via management command by {resolver.email}'
        )

        # Notify post author
        if post.author != resolver:
            from apps.identity.models import Notification
            Notification.objects.create(
                recipient=post.author,
                title="Your Post Has Been Removed",
                message=f"Your post '{post_title}...' has been removed by a moderator.",
                link='/posts/'
            )

        self.stdout.write(self.style.SUCCESS(f'✅ Post #{post.id} deleted'))
        self.stdout.write(f'   Content: {post_title}...')
        self.stdout.write(f'   Reports resolved: {resolved_count}')
        self.stdout.write(f'   Resolver: {resolver.person.full_name if resolver.person else resolver.email}')

    def resolve_all(self, resolver, note):
        """Dismiss all unresolved reports."""
        count = PostReport.objects.filter(is_resolved=False).count()
        if count == 0:
            self.stdout.write(self.style.SUCCESS('✅ No unresolved reports to process'))
            return

        PostReport.objects.filter(is_resolved=False).update(
            is_resolved=True,
            resolved_by=resolver,
            resolved_at=timezone.now(),
            resolution_note=note or 'Batch resolved via management command'
        )

        # Restore all hidden posts that are now under threshold
        posts = Post.objects.filter(is_hidden_by_reports=True)
        restored = 0
        for post in posts:
            unresolved = PostReport.objects.filter(post=post, is_resolved=False).count()
            post.report_count = unresolved
            if unresolved < Post.REPORT_THRESHOLD:
                post.is_hidden_by_reports = False
                restored += 1
            post.save()

        self.stdout.write(self.style.SUCCESS(f'✅ Resolved {count} reports'))
        self.stdout.write(f'   Posts restored: {restored}')
        self.stdout.write(f'   Resolver: {resolver.person.full_name if resolver.person else resolver.email}')

    def cleanup_reports(self, resolver):
        """Auto-resolve reports for deleted or inactive posts."""
        inactive_reports = PostReport.objects.filter(
            is_resolved=False,
            post__is_active=False
        )

        deleted_reports = PostReport.objects.filter(
            is_resolved=False
        ).exclude(post__in=Post.objects.all())

        total = inactive_reports.count() + deleted_reports.count()

        if total == 0:
            self.stdout.write(self.style.SUCCESS('✅ No orphaned reports to clean up'))
            return

        inactive_reports.update(
            is_resolved=True,
            resolved_by=resolver,
            resolved_at=timezone.now(),
            resolution_note='Auto-resolved: Post is inactive'
        )

        deleted_reports.update(
            is_resolved=True,
            resolved_by=resolver,
            resolved_at=timezone.now(),
            resolution_note='Auto-resolved: Post has been deleted'
        )

        self.stdout.write(self.style.SUCCESS(f'✅ Cleaned up {total} orphaned reports'))
