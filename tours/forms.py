import datetime

from django import forms

from .models import Enquiry

INTEREST_CHOICES = [
    ("Wildlife safari", "Wildlife safari"),
    ("Kilimanjaro climb", "Kilimanjaro climb"),
    ("Zanzibar beach", "Zanzibar beach"),
    ("Cultural tours", "Cultural tours"),
    ("Day trips", "Day trips"),
    ("Honeymoon", "Honeymoon"),
    ("Family holiday", "Family holiday"),
    ("Group joining", "Group joining"),
]

BUDGET_CHOICES = [
    ("", "Select a budget (optional)"),
    ("Budget / camping", "Budget / camping"),
    ("Mid-range lodges", "Mid-range lodges"),
    ("Luxury", "Luxury"),
    ("Not sure yet", "Not sure yet"),
]


class EnquiryForm(forms.ModelForm):
    # Spam trap: real people never see or fill this field.
    website = forms.CharField(required=False, widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}))
    interests_list = forms.MultipleChoiceField(
        choices=INTEREST_CHOICES, required=False, widget=forms.CheckboxSelectMultiple, label="I'm interested in"
    )
    budget = forms.ChoiceField(choices=BUDGET_CHOICES, required=False)

    class Meta:
        model = Enquiry
        fields = ["full_name", "email", "phone", "country", "travel_date", "adults", "children", "budget", "message"]
        labels = {"full_name": "Full name", "phone": "Phone / WhatsApp", "travel_date": "Travel date"}
        widgets = {
            "full_name": forms.TextInput(attrs={"autocomplete": "name", "placeholder": "Your name"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email", "placeholder": "you@example.com"}),
            "phone": forms.TextInput(attrs={"autocomplete": "tel", "placeholder": "+1 555 123 4567"}),
            "country": forms.TextInput(attrs={"autocomplete": "country-name", "placeholder": "Country"}),
            "travel_date": forms.DateInput(attrs={"type": "date"}),
            "adults": forms.NumberInput(attrs={"min": 1, "max": 60}),
            "children": forms.NumberInput(attrs={"min": 0, "max": 40}),
            "message": forms.Textarea(attrs={"rows": 4, "placeholder": "Tell us about your plans, questions or special requests"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["adults"].initial = 2
        self.fields["children"].initial = 0
        self.fields["adults"].required = False
        self.fields["children"].required = False
        self.fields["travel_date"].widget.attrs["min"] = datetime.date.today().isoformat()

    def clean_adults(self):
        return self.cleaned_data.get("adults") or 1

    def clean_children(self):
        return self.cleaned_data.get("children") or 0

    def clean_travel_date(self):
        d = self.cleaned_data.get("travel_date")
        if d and d < datetime.date.today():
            raise forms.ValidationError("Please choose a date in the future.")
        return d

    def is_spam(self):
        return bool(self.data.get("website"))

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.interests = ", ".join(self.cleaned_data.get("interests_list") or [])
        if commit:
            obj.save()
        return obj
