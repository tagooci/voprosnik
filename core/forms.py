from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.db import transaction

from .models import Profile
from .validators import avatar_validators


class BootstrapFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.HiddenInput):
                field.widget.attrs["class"] = "form-control"


class LoginForm(BootstrapFormMixin, AuthenticationForm):
    pass


class SignupForm(BootstrapFormMixin, UserCreationForm):
    email = forms.EmailField(label="Почта")
    first_name = forms.CharField(label="Имя", max_length=150)
    avatar = forms.ImageField(label="Аватар", required=False, validators=avatar_validators,
                              help_text="JPG, PNG или WebP, не больше 2 МБ.")

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("username", "email", "first_name", "password1", "password2", "avatar")

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            Profile.objects.create(user=user, avatar=self.cleaned_data.get("avatar") or "")
        return user


class ProfileForm(BootstrapFormMixin, forms.ModelForm):
    email = forms.EmailField(label="Почта")
    first_name = forms.CharField(label="Ник", max_length=150)
    avatar = forms.ImageField(label="Аватар", required=False, validators=avatar_validators,
                              help_text="JPG, PNG или WebP, не больше 2 МБ.")

    class Meta:
        model = get_user_model()
        fields = ("email", "first_name", "avatar")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        profile = Profile.objects.filter(user=self.instance).first()
        if profile:
            self.fields["avatar"].initial = profile.avatar

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save(update_fields=["email", "first_name"])
            profile, _ = Profile.objects.get_or_create(user=user)
            avatar = self.cleaned_data.get("avatar")
            if avatar is False:
                profile.avatar = ""
            elif avatar:
                profile.avatar = avatar
            profile.save()
        return user
