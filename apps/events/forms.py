from django import forms
from apps.events.models import ClanEvent, MeetingMinutes

class EventForm(forms.ModelForm):
    class Meta:
        model = ClanEvent
        fields = ['title', 'event_type', 'description', 'scheduled_at', 'location', 'organized_by']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Event title', 'class': 'form-input'}),
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Describe the event...', 'class': 'form-input'}),
            'scheduled_at': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-input'},
                format='%Y-%m-%dT%H:%M'
            ),
            'location': forms.TextInput(attrs={'placeholder': 'Venue or location', 'class': 'form-input'}),
            'organized_by': forms.TextInput(attrs={'placeholder': 'Who is organizing?', 'class': 'form-input'}),
            'event_type': forms.Select(attrs={'class': 'form-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Format the initial date value for datetime-local input
        if self.instance and self.instance.pk and self.instance.scheduled_at:
            self.initial['scheduled_at'] = self.instance.scheduled_at.strftime('%Y-%m-%dT%H:%M')

class MeetingMinutesForm(forms.ModelForm):
    class Meta:
        model = MeetingMinutes
        fields = ['summary', 'decisions', 'action_items', 'next_meeting']
        widgets = {
            'summary': forms.Textarea(attrs={'rows': 6, 'placeholder': 'Summary of the meeting...', 'class': 'form-input'}),
            'decisions': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Key decisions made...', 'class': 'form-input'}),
            'action_items': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Action items and who is responsible...', 'class': 'form-input'}),
            'next_meeting': forms.DateTimeInput(
                attrs={'type': 'datetime-local', 'class': 'form-input'},
                format='%Y-%m-%dT%H:%M'
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.next_meeting:
            self.initial['next_meeting'] = self.instance.next_meeting.strftime('%Y-%m-%dT%H:%M')

