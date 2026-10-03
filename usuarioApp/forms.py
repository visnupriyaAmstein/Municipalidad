from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils import timezone

from .models import Actividad

MAX_FOTO_MB = 5


class ActividadForm(forms.ModelForm):
    class Meta:
        model = Actividad
        fields = ['descripcion', 'fecha', 'foto_antes', 'foto_despues']
        widgets = {
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control campo-verde', 'rows': 4,
                'placeholder': 'Escribe lo que realizaste (mín. 10 caracteres)'}),
            # format ISO: si no, con el idioma es-cl el valor sale dd/mm/aaaa y el input date lo ignora
            'fecha': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'form-control campo-verde'}),
            # visually-hidden (no d-none) para que el input siga siendo enfocable
            'foto_antes': forms.ClearableFileInput(attrs={'accept': 'image/*', 'class': 'visually-hidden'}),
            'foto_despues': forms.ClearableFileInput(attrs={'accept': 'image/*', 'class': 'visually-hidden'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fecha'].input_formats = ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']
        self.fields['fecha'].widget.attrs['max'] = timezone.localdate().isoformat()

    def clean_descripcion(self):
        texto = self.cleaned_data['descripcion'].strip()
        if len(texto) < 10:
            raise forms.ValidationError('Describe el avance con al menos 10 caracteres.')
        return texto

    def clean_fecha(self):
        fecha = self.cleaned_data['fecha']
        if fecha > timezone.localdate():
            raise forms.ValidationError('La fecha no puede ser futura.')
        return fecha

    def _validar_foto(self, campo):
        foto = self.cleaned_data.get(campo)
        if foto and foto.size > MAX_FOTO_MB * 1024 * 1024:
            raise forms.ValidationError(f'La imagen no puede superar los {MAX_FOTO_MB} MB.')
        return foto

    def clean_foto_antes(self):
        return self._validar_foto('foto_antes')

    def clean_foto_despues(self):
        return self._validar_foto('foto_despues')


class RegistroForm(UserCreationForm):
    first_name = forms.CharField(
        label='Nombre', max_length=150, required=True
    )
    last_name = forms.CharField(
        label='Apellido', max_length=150, required=True
    )
    email = forms.EmailField(
        label='Correo electrónico', required=True
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']
        labels = {'username': 'Nombre de usuario'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
        self.fields['password1'].label = 'Contraseña'
        self.fields['password2'].label = 'Repetir contraseña'

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Ya existe una cuenta con este correo.')
        return email

    def clean_first_name(self):
        return self.cleaned_data['first_name'].strip().title()

    def clean_last_name(self):
        return self.cleaned_data['last_name'].strip().title()