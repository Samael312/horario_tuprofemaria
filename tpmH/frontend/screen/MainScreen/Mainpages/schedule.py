from nicegui import ui
from components.header import create_main_screen
from components.share_data import *
from components.clear_table import clear_table


@ui.page('/ScheduleMaker')
def scheduleMaker():
    create_main_screen()
    with ui.column().classes('absolute-center items-center gap-4'):
        ui.label('Creador de horarios')


