from nicegui import ui, app
import logging
from components.headerAdmin import create_admin_screen
from db.sqlite_db import SQLiteSession
from db.models import User
from auth.sync_edit import sync_sqlite_to_postgres_edit
from components.h_selection import make_selection_handler
from components.clear_table import clear_table
from components.delete_rows import delete_selected_rows_v2
from components.share_data import pack_of_classes

logging.basicConfig(level=logging.DEBUG, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

@ui.page('/students_edit')
def students_edit():
    create_admin_screen()
    
    # Verificar sesión
    username_sess = app.storage.user.get("username")
    if not username_sess:
        ui.label("No hay usuario en sesión").classes('text-negative mt-4')
        return

    # --- Función para actualizar SOLO la memoria local (Python) ---
    def update_local_row(row_data):
        """
        Cuando el usuario cambia un dropdown, actualizamos table.rows en Python
        para que cuando pulse 'Guardar', se envíen los datos nuevos.
        """
        for row in table.rows:
            if row['Usuario'] == row_data['Usuario']:
                row.update(row_data) # Actualiza Role, Package o Status en memoria
                break
        # ui.notify(f"Dato actualizado en memoria: {row_data}", type='info') # Debug opcional

    with ui.row().classes('w-full items-center justify-center'):
        ui.label('Editar Lista de Estudiantes').classes('text-h4 mt-4 text-center')

    with ui.column().classes('w-full max-w-5xl mx-auto p-4 md:p-8 gap-3'):
        session = SQLiteSession()
        try:
            # 1. Obtener datos iniciales
            student_data = session.query(User).filter(User.role != 'admin').all()

            rows = [{
                'Usuario': s.username,
                'Name': s.name,
                'Surname': s.surname,
                'Role': getattr(s, 'role', 'client'),
                'Package': getattr(s, 'package', 'None'),
                'Status': getattr(s, 'status', 'Active')
            } for s in student_data]

            cols = [
                {'name': 'Usuario', 'label': 'Usuario', 'field': 'Usuario', 'align': 'left', 'sortable': True},
                {'name': 'Name', 'label': 'Nombre', 'field': 'Name', 'align': 'left', 'sortable': True},
                {'name': 'Surname', 'label': 'Apellido', 'field': 'Surname', 'align': 'left', 'sortable': True},
                {'name': 'Role', 'label': 'Role', 'field': 'Role', 'align': 'left'},
                {'name': 'Package', 'label': 'Package', 'field': 'Package', 'align': 'left'},
                {'name': 'Status', 'label': 'Status', 'field': 'Status', 'align': 'left'},
            ]

            # 2. Crear Tabla
            table = ui.table(
                columns=cols,
                rows=rows,
                row_key='Usuario',
                selection='multiple',
                pagination=10
            ).classes('w-full').props('dense bordered flat')

            # --- SLOTS ---
            
            # SLOT 1: ROLE
            table.add_slot('body-cell-Role', '''
                <q-td :props="props">
                    <q-select
                        v-model="props.row.Role"
                        :options="['admin', 'client']"
                        dense filled outlined emit-value map-options
                        @update:model-value="$parent.$emit('row-change', props.row)"
                        popup-content-class="bg-white text-black"
                    >
                        <template v-slot:selected-item="scope">
                            <q-chip dense :color="props.row.Role === 'admin' ? 'red-5' : 'blue-5'" text-color="white" icon="manage_accounts">
                                {{ props.row.Role }}
                            </q-chip>
                        </template>
                    </q-select>
                </q-td>
            ''')
            
            # SLOT 2: PACKAGE
            # Usamos f-string y {{ }} dobles para pasar la variable Python a Vue
            table.add_slot('body-cell-Package', f'''
                <q-td :props="props">
                    <q-select
                        v-model="props.row.Package"
                        :options="{pack_of_classes}" 
                        dense filled outlined emit-value map-options
                        @update:model-value="$parent.$emit('row-change', props.row)"
                    >
                        <template v-slot:selected-item="scope">
                            <div style="display:flex; align-items:center; gap:5px;">
                                <q-icon name="inventory_2" color="purple" v-if="props.row.Package !== 'None'" />
                                <span>{{{{ props.row.Package }}}}</span>
                            </div>
                        </template>
                    </q-select>
                </q-td>
            ''')

            # SLOT 3: STATUS
            table.add_slot('body-cell-Status', '''
                <q-td :props="props">
                    <q-select
                        v-model="props.row.Status"
                        :options="['Active', 'Inactive']"
                        dense filled outlined emit-value map-options
                        @update:model-value="$parent.$emit('row-change', props.row)"
                    >
                        <template v-slot:selected-item="scope">
                            <div style="display:flex; align-items:center; gap:6px;">
                                <div :style="{
                                    width: '10px', height: '10px', borderRadius: '50%',
                                    backgroundColor: props.row.Status === 'Active' ? '#21BA45' : '#C10015'
                                }"></div>
                                <span>{{ props.row.Status }}</span>
                            </div>
                        </template>
                    </q-select>
                </q-td>
            ''')

            # --- HANDLERS ---
            # Unificamos todos los cambios visuales en un solo evento 'row-change'
            # Esto actualiza la variable 'table.rows' de Python sin tocar la DB aún
            table.on('row-change', lambda e: update_local_row(e.args))

            # Manejo de selección
            selection_handler, selection_state = make_selection_handler(table, logger=logger)
            table.on('selection', selection_handler)

            # Botones auxiliares
            with ui.row().classes('gap-4 mt-2'):
                ui.button('Limpiar Tabla', 
                        on_click=lambda: table.set_rows([]), 
                        color='yellow').classes('mt-2 text-black')

                ui.button('Eliminar filas seleccionadas',
                        color='negative',
                        on_click=lambda: delete_selected_rows_v2(table, selection_state, id_column="Usuario")
                        ).classes('mt-2')

            # ------------------------------------------------------------
            # LOGICA DE GUARDADO (Corregida)
            # ------------------------------------------------------------
            def save_changes():
                session_save = SQLiteSession()
                try:
                    logger.info("Iniciando guardado masivo...")
                    
                    # 1. Obtenemos las filas ACTUALIZADAS desde Python (gracias a update_local_row)
                    current_rows = table.rows
                    current_usernames = [row['Usuario'] for row in current_rows if row.get('Usuario')]

                    # 2. ELIMINAR usuarios que ya no están en la tabla
                    users_to_delete = session_save.query(User).filter(
                        User.username.notin_(current_usernames),
                        User.role != 'superuser', 
                        User.role != 'admin' 
                    ).all()

                    for u in users_to_delete:
                        session_save.delete(u)

                    # 3. ACTUALIZAR O CREAR (Upsert)
                    for row in current_rows:
                        u_name = row.get('Usuario')
                        if not u_name: continue

                        user_db = session_save.query(User).filter(User.username == u_name).first()

                        if not user_db:
                            user_db = User(username=u_name)
                            session_save.add(user_db)
                        
                        # Aquí asignamos los valores que vinieron de la tabla (actualizados por update_local_row)
                        user_db.name = row.get('Name', '')
                        user_db.surname = row.get('Surname', '')
                        user_db.role = row.get('Role', 'client')
                        user_db.package = row.get('Package', 'None')
                        # user_db.status = row.get('Status', 'Active')

                    session_save.commit()
                    
                    
                    sync_sqlite_to_postgres_edit()
                    

                    ui.notify("Base de datos actualizada correctamente.", color='positive')
                    
                    # --- CORRECCIÓN DE NAVEGACIÓN ---
                    # Ahora está dentro del TRY, justo después del éxito
                    ui.timer(1.0, lambda: ui.navigate.to('/Students'))

                except Exception as e:
                    session_save.rollback()
                    logger.error(f"Error en save_changes: {e}", exc_info=True)
                    ui.notify(f"Error al guardar: {str(e)}", color='negative')
                finally:
                    session_save.close()

            with ui.column().classes('w-full items-center mt-6'):
                ui.button("Guardar Cambios", on_click=save_changes, color='positive').classes('w-64')

        except Exception as e:
            ui.label(f"Error cargando página: {e}")
        finally:
            session.close()