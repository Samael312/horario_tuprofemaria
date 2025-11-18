from nicegui import ui, app
import logging
from components.headerAdmin import create_admin_screen
from components.share_data import *
from components.clear_table import clear_table
from components.button_dur import make_add_hour_button
from components.h_selection import make_selection_handler
from components.delete_rows import delete_selected_rows_v2
from components.save_rgo import create_save_schedule_button

logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)

# =========================
# NEW STUDENT
# =========================
@ui.page('/Admhorario')
def adm_horario():
    user = app.storage.user.get("username", "Usuario")
    create_admin_screen()

    with ui.column().classes('w-full h-full p-4 md:p-8 items-center gap-6'):

        # 1. Selector de días
        with ui.card().classes('w-full max-w-3xl p-4'):
            ui.label('Selecciona los días').classes('text-lg font-bold')
            ui.separator()
            day_selector = ui.select(days_of_week, 
                                     label='Días', multiple=True, 
                                     value=[]).classes('w-auto min-w-[150px]')
        
        # 3. Selector de disponibilidad
        with ui.card().classes('w-full max-w-3xl p-4'):
            ui.label('Disponibilidad').classes('text-lg font-bold')
            ui.separator()
            avai_selector = ui.select(availability_options, label='Disponibilidad').classes('w-48')