from django.db import models


class RelationType(models.TextChoices):
    PARENT = 'parent', 'Parent'
    FATHER = 'father', 'Father'
    MOTHER = 'mother', 'Mother'
    CHILD = 'child', 'Child'
    SPOUSE = 'spouse', 'Spouse'
    SIBLING = 'sibling', 'Sibling'
    GRANDPARENT = 'grandparent', 'Grandparent'
    GRANDCHILD = 'grandchild', 'Grandchild'
    AUNT_UNCLE = 'aunt_uncle', 'Aunt/Uncle'
    NEPHEW_NIECE = 'nephew_niece', 'Nephew/Niece'
    COUSIN = 'cousin', 'Cousin'
    IN_LAW = 'in_law', 'In-Law'


class FamilyRole(models.TextChoices):
    FOUNDER = 'founder', 'Founder'
    ELDER = 'elder', 'Elder'
    PARENT = 'parent', 'Parent'
    CHILD = 'child', 'Child'
    SPOUSE = 'spouse', 'Spouse'
    MEMBER = 'member', 'Member'
    OTHER = 'other', 'Other'
