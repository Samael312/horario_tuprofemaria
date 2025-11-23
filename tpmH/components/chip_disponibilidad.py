# chips.py
# Módulo para generar chips HTML de disponibilidad en NiceGUI/Quasar

def make_chip(estado, h_ini=None, h_fin=None):
    """
    Devuelve un chip HTML según el estado de disponibilidad.
    Opcionalmente incluye el intervalo horario.
    """

    # Determinar color e ícono
    if estado and estado.lower() == "ocupado":
        chip = (
            "<q-chip dense color='red' text-color='white' class='q-ma-xs'>"
            "<q-icon name='close' size='xs' class='q-mr-xs'></q-icon>"
            "Ocupado"
        )
    else:
        chip = (
            "<q-chip dense color='green' text-color='white' class='q-ma-xs'>"
            "<q-icon name='check' size='xs' class='q-mr-xs'></q-icon>"
            "Libre"
        )

    # Agregar el rango si se suministra
    if h_ini and h_fin:
        chip += f" ({h_ini}-{h_fin})"

    chip += "</q-chip>"
    return chip
