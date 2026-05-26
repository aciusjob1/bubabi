class EventType:
    MEETING   = 'meeting'
    DEADLINE  = 'deadline'
    CEREMONY  = 'ceremony'
    EMERGENCY = 'emergency'

    CHOICES = [
        (MEETING,   'Meeting'),
        (DEADLINE,  'Deadline'),
        (CEREMONY,  'Ceremony'),
        (EMERGENCY, 'Emergency'),
    ]


class ParticipationStatus:
    INVITED   = 'invited'
    CONFIRMED = 'confirmed'
    ATTENDED  = 'attended'
    ABSENT    = 'absent'
    EXCUSED   = 'excused'

    CHOICES = [
        (INVITED,   'Invited'),
        (CONFIRMED, 'Confirmed'),
        (ATTENDED,  'Attended'),
        (ABSENT,    'Absent'),
        (EXCUSED,   'Excused'),
    ]