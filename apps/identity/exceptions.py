class MemberStatus:
    INVITED   = 'invited'
    PENDING   = 'pending'
    ACTIVE    = 'active'
    SUSPENDED = 'suspended'
    REMOVED   = 'removed'

    CHOICES = [
        (INVITED,   'Invited'),
        (PENDING,   'Pending'),
        (ACTIVE,    'Active'),
        (SUSPENDED, 'Suspended'),
        (REMOVED,   'Removed'),
    ]

    TRANSITIONS = {
        INVITED:   [PENDING, REMOVED],
        PENDING:   [ACTIVE, REMOVED],
        ACTIVE:    [SUSPENDED, REMOVED],
        SUSPENDED: [ACTIVE, REMOVED],
        REMOVED:   [],
    }


class Gender:
    MALE   = 'male'
    FEMALE = 'female'
    OTHER  = 'other'

    CHOICES = [
        (MALE,   'Male'),
        (FEMALE, 'Female'),
        (OTHER,  'Other'),
    ]