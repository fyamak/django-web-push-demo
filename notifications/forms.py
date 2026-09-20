from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django import forms


class SignUpForm(UserCreationForm):
    email = forms.EmailField(
        required=False,
        label="E-posta",
        help_text="İsteğe bağlı. Yönetim ekranında kullanıcıyı ayırt etmek için kullanılabilir.",
    )

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("username", "email")
        labels = {
            "username": "Kullanıcı adı",
        }
