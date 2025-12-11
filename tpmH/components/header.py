from nicegui import ui, app
from db.postgres_db import PostgresSession
from db.models import SchedulePref, AsignedClasses

def create_main_screen():
    
    # 1. Obtener usuario actual
    username = app.storage.user.get("username")
    
    # 2. Verificar existencia de datos en la BD
    show_full_menu = False
    
    if username:
        session = PostgresSession()
        try:
            # Verificamos si existe al menos un registro en SchedulePref
            has_pref = session.query(SchedulePref).filter(SchedulePref.username == username).first()
            # Verificamos si existe al menos un registro en AsignedClasses
            has_classes = session.query(AsignedClasses).filter(AsignedClasses.username == username).first()
            
            # Si tiene cualquiera de los dos, mostramos el menú completo
            if has_pref or has_classes:
                show_full_menu = True
        except Exception as e:
            print(f"Error verificando menú: {e}")
        finally:
            session.close()

    def logout():
        app.storage.user.clear()
        ui.navigate.to('/login')

    # Helper para botones (definido fuera para usarlo o no según condición)
    def nav_btn(label, route, icon):
        ui.button(label, icon=icon, on_click=lambda: ui.navigate.to(route)) \
            .props('flat round color=white') \
            .classes('text-white font-medium hover:bg-white/20 transition-all duration-300 rounded-lg px-3')

    # --- RENDERIZADO DEL HEADER ---
    with ui.header().classes('px-6 py-3 items-center justify-between bg-gradient-to-r from-pink-600 to-pink-500 shadow-md'):
        
        # A. Logo y Título (Siempre visible)
        with ui.row().classes('items-center gap-2 cursor-pointer').on('click', lambda: ui.navigate.to('/mainscreen')):
            ui.icon('school', size='md', color='white')
            ui.label('TuProfeMaria').classes('text-white text-xl font-bold tracking-wide')

        # B. Menú de Navegación (Condicional)
        with ui.row().classes('gap-1 items-center'):
            
            if show_full_menu:
                # Si hay datos, mostramos TODO el menú
                #nav_btn('Inicio', '/mainscreen', 'home')
                nav_btn('Horario', '/ScheduleMaker', 'edit_calendar')
                nav_btn('Mis Clases', '/myclasses', 'school')
                nav_btn('Mis Tareas', '/StudentHomework', 'assignment')
                nav_btn('Materiales', '/materials', 'menu_book')
                nav_btn('Profesora', '/teacher', 'people')
                
                # Separador
                ui.element('div').classes('w-[1px] h-6 bg-pink-300 mx-2')

                # Perfil
                nav_btn('Perfil', '/profile', 'person')
            
            # Botón Logout (Siempre visible por usabilidad, para no atrapar al usuario)
            ui.button(on_click=logout, icon='logout') \
                .props('outline color=white') \
                .tooltip('Cerrar Sesión') \
                .classes('ml-2 hover:bg-red-500 hover:border-red-500 transition-colors')