class AccountType:
    POOL           = 'pool'
    MEMBER_LEDGER  = 'member_ledger'
    EXTERNAL       = 'external'

    CHOICES = [
        (POOL,          'Clan Pool'),
        (MEMBER_LEDGER, 'Member Ledger'),
        (EXTERNAL,      'External'),
    ]


class EntryType:
    DEBIT  = 'debit'
    CREDIT = 'credit'

    CHOICES = [
        (DEBIT,  'Debit'),
        (CREDIT, 'Credit'),
    ]


class ContributionStatus:
    DUE       = 'due'
    PAID      = 'paid'
    LATE      = 'late'
    PENALIZED = 'penalized'
    WAIVED    = 'waived'

    CHOICES = [
        (DUE,       'Due'),
        (PAID,      'Paid'),
        (LATE,      'Late'),
        (PENALIZED, 'Penalized'),
        (WAIVED,    'Waived'),
    ]

    TRANSITIONS = {
        DUE:       [PAID, LATE],
        LATE:      [PAID, PENALIZED],
        PENALIZED: [PAID, WAIVED],
        WAIVED:    [],
        PAID:      [],
    }


class LoanStatus:
    REQUESTED    = 'requested'
    UNDER_REVIEW = 'under_review'
    APPROVED     = 'approved'
    DISBURSED    = 'disbursed'
    REPAID       = 'repaid'
    DEFAULTED    = 'defaulted'
    REJECTED     = 'rejected'

    CHOICES = [
        (REQUESTED,    'Requested'),
        (UNDER_REVIEW, 'Under Review'),
        (APPROVED,     'Approved'),
        (DISBURSED,    'Disbursed'),
        (REPAID,       'Repaid'),
        (DEFAULTED,    'Defaulted'),
        (REJECTED,     'Rejected'),
    ]

    TRANSITIONS = {
        REQUESTED:    [UNDER_REVIEW, REJECTED],
        UNDER_REVIEW: [APPROVED, REJECTED],
        APPROVED:     [DISBURSED],
        DISBURSED:    [REPAID, DEFAULTED],
        DEFAULTED:    [REPAID],
        REPAID:       [],
        REJECTED:     [],
    }


class FineStatus:
    UNPAID = 'unpaid'
    PAID   = 'paid'
    WAIVED = 'waived'

    CHOICES = [
        (UNPAID, 'Unpaid'),
        (PAID,   'Paid'),
        (WAIVED, 'Waived'),
    ]


class PaymentMethod:
    CASH         = 'cash'
    MOBILE_MONEY = 'mobile_money'
    BANK         = 'bank'

    CHOICES = [
        (CASH,         'Cash'),
        (MOBILE_MONEY, 'Mobile Money'),
        (BANK,         'Bank Transfer'),
    ]


class ExpenseCategory:
    EVENT     = 'event'
    WELFARE   = 'welfare'
    ADMIN     = 'admin'
    EMERGENCY = 'emergency'
    OTHER     = 'other'

    CHOICES = [
        (EVENT,     'Event'),
        (WELFARE,   'Welfare'),
        (ADMIN,     'Administration'),
        (EMERGENCY, 'Emergency'),
        (OTHER,     'Other'),
    ]