from nicegui import ui
from components.headerAdmin import create_admin_screen
from components.share_data import *
from components.clear_table import clear_table


@ui.page('/myclassesAdmin')
def my_classesAdmin():
    create_admin_screen()
    with ui.column().classes('absolute-center items-center gap-4'):
        ui.label('Aquí se muestran tus clases por dar.')


