from django import forms
from apps.governance.models import Vote, MemberRole, Role
from django.utils import timezone


class VoteForm(forms.ModelForm):
    class Meta:
        model  = Vote
        fields = [
            'topic', 'description',
            'quorum_percent', 'opens_at', 'closes_at'
        ]
        widgets = {
            'topic':       forms.TextInput(attrs={
                'placeholder': 'What are we voting on?'
            }),
            'description': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Explain the vote in detail'
            }),
            'opens_at':    forms.DateTimeInput(attrs={
                'type': 'datetime-local'
            }),
            'closes_at':   forms.DateTimeInput(attrs={
                'type': 'datetime-local'
            }),
        }


class AssignRoleForm(forms.Form):
    member_id = forms.UUIDField(widget=forms.HiddenInput())
    role      = forms.ModelChoiceField(queryset=Role.objects.none())

    def __init__(self, *args, clan=None, **kwargs):
        super().__init__(*args, **kwargs)
        if clan:
            self.fields['role'].queryset = Role.objects.filter(clan=clan)