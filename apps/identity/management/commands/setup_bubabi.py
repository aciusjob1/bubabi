from django.core.management.base import BaseCommand
from apps.identity.models import Clan
from apps.governance.models import Role, ClanPermission
from apps.governance.constants import RoleLevel, PermissionCode
from apps.financials.models import Account
from apps.financials.constants import AccountType


class Command(BaseCommand):
    help = 'Set up default BUBABI clan roles, permissions and accounts'

    def handle(self, *args, **kwargs):
        self.stdout.write('Setting up BUBABI clan...')

        # Get clan
        try:
            clan = Clan.objects.get(name='BUBABI')
        except Clan.DoesNotExist:
            self.stdout.write(self.style.ERROR(
                'BUBABI clan not found. Create it in admin first.'
            ))
            return

        # Create permissions
        self.stdout.write('Creating permissions...')
        permissions = {}
        perm_data = [
            (PermissionCode.VIEW_BALANCE,        'View clan balance',         'financial'),
            (PermissionCode.RECORD_CONTRIBUTION, 'Record contribution',       'financial'),
            (PermissionCode.VERIFY_CONTRIBUTION, 'Verify contribution',       'financial'),
            (PermissionCode.APPROVE_EXPENSE,     'Approve expense',           'financial'),
            (PermissionCode.DISBURSE_LOAN,       'Disburse loan',             'financial'),
            (PermissionCode.ISSUE_FINE,          'Issue fine',                'financial'),
            (PermissionCode.WAIVE_FINE,          'Waive fine',                'financial'),
            (PermissionCode.INITIATE_LOAN_REVIEW,'Initiate loan review',      'financial'),
            (PermissionCode.INVITE_MEMBER,       'Invite member',             'membership'),
            (PermissionCode.APPROVE_MEMBER,      'Approve pending member',    'membership'),
            (PermissionCode.SUSPEND_MEMBER,      'Suspend member',            'membership'),
            (PermissionCode.INITIATE_REMOVAL,    'Initiate member removal',   'membership'),
            (PermissionCode.ASSIGN_ROLE,         'Assign roles',              'governance'),
            (PermissionCode.INITIATE_VOTE,       'Initiate vote',             'governance'),
            (PermissionCode.CLOSE_VOTE,          'Close vote',                'governance'),
            (PermissionCode.CREATE_APPROVAL,     'Create approval request',   'governance'),
            (PermissionCode.ADD_PERSON,          'Add person',                'genealogy'),
            (PermissionCode.EDIT_PERSON,         'Edit person',               'genealogy'),
            (PermissionCode.ADD_RELATIONSHIP,    'Add relationship',          'genealogy'),
        ]

        for codename, description, domain in perm_data:
            perm, created = ClanPermission.objects.get_or_create(
                codename=codename,
                defaults={
                    'description': description,
                    'domain': domain
                }
            )
            permissions[codename] = perm
            status = 'Created' if created else 'Exists'
            self.stdout.write(f'  {status}: {codename}')

        # Create roles with permissions
        self.stdout.write('Creating roles...')
        role_data = [
            ('Leader', RoleLevel.LEADER, True, list(permissions.values())),
            ('Deputy Leader', RoleLevel.DEPUTY_LEADER, True, [
                permissions[PermissionCode.VIEW_BALANCE],
                permissions[PermissionCode.RECORD_CONTRIBUTION],
                permissions[PermissionCode.VERIFY_CONTRIBUTION],
                permissions[PermissionCode.INVITE_MEMBER],
                permissions[PermissionCode.APPROVE_MEMBER],
                permissions[PermissionCode.SUSPEND_MEMBER],
                permissions[PermissionCode.INITIATE_VOTE],
                permissions[PermissionCode.ADD_PERSON],
                permissions[PermissionCode.ADD_RELATIONSHIP],
            ]),
            ('Treasurer', RoleLevel.TREASURER, True, [
                permissions[PermissionCode.VIEW_BALANCE],
                permissions[PermissionCode.RECORD_CONTRIBUTION],
                permissions[PermissionCode.VERIFY_CONTRIBUTION],
                permissions[PermissionCode.APPROVE_EXPENSE],
                permissions[PermissionCode.DISBURSE_LOAN],
                permissions[PermissionCode.ISSUE_FINE],
                permissions[PermissionCode.WAIVE_FINE],
                permissions[PermissionCode.INITIATE_LOAN_REVIEW],
            ]),
            ('Secretary', RoleLevel.SECRETARY, True, [
                permissions[PermissionCode.VIEW_BALANCE],
                permissions[PermissionCode.RECORD_CONTRIBUTION],
                permissions[PermissionCode.INVITE_MEMBER],
                permissions[PermissionCode.ADD_PERSON],
                permissions[PermissionCode.ADD_RELATIONSHIP],
                permissions[PermissionCode.INITIATE_VOTE],
            ]),
            ('Elder', RoleLevel.ELDER, True, [
                permissions[PermissionCode.VIEW_BALANCE],
                permissions[PermissionCode.INITIATE_VOTE],
                permissions[PermissionCode.ADD_PERSON],
            ]),
            ('Member', RoleLevel.MEMBER, True, [
                permissions[PermissionCode.VIEW_BALANCE],
            ]),
        ]

        for name, level, is_system, perms in role_data:
            role, created = Role.objects.get_or_create(
                clan=clan,
                name=name,
                defaults={
                    'hierarchy_level': level,
                    'is_system_role': is_system
                }
            )
            role.permissions.set(perms)
            status = 'Created' if created else 'Updated'
            self.stdout.write(f'  {status}: {name}')

        # Create main account
        self.stdout.write('Creating accounts...')
        account, created = Account.objects.get_or_create(
            clan=clan,
            account_type=AccountType.POOL,
            defaults={
                'name': 'BUBABI Main Fund',
                'description': 'Primary clan fund',
                'is_active': True
            }
        )
        status = 'Created' if created else 'Exists'
        self.stdout.write(f'  {status}: BUBABI Main Fund')

        self.stdout.write(self.style.SUCCESS(
            '\nBUBABI setup complete.'
        ))