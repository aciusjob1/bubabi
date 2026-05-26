from django import forms
from apps.identity.models import Clan, Announcement

class ClanSettingsForm(forms.ModelForm):
    class Meta:
        model = Clan
        fields = ['name', 'code', 'motto', 'logo', 'banner_image', 'primary_color', 'accent_color', 'sidebar_color', 'blur_intensity', 'currency', 'default_contribution', 'late_fine_amount', 'max_loan_amount', 'timezone', 'default_language', 'is_public', 'contact_email', 'contact_phone']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'primary_color': forms.TextInput(attrs={'type': 'color'}),
            'accent_color': forms.TextInput(attrs={'type': 'color'}),
            'sidebar_color': forms.TextInput(attrs={'type': 'color'}),
            'blur_intensity': forms.Select(choices=[
                ('0px', 'No Blur'),
                ('4px', 'Light (4px)'),
                ('8px', 'Medium (8px)'),
                ('16px', 'Strong (16px)'),
                ('24px', 'Heavy (24px)'),
            ]),
        }

class PaymentMethodsForm(forms.Form):
    enabled_methods = forms.MultipleChoiceField(
        choices=[('cash', 'Cash'), ('mobile_money', 'Mobile Money'), ('bank_transfer', 'Bank Transfer'), ('in_kind', 'In-Kind')],
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    default_method = forms.ChoiceField(
        choices=[('cash', 'Cash'), ('mobile_money', 'Mobile Money'), ('bank_transfer', 'Bank Transfer'), ('in_kind', 'In-Kind')],
        required=False
    )
    mobile_providers = forms.CharField(widget=forms.Textarea(attrs={'rows': 4, 'placeholder': 'One per line. Format: code|Name|Prefixes'}), required=False)
    banks = forms.CharField(widget=forms.Textarea(attrs={'rows': 4, 'placeholder': 'One per line. Format: code|Bank Name'}), required=False)

class TransitionMemberForm(forms.Form):
    new_status = forms.ChoiceField(choices=[('active', 'Active'), ('suspended', 'Suspended'), ('removed', 'Removed')])
    reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'Reason for status change...', 'class': 'form-input'})
    )

class InviteMemberForm(forms.Form):
    full_name = forms.CharField(max_length=200)
    email = forms.EmailField()
    phone = forms.CharField(max_length=20, required=False)
    gender = forms.ChoiceField(choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')])
    birth_date = forms.DateField(required=False)

class PersonForm(forms.ModelForm):
    class Meta:
        from apps.identity.models import Person
        model = Person
        fields = ['full_name', 'gender', 'birth_date', 'death_date', 'biography', 'profile_image']

class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ['title', 'content', 'category', 'is_pinned', 'expires_at']
