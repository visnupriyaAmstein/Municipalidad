from django import forms
from django.contrib.auth.models import User

from usuarioApp.models import Actividad
from .models import Tarea


def funcionarios():
    """Usuarios a los que se les pueden asignar tareas (grupo Usuario, sin administradores)."""
    return (User.objects.filter(groups__name='Usuario', is_active=True, is_superuser=False)
            .exclude(groups__name='Administrador').order_by('first_name', 'last_name', 'username').distinct())


class FuncionarioChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return obj.get_full_name() or obj.username


class TareaForm(forms.ModelForm):
    asignados = FuncionarioChoiceField(
        queryset=User.objects.none(), required=True,
        widget=forms.CheckboxSelectMultiple,
        label='Asignar a',
        error_messages={'required': 'Asigna la tarea a al menos un funcionario.'},
    )

    class Meta:
        model = Tarea
        fields = ['titulo', 'area', 'ubicacion', 'descripcion', 'asignados', 'activa']
        labels = {'titulo': 'Título', 'area': 'Área', 'ubicacion': 'Ubicación', 'descripcion': 'Descripción'}
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Mantención Plaza Sector Norte'}),
            'area': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Obras'}),
            'ubicacion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Av. del Mar 1200'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 4,
                                                 'placeholder': 'Describe la tarea que debe realizarse'}),
            'activa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['asignados'].queryset = funcionarios()

    def clean_titulo(self):
        titulo = self.cleaned_data['titulo'].strip()
        if len(titulo) < 5:
            raise forms.ValidationError('El título debe tener al menos 5 caracteres.')
        return titulo


class EvaluacionForm(forms.Form):
    """El administrador aprueba o rechaza un reporte. Al rechazar debe explicar el motivo."""
    estado = forms.ChoiceField(choices=[(Actividad.Estado.APROBADA, 'Aprobar'),
                                        (Actividad.Estado.RECHAZADA, 'Rechazar')])
    observacion = forms.CharField(
        required=False, max_length=1000, label='Observación',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3,
                                     'placeholder': 'Comentario para el funcionario (obligatorio si rechazas)'}))

    def clean(self):
        datos = super().clean()
        observacion = (datos.get('observacion') or '').strip()
        datos['observacion'] = observacion
        if datos.get('estado') == Actividad.Estado.RECHAZADA and len(observacion) < 5:
            self.add_error('observacion', 'Explica al funcionario por qué se rechaza el reporte.')
        return datos
