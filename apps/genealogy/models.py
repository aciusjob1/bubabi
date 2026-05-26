from django.db import models
from apps.core.models import BaseModel
from apps.identity.models import Person, Clan, Member
from .constants import RelationType, FamilyRole


class Family(BaseModel):
    clan = models.ForeignKey(Clan, on_delete=models.PROTECT, related_name='families')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    founding_person = models.ForeignKey(Person, on_delete=models.SET_NULL, null=True, blank=True, related_name='founded_families')
    established_date = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = [('clan', 'name')]
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.clan.name})"


class PersonFamilyMembership(BaseModel):
    person = models.ForeignKey(Person, on_delete=models.PROTECT, related_name='family_memberships')
    family = models.ForeignKey(Family, on_delete=models.PROTECT, related_name='members')
    role_in_family = models.CharField(max_length=20, choices=FamilyRole.choices, default=FamilyRole.MEMBER)
    joined_family_at = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = [('person', 'family')]

    def __str__(self):
        return f"{self.person.full_name} -> {self.family.name} ({self.role_in_family})"


class Relationship(BaseModel):
    from_person = models.ForeignKey(Person, on_delete=models.PROTECT, related_name='relationships_from')
    to_person = models.ForeignKey(Person, on_delete=models.PROTECT, related_name='relationships_to')
    relation_type = models.CharField(max_length=20, choices=RelationType.choices)
    is_biological = models.BooleanField(default=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(Member, on_delete=models.PROTECT, related_name='recorded_relationships')

    class Meta:
        unique_together = [('from_person', 'to_person', 'relation_type')]
        ordering = ['relation_type']

    def __str__(self):
        return f"{self.from_person.full_name} -> [{self.relation_type}] -> {self.to_person.full_name}"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.from_person == self.to_person:
            raise ValidationError("A person cannot have a relationship with themselves.")
