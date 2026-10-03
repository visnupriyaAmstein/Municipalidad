from django import forms
from .models import Tarea


class TareaForm(forms.ModelForm):
    class Meta:
        model = Tarea
        fields = ['titulo', 'area', 'ubicacion', 'descripcion', 'activa']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Mantención Plaza Sector Norte'}),
            'area': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Obras'}),
            'ubicacion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Av. del Mar 1200'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 4,
                                                 'placeholder': 'Describe la tarea que debe realizarse'}),
            'activa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_titulo(self):
        titulo = self.cleaned_data['titulo'].strip()
        if len(titulo) < 5:
            raise forms.ValidationError('El título debe tener al menos 5 caracteres.')
        return titulo
