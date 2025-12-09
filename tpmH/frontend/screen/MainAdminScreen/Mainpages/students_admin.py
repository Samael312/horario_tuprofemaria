from nicegui import ui, app
from db.postgres_db import PostgresSession
from db.sqlite_db import BackupSession
from db.models import User, AsignedClasses
from components.headerAdmin import create_admin_screen
from components.share_data import PACKAGE_LIMITS
import logging

# Configuración de logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Nota: PRECIO_POR_CLASE se ha eliminado como constante global 
# porque ahora depende de la columna user.price de la base de datos.

@ui.page('/Students')
def students():
    # --- 1. ESTILOS Y HEADER ---
    ui.query('body').style('background-color: #F8FAFC; font-family: "Inter", sans-serif;')
    create_admin_screen()
    
    if not app.storage.user.get('authenticated', False):
        ui.navigate.to('/login')
        return

    current_username = app.storage.user.get("username")
    
    # Declaramos variables para el ámbito (scope)
    table = None
    search_input = None
    rows = [] # Lista maestra de filas

    # --- HELPER PARA OBTENER DATOS (Refactorizado) ---
    def get_data_rows():
        session = PostgresSession()
        new_rows = []
        try:
            all_users = session.query(User).all()
            display_users = [u for u in all_users if u.username != current_username]
            
            for u in display_users:
                # --- MODIFICADO: Datos tomados DIRECTAMENTE de la tabla User ---
                # Total de clases históricas (actualizado al completar clase)
                total_cnt = getattr(u, 'total_classes', 0)
                if total_cnt is None: total_cnt = 0
                
                # Progreso del paquete actual (actualizado al completar clase)
                pkg_progress = getattr(u, 'class_count', '-')
                if not pkg_progress: pkg_progress = '-'

                # --- LÓGICA DE PAGOS ---
                pay_info = u.payment_info if u.payment_info else {}
                pkg_limit = PACKAGE_LIMITS.get(u.package, 0)
                
                raw_paquete = pay_info.get('Clases_paquete', f"0/{pkg_limit}")
                try:
                    curr, db_limit = map(int, raw_paquete.split('/'))
                    final_limit = pkg_limit if (db_limit == 0 and pkg_limit > 0) else db_limit
                    val_paquete_pagado = f"{curr}/{final_limit}"
                except:
                    val_paquete_pagado = f"0/{pkg_limit}"

                # --- LÓGICA CON PRECIO INDIVIDUAL ---
                historico_pagadas = pay_info.get('Clases_totales', 0)
                
                # Obtenemos el precio del usuario, por defecto 10 si es None
                user_price = u.price if hasattr(u, 'price') and u.price is not None else 10
                
                # Multiplicamos clases históricas por el precio individual del usuario
                val_total_dinero = historico_pagadas * user_price

                new_rows.append({
                    'id': u.id,
                    'avatar': f'https://ui-avatars.com/api/?name={u.name}+{u.surname}&background=random',
                    'username': u.username,
                    'fullname': f"{u.name} {u.surname}",
                    'email': u.email or 'Sin correo',
                    'goal': u.goal or 'Sin objetivo',
                    'role': u.role,
                    'package': u.package or 'Sin Plan',
                    'time_zone': u.time_zone or 'UTC',
                    'status': u.status,
                    'total_classes': total_cnt,      # <-- Desde User.total_classes
                    'current_progress': pkg_progress, # <-- Desde User.class_count
                    'paid_package': val_paquete_pagado,
                    'price': user_price,
                    'total_paid': val_total_dinero
                })
            return new_rows
        except Exception as e:
            logger.error(f"Error fetching rows: {e}")
            return []
        finally:
            session.close()

    # --- 2. LÓGICA DE ACTUALIZACIÓN (BACKEND + FRONTEND) ---
    async def update_payment_counter(user_id, delta):
        session = PostgresSession()
        try:
            user = session.query(User).filter(User.id == user_id).first()
            if user:
                payment_data = dict(user.payment_info) if user.payment_info else {}
                real_limit = PACKAGE_LIMITS.get(user.package, 0)
                current_str = payment_data.get('Clases_paquete', f"0/{real_limit}")
                
                try:
                    curr_paid, _ = map(int, current_str.split('/'))
                except:
                    curr_paid = 0
                
                new_paid = max(0, curr_paid + delta)
                payment_data['Clases_paquete'] = f"{new_paid}/{real_limit}"

                current_total = payment_data.get('Clases_totales', 0)
                new_total_historico = max(0, current_total + delta)
                payment_data['Clases_totales'] = new_total_historico

                user.payment_info = payment_data
                session.commit()

                # Backup SQLite
                try:
                    bk_sess = BackupSession()
                    bk_user = bk_sess.query(User).filter(User.username == user.username).first()
                    if bk_user:
                        bk_user.payment_info = payment_data
                        bk_sess.commit()
                    bk_sess.close()
                except: pass

                # Calculamos el dinero total para la notificación usando el precio del usuario
                user_price = user.price if hasattr(user, 'price') and user.price is not None else 10
                money = new_total_historico * user_price
                
                ui.notify(f'Actualizado: {new_paid}/{real_limit} (Total: ${money})', type='positive')
                
                # --- SOLUCIÓN: ACTUALIZAR FRONTEND ---
                nonlocal rows
                rows = get_data_rows() # 1. Traer datos frescos de DB
                
                # 2. Respetar el filtro de búsqueda si existe
                query = search_input.value.lower() if search_input else ""
                if query:
                    table.rows = [r for r in rows if query in r['fullname'].lower() or query in r['username'].lower()]
                else:
                    table.rows = rows
                
                # 3. Forzar actualización visual de la tabla
                table.update()

        except Exception as e:
            logger.error(f"Error actualizando pagos: {e}")
            ui.notify("Error actualizando pagos", type='negative')
        finally:
            session.close()

    # --- 3. CARGA DE MÉTRICAS (Simplificada) ---
    session = PostgresSession()
    try:
        all_users = session.query(User).all()
        total_users = len(all_users)
        total_students = sum(1 for u in all_users if u.role == 'client')
        active_users = sum(1 for u in all_users if u.status == 'Active')
    except:
        total_users = 0; total_students = 0; active_users = 0
    finally:
        session.close()

    # Cargar filas iniciales usando el helper
    rows = get_data_rows()

    # --- 4. COMPONENTES VISUALES ---
    
    def render_stat_card(title, value, icon, color):
        with ui.card().classes(f'w-full p-4 rounded-2xl border-l-4 border-{color}-500 shadow-sm bg-white items-center flex-row justify-between'):
            with ui.column().classes('gap-1'):
                ui.label(title).classes('text-xs font-bold text-gray-400 uppercase tracking-wider')
                ui.label(str(value)).classes('text-3xl font-black text-gray-800 leading-none')
            with ui.element('div').classes(f'p-3 bg-{color}-50 rounded-full'):
                ui.icon(icon, color=f'{color}-600', size='md')

    with ui.column().classes('w-full max-w-7xl mx-auto p-4 md:p-8 gap-8'):
        
        # Header
        with ui.row().classes('w-full justify-between items-center'):
            with ui.row().classes('items-center gap-3'):
                with ui.element('div').classes('p-2 bg-pink-100 rounded-xl'):
                    ui.icon('school', size='lg', color='pink-600')
                with ui.column().classes('gap-0'):
                    ui.label('Directorio de Usuarios').classes('text-2xl font-bold text-slate-800')
                    ui.label('Administra el acceso y datos de tus estudiantes').classes('text-sm text-slate-500')

        # Metrics
        with ui.grid().classes('w-full grid-cols-1 md:grid-cols-3 gap-4'):
            render_stat_card('Total Registrados', total_users, 'group', 'slate')
            render_stat_card('Estudiantes', total_students, 'school', 'pink')
            render_stat_card('Usuarios Activos', active_users, 'verified_user', 'green')

        # Tabla
        with ui.card().classes('w-full p-0 rounded-2xl shadow-lg border border-slate-100 overflow-hidden'):
            with ui.row().classes('w-full bg-slate-50 p-4 border-b border-slate-200 justify-between items-center'):
                ui.label(f'{len(rows)} Usuarios encontrados').classes('font-bold text-slate-600 text-sm')
                search_input = ui.input(placeholder='Buscar estudiante...').props('outlined dense rounded bg-white') \
                    .classes('w-full md:w-64').on('keydown.enter', lambda: None)
                search_input.add_slot('prepend', '<q-icon name="search" />')

            columns = [
                {'name': 'avatar', 'label': '', 'field': 'avatar', 'align': 'center', 'classes': 'w-12'},
                {'name': 'fullname', 'label': 'ESTUDIANTE', 'field': 'fullname', 'align': 'left', 'sortable': True, 'headerClasses': 'text-slate-500 font-bold text-xs uppercase'},
                {'name': 'info', 'label': 'CONTACTO', 'field': 'email', 'align': 'left', 'headerClasses': 'text-slate-500 font-bold text-xs uppercase'},
                {'name': 'plan', 'label': 'PLAN', 'field': 'package', 'align': 'left', 'sortable': True, 'headerClasses': 'text-slate-500 font-bold text-xs uppercase'},
                {'name': 'goal', 'label': 'OBJETIVO', 'field': 'goal', 'align': 'left', 'sortable': True, 'headerClasses': 'text-slate-500 font-bold text-xs uppercase'},
                
                # --- NUEVA COLUMNA PRECIO ---
                {'name': 'price', 'label': 'PRECIO', 'field': 'price', 'align': 'center', 'sortable': True, 'headerClasses': 'text-slate-500 font-bold text-xs uppercase'},
                
                {'name': 'activity', 'label': 'CLASES', 'field': 'total_classes', 'align': 'center', 'headerClasses': 'text-slate-500 font-bold text-xs uppercase'},
                {'name': 'paid_package', 'label': 'PAQUETE PAGADO', 'field': 'paid_package', 'align': 'center', 'headerClasses': 'text-slate-500 font-bold text-xs uppercase'},
                {'name': 'total_paid', 'label': 'TOTAL PAGADO', 'field': 'total_paid', 'align': 'center', 'sortable': True, 'headerClasses': 'text-slate-500 font-bold text-xs uppercase'},
                {'name': 'status', 'label': 'ESTADO', 'field': 'status', 'align': 'center', 'sortable': True, 'headerClasses': 'text-slate-500 font-bold text-xs uppercase'},
            ]

            table = ui.table(columns=columns, rows=rows, pagination={'rowsPerPage': 8}).classes('w-full').props('flat')

            # --- SLOTS ---
            table.add_slot('body-cell-avatar', '<q-td key="avatar" :props="props"><q-avatar size="32px"><img :src="props.row.avatar"></q-avatar></q-td>')
            
            table.add_slot('body-cell-fullname', '''
                <q-td key="fullname" :props="props">
                    <div class="flex column">
                        <span class="text-weight-bold text-slate-800">{{ props.row.fullname }}</span>
                        <span class="text-xs text-slate-400">@{{ props.row.username }}</span>
                    </div>
                </q-td>
            ''')
            
            table.add_slot('body-cell-info', '<q-td key="info" :props="props"><div class="flex items-center gap-1 text-slate-600"><q-icon name="mail" size="xs" /><span>{{ props.row.email }}</span></div></q-td>')
            
            table.add_slot('body-cell-plan', '''
                <q-td key="plan" :props="props">
                    <div class="flex column gap-1">
                        <q-badge :color="props.row.package ? 'blue-1' : 'grey-2'" :text-color="props.row.package ? 'blue-8' : 'grey-6'" class="font-bold">{{ props.row.package || 'SIN PLAN' }}</q-badge>
                        <div class="flex items-center gap-1 text-xs text-slate-400"><q-icon name="public" /><span>{{ props.row.time_zone }}</span></div>
                    </div>
                </q-td>
            ''')

            table.add_slot('body-cell-goal', '''
                <q-td key="goal" :props="props">
                    <div class="flex column gap-1">
                        <q-badge :color="props.row.goal ? 'orange-1' : 'grey-2'" :text-color="props.row.goal ? 'orange-8' : 'grey-6'" class="font-bold">{{ props.row.goal || 'SIN OBJETIVO' }}</q-badge>
                    </div>
                </q-td>
            ''')

            # --- SLOT VISUAL PARA PRECIO INDIVIDUAL ---
            table.add_slot('body-cell-price', '''
                <q-td key="price" :props="props">
                    <div class="flex justify-center">
                        <q-badge color="grey-2" text-color="grey-8" class="font-bold">
                            $ {{ props.row.price }}
                        </q-badge>
                    </div>
                </q-td>
            ''')

            table.add_slot('body-cell-activity', '''
                <q-td key="activity" :props="props">
                    <div class="flex column items-center gap-1">
                        <q-badge color="amber-50" text-color="amber-900" class="font-bold" rounded>Realizadas: #{{ props.row.total_classes }}</q-badge>
                        <span class="text-xs text-slate-400">Prog: {{ props.row.current_progress }}</span>
                    </div>
                </q-td>
            ''')

            # --- SLOT CLAVE: PAQUETE PAGADO ---
            table.add_slot('body-cell-paid_package', r'''
                <q-td key="paid_package" :props="props">
                    <div class="flex items-center justify-center gap-2">
                        <q-btn icon="remove" size="xs" round flat color="red" @click="$parent.$emit('update_pay', props.row.id, -1)" />
                        <q-badge color="green-50" text-color="green-800" class="text-sm font-bold q-px-sm" rounded>
                            {{ props.row.paid_package }}
                        </q-badge>
                        <q-btn icon="add" size="xs" round flat color="green" @click="$parent.$emit('update_pay', props.row.id, 1)" />
                    </div>
                </q-td>
            ''')
            table.on('update_pay', lambda e: update_payment_counter(e.args[0], e.args[1]))

            table.add_slot('body-cell-total_paid', '''
                <q-td key="total_paid" :props="props">
                    <div class="flex justify-center">
                        <q-badge outline color="purple" class="font-bold text-sm">
                            $ {{ props.row.total_paid }}
                        </q-badge>
                    </div>
                </q-td>
            ''')

            table.add_slot('body-cell-status', '<q-td key="status" :props="props"><div class="flex justify-center"><q-badge rounded :color="props.row.status === \'Active\' ? \'green\' : \'red\'">{{ props.row.status }}</q-badge></div></q-td>')

            # Filtro
            def filter_table():
                query = search_input.value.lower()
                if not query:
                    table.rows = rows
                    return
                filtered = [r for r in rows if query in r['fullname'].lower() or query in r['username'].lower()]
                table.rows = filtered
                table.update()
            search_input.on('update:model-value', filter_table)

    # FAB
    with ui.page_sticky(position='bottom-right', x_offset=30, y_offset=30):
        with ui.fab(icon='edit', color='pink-600', direction="left").props('glossy push'):
            ui.fab_action(label='Edición Masiva', icon='table_view', color='slate', on_click=lambda: ui.navigate.to('/students_edit'))

if __name__ in {"__main__", "__mp_main__"}:
    ui.run()