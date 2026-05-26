from django import forms
from apps.genealogy.models import Family, Relationship, PersonFamilyMembership
from apps.genealogy.constants import RelationType, FamilyRole
from apps.identity.models import Person


class FamilyForm(forms.ModelForm):
    class Meta:
        model  = Family
        fields = [
            'name', 'description',
            'founding_person', 'established_date'
        ]
        widgets = {
            'name':             forms.TextInput(attrs={
                'placeholder': 'Family house name'
            }),
            'description':      forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'Brief description'
            }),
            'established_date': forms.DateInput(attrs={
                'type': 'date'
            }),
        }


class RelationshipForm(forms.Form):
    from_person   = forms.ModelChoiceField(
        queryset=Person.objects.all(),
        label='Person'
    )
    relation_type = forms.ChoiceField(
        choices=RelationType.CHOICES
    )
    to_person     = forms.ModelChoiceField(
        queryset=Person.objects.all(),
        label='Related To'
    )
    is_biological = forms.BooleanField(required=False, initial=True)
    start_date    = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    notes         = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 2,
            'placeholder': 'Optional notes'
        })
    )