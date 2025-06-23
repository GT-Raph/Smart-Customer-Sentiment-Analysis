from django import forms
from django.contrib.auth.forms import AuthenticationForm

class BranchLoginForm(AuthenticationForm):
    username = forms.CharField(label="Username")
    password = forms.CharField(widget=forms.PasswordInput)
    branch_code = forms.CharField(label="Branch Code", max_length=10)