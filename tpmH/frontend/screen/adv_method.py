from nicegui import ui, app
from fastapi.responses import RedirectResponse
# Asegúrate de que estos imports existan en tu proyecto, si no, coméntalos para probar
from db.postgres_db import PostgresSession
from db.models import User

def create_ui(content_function=None):
    """Crea la interfaz base consistente con el login."""
    ui.dark_mode().set_value(False)

    # HEADER COMPACTO
    with ui.header().classes('h-16 px-6 bg-white border-b border-gray-200 items-center justify-between shadow-sm text-gray-800'):
        with ui.row().classes('items-center gap-2 cursor-pointer').on('click', lambda: ui.navigate.to('/')):
            ui.icon('school', color='pink-600', size='md')
            ui.label('TuProfeMaria').classes('text-xl font-black tracking-tight text-gray-800')

def adv_method():
    """Pantalla de selección de métodos de pago (Paso previo al registro)."""

    @ui.page('/method')
    def create_method_screen():
        
        # Renderizamos el marco base
        create_ui()

        def render_method_screen():
            
            # --- 1. ESTILOS CSS ---
            ui.add_head_html("""
            <style>
                .option-card { transition: all 0.2s ease; border: 2px solid transparent; }
                .option-card:hover { transform: translateY(-2px); box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); }
                .selected-card { border-color: #db2777 !important; background-color: #fdf2f8 !important; }
            </style>
            """)

            # --- 2. VARIABLES DE ESTADO ---
            chk_paypal = ui.checkbox('Paypal').classes('hidden')
            chk_binance = ui.checkbox('Binance').classes('hidden')
            chk_zelle = ui.checkbox('Zelle').classes('hidden')

            # --- 3. LÓGICA: GUARDAR EN MEMORIA (STORAGE) ---
            async def continue_to_signup():
                selected = []
                if chk_paypal.value: selected.append('Paypal')
                if chk_binance.value: selected.append('Binance')
                if chk_zelle.value: selected.append('Zelle')

                # VALIDACIÓN: Bloqueo si no hay selección
                if not selected:
                    ui.notify('⚠️ Selecciona al menos una opción para continuar', type='warning', position='top')
                    return 

                try:
                    # Guardamos en la memoria temporal del usuario
                    app.storage.user['temp_payment_methods'] = selected
                    
                    ui.notify('Selección guardada. Continuando al registro...', type='positive')
                    ui.timer(0.5, lambda: ui.navigate.to('/signup'))
                    
                except Exception as e:
                    ui.notify(f'Error al guardar en memoria: {str(e)}', type='negative')

            # --- 4. COMPONENTE VISUAL COMPACTO ---
            def render_option_card(title, icon, color_class, checkbox_ref):
                card = ui.card().classes('w-full p-0 border-2 border-gray-100 shadow-none option-card cursor-pointer rounded-xl')
                card.on('click', lambda: checkbox_ref.set_value(not checkbox_ref.value))

                with card:
                    with ui.row().classes('w-full items-center justify-between p-3'):
                        # Izquierda
                        with ui.row().classes('items-center gap-3'):
                            bg_color = color_class.replace("text", "bg").replace("600", "100").replace("500", "100")
                            with ui.element('div').classes(f'p-2 rounded-full {bg_color}'):
                                ui.icon(icon).classes(f'text-xl {color_class}')
                            
                            with ui.column().classes('gap-0'):
                                ui.label(title).classes('text-base font-bold text-gray-800 leading-tight')
                                ui.label('Disponible').classes('text-[10px] uppercase tracking-wide text-gray-400')
                        
                        # Derecha (Check)
                        indicator = ui.element('div').classes('rounded-full border-2 w-5 h-5 flex items-center justify-center transition-colors')
                        with indicator:
                             ui.icon('check', size='xs', color='white').bind_visibility_from(checkbox_ref, 'value')

                # Lógica manual de estilos
                def update_visuals():
                    if checkbox_ref.value:
                        card.classes('selected-card')
                        indicator.classes('border-pink-600 bg-pink-600')
                        indicator.classes(remove='border-gray-300')
                    else:
                        card.classes(remove='selected-card')
                        indicator.classes('border-gray-300')
                        indicator.classes(remove='border-pink-600 bg-pink-600')

                checkbox_ref.on_value_change(update_visuals)
                update_visuals()

            # --- 5. LAYOUT PRINCIPAL ---
            with ui.column().classes('w-full min-h-[calc(100vh-64px)] items-center justify-center bg-gray-50 p-4'):
                
                # Tarjeta Principal
                with ui.card().classes('w-full max-w-md p-0 shadow-xl rounded-2xl overflow-hidden bg-white'):
                    
                    # Header Decorativo (Solo Icono)
                    with ui.row().classes('w-full h-24 bg-gradient-to-r from-pink-600 to-rose-500 items-center justify-center relative'):
                        with ui.element('div').classes('bg-white/20 backdrop-blur-sm p-3 rounded-full shadow-lg'):
                            ui.icon('gpp_good', size='2.5em', color='white')
                    
                    # Cuerpo
                    with ui.column().classes('w-full p-6 pt-4 gap-4'):
                        
                        # --- AVISO IMPORTANTE (Movido aquí para que se vea bien) ---
                        with ui.row().classes('w-full bg-blue-50 border border-blue-100 rounded-lg p-3 gap-3 items-start'):
                            ui.icon('info', color='blue-600').classes('mt-0.5')
                            ui.label('Para concretar el pago e iniciar las clases, ponte en contacto con tu profesora. Conatcto en pestaña "Profesora".') \
                                .classes('text-xs text-blue-800 leading-tight flex-1 font-medium')

                        # Título
                        with ui.column().classes('w-full items-center text-center gap-1'):
                            ui.label('Métodos de Pago').classes('text-xl font-black text-gray-800')
                            ui.label('Selecciona tus opciones preferidas').classes('text-sm text-gray-500')

                        # Lista de Opciones
                        with ui.column().classes('w-full gap-2'):
                            render_option_card('PayPal', 'payment', 'text-blue-600', chk_paypal)
                            render_option_card('Binance', 'currency_bitcoin', 'text-yellow-500', chk_binance)
                            render_option_card('Zelle', 'attach_money', 'text-purple-600', chk_zelle)

                        # Botones
                        ui.button('Siguiente: Crear Cuenta', on_click=continue_to_signup) \
                            .props('unelevated icon-right=arrow_forward') \
                            .classes('w-full py-3 mt-2 bg-gray-900 text-white font-bold rounded-xl shadow-lg hover:bg-gray-800 transition-all text-base')
                        
                        ui.button('Cancelar', on_click=lambda: ui.navigate.to('/login')) \
                            .props('flat text-color=grey-5 dense') \
                            .classes('w-full text-xs')

        render_method_screen()

# EJECUCIÓN
if __name__ in {"__main__", "__mp_main__"}:
    adv_method()
    ui.run(storage_secret='clave_secreta_temporal')