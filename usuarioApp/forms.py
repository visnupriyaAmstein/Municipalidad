from django import forms
from django.core.validators import FileExtensionValidator
from django.utils import timezone

from .models import Actividad

MAX_FOTO_MB = 5
EXTENSIONES_FOTO = ['jpg', 'jpeg', 'png', 'webp']   # formatos de foto permitidos


class ActividadForm(forms.ModelForm):
    class Meta:
        model = Actividad
        fields = ['descripcion', 'fecha', 'foto_antes', 'foto_despues']
        widgets = {
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control campo', 'rows': 4,
                'placeholder': 'Escribe lo que realizaste (mín. 10 caracteres)'}),
            # format ISO: si no, con el idioma es-cl el valor sale dd/mm/aaaa y el input date lo ignora
            'fecha': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'form-control campo'}),
            # visually-hidden (no d-none) para que el input siga siendo enfocable
            'foto_antes': forms.ClearableFileInput(attrs={'accept': '.jpg,.jpeg,.png,.webp', 'class': 'visually-hidden'}),
            'foto_despues': forms.ClearableFileInput(attrs={'accept': '.jpg,.jpeg,.png,.webp', 'class': 'visually-hidden'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fecha'].input_formats = ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']
        self.fields['fecha'].widget.attrs['max'] = timezone.localdate().isoformat()
        # Solo se aceptan JPG, PNG y WEBP (además Django verifica que el contenido sea una imagen real)
        for campo in ('foto_antes', 'foto_despues'):
            self.fields[campo].validators.append(FileExtensionValidator(EXTENSIONES_FOTO))

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
