class RoleLevel:
    MEMBER         = 0
    ELDER          = 1
    SECRETARY      = 2
    TREASURER      = 3
    DEPUTY_LEADER  = 4
    LEADER         = 5

    CHOICES = [
        (MEMBER,        'Member'),
        (ELDER,         'Elder'),
        (SECRETARY,     'Secretary'),
        (TREASURER,     'Treasurer'),
        (DEPUTY_LEADER, 'Deputy Leader'),
        (LEADER,        'Leader'),
    ]


class PermissionCode:
    # Financial
    VIEW_BALANCE         = 'financial.view_balance'
    RECORD_CONTRIBUTION  = 'financial.record_contribution'
    VERIFY_CONTRIBUTION  = 'financial.verify_contribution'
    APPROVE_EXPENSE      = 'financial.approve_expense'
    DISBURSE_LOAN        = 'financial.disburse_loan'
    ISSUE_FINE           = 'financial.issue_fine'
    WAIVE_FINE           = 'financial.waive_fine'
    INITIATE_LOAN_REVIEW = 'financial.initiate_loan_review'

    # Membership
    INVITE_MEMBER        = 'membership.invite_member'
    APPROVE_MEMBER       = 'membership.approve_pending'
    SUSPEND_MEMBER       = 'membership.suspend_member'
    INITIATE_REMOVAL     = 'membership.initiate_removal'

    # Governance
    ASSIGN_ROLE          = 'governance.assign_role'
    INITIATE_VOTE        = 'governance.initiate_vote'
    CLOSE_VOTE           = 'governance.close_vote'
    CREATE_APPROVAL      = 'governance.create_approval_request'

    # Genealogy
    ADD_PERSON           = 'genealogy.add_person'
    EDIT_PERSON          = 'genealogy.edit_person'
    ADD_RELATIONSHIP     = 'genealogy.add_relationship'


class ApprovalStatus:
    PENDING  = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    EXPIRED  = 'expired'

    CHOICES = [
        (PENDING,  'Pending'),
        (APPROVED, 'Approved'),
        (REJECTED, 'Rejected'),
        (EXPIRED,  'Expired'),
    ]


class VoteStatus:
    OPEN      = 'open'
    CLOSED    = 'closed'
    CANCELLED = 'cancelled'

    CHOICES = [
        (OPEN,      'Open'),
        (CLOSED,    'Closed'),
        (CANCELLED, 'Cancelled'),
    ]


class VoteChoice:
    YES     = 'yes'
    NO      = 'no'
    ABSTAIN = 'abstain'

    CHOICES = [
        (YES,     'Yes'),
        (NO,      'No'),
        (ABSTAIN, 'Abstain'),
    ]