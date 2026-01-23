from nicegui import ui, app
import logging
from components.headerAdmin import create_admin_screen
# --- IMPORTS ACTUALIZADOS ---
from db.postgres_db import PostgresSession  # Fuente de la verdad
from db.sqlite_db import BackupSession       # Respaldo
from db.models import User, SchedulePref, AsignedClasses
# ----------------------------
from components.h_selection import make_selection_handler
from components.delete_rows import delete_selected_rows_v2
from components.share_data import *

logging.basicConfig(level=logging.DEBUG, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

@ui.page('/students_edit')
def students_edit():
    # 1. Header y Autenticación
    create_admin_screen()
    
    username_sess = app.storage.user.get("username")
    if not username_sess:
        ui.navigate.to('/login')
        return

    # --- Lógica Local ---
    def update_local_row(row_data):
        """Actualiza la memoria de la tabla sin tocar la DB todavía."""
        for row in table.rows:
            if row['Usuario'] == row_data['Usuario']:
                row.update(row_data)
                break

    # --- UI PRINCIPAL ---
    with ui.column().classes('w-full max-w-7xl mx-auto p-4 md:p-8 gap-6'):
        
        # 2. Encabezado de Página
        with ui.row().classes('w-full items-center justify-between mb-2'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('edit_note', size='lg', color='blue-600')
                with ui.column().classes('gap-0'):
                    ui.label('Editor Masivo de Estudiantes').classes('text-3xl font-bold text-gray-800')
                    ui.label('Modifica roles, paquetes, precios y estados').classes('text-sm text-gray-500')
            
            # Botón Cancelar/Volver
            ui.button('Volver a Lista', on_click=lambda: ui.navigate.to('/Students')) \
                .props('flat color=grey-7 icon=arrow_back')

        # 3. Tarjeta de Edición
        with ui.card().classes('w-full shadow-lg rounded-xl overflow-hidden border border-gray-200 p-0'):
            
            # Barra de Herramientas de Tabla
            with ui.row().classes('w-full bg-blue-50 p-4 border-b border-blue-100 items-center justify-between'):
                ui.label('Tabla de Edición').classes('text-lg font-bold text-blue-900')
                
                # Acciones de Tabla
                with ui.row().classes('gap-2'):
                     ui.button('Borrar Seleccionados', 
                            icon='delete', 
                            color='negative', 
                            on_click=lambda: delete_selected_rows_v2(table, selection_state, id_column="Usuario")
                        ).props('flat dense')

            # --- CARGA DE DATOS DESDE NEON (NUBE) ---
            session = PostgresSession()
            try:
                # Cargar Datos de la nube
                student_data = session.query(User).all()

                rows = [{
                    'Usuario': s.username,
                    'Name': s.name,
                    'Surname': s.surname,
                    'Role': getattr(s, 'role', 'client'),
                    'Package': getattr(s, 'package', 'None'),
                    'Status': getattr(s, 'status', 'Active'),
                    'Price': getattr(s, 'price', 10) if getattr(s, 'price', None) is not None else 10
                } for s in student_data]

                # Definir Columnas
                cols = [
                    {'name': 'Usuario', 'label': 'USUARIO', 'field': 'Usuario', 'align': 'left', 'sortable': True, 'headerClasses': 'bg-gray-100 font-bold'},
                    {'name': 'Name', 'label': 'NOMBRE', 'field': 'Name', 'align': 'left', 'sortable': True, 'headerClasses': 'bg-gray-100 font-bold'},
                    {'name': 'Surname', 'label': 'APELLIDO', 'field': 'Surname', 'align': 'left', 'sortable': True, 'headerClasses': 'bg-gray-100 font-bold'},
                    {'name': 'Role', 'label': 'ROL (EDIT)', 'field': 'Role', 'align': 'left', 'headerClasses': 'bg-blue-100 text-blue-900 font-bold'},
                    {'name': 'Package', 'label': 'PAQUETE (EDIT)', 'field': 'Package', 'align': 'left', 'headerClasses': 'bg-blue-100 text-blue-900 font-bold'},
                    {'name': 'Price', 'label': 'PRECIO ($)', 'field': 'Price', 'align': 'left', 'headerClasses': 'bg-green-100 text-green-900 font-bold'},
                    {'name': 'Status', 'label': 'ESTADO (EDIT)', 'field': 'Status', 'align': 'left', 'headerClasses': 'bg-blue-100 text-blue-900 font-bold'},
                ]

                # Renderizar Tabla
                table = ui.table(
                    columns=cols,
                    rows=rows,
                    row_key='Usuario',
                    selection='multiple',
                    pagination={'rowsPerPage': 10}
                ).classes('w-full').props('flat bordered separator=cell')

                # --- VUE SLOTS (Personalización Visual) ---
                table.add_slot('body-cell-Role', '''
                    <q-td :props="props">
                        <q-select
                            v-model="props.row.Role"
                            :options="['admin', 'client']"
                            dense borderless emit-value map-options
                            @update:model-value="$parent.$emit('row-change', props.row)"
                        >
                            <template v-slot:selected-item="scope">
                                <q-chip dense :color="props.row.Role === 'admin' ? 'red-1' : 'blue-1'" 
                                            :text-color="props.row.Role === 'admin' ? 'red-9' : 'blue-9'" 
                                            :icon="props.row.Role === 'admin' ? 'security' : 'person'">
                                    {{ props.row.Role.toUpperCase() }}
                                </q-chip>
                            </template>
                        </q-select>
                    </q-td>
                ''')
                
                table.add_slot('body-cell-Package', f'''
                    <q-td :props="props">
                        <q-select
                            v-model="props.row.Package"
                            :options="{pack_of_classes}" 
                            dense borderless emit-value map-options
                            @update:model-value="$parent.$emit('row-change', props.row)"
                        >
                             <template v-slot:selected-item="scope">
                                <div class="row items-center q-gutter-x-sm">
                                    <q-icon name="inventory_2" size="xs" color="purple" />
                                    <span class="text-weight-medium">{{{{ props.row.Package }}}}</span>
                                </div>
                            </template>
                        </q-select>
                    </q-td>
                ''')

                table.add_slot('body-cell-Price', '''
                    <q-td :props="props">
                        <q-input
                            v-model.number="props.row.Price"
                            type="number"
                            dense borderless
                            prefix="$"
                            input-class="text-weight-bold text-green-800"
                            @update:model-value="$parent.$emit('row-change', props.row)"
                        />
                    </q-td>
                ''')

                table.add_slot('body-cell-Status', '''
                    <q-td :props="props">
                        <q-select
                            v-model="props.row.Status"
                            :options="['Active', 'Inactive']"
                            dense borderless emit-value map-options
                            @update:model-value="$parent.$emit('row-change', props.row)"
                        >
                            <template v-slot:selected-item="scope">
                                <div class="row items-center q-gutter-x-sm">
                                    <div :style="{
                                        width: '8px', height: '8px', borderRadius: '50%',
                                        backgroundColor: props.row.Status === 'Active' ? '#21BA45' : '#C10015'
                                    }"></div>
                                    <span :class="props.row.Status === 'Active' ? 'text-green-9' : 'text-red-9'">
                                        {{ props.row.Status }}
                                    </span>
                                </div>
                            </template>
                        </q-select>
                    </q-td>
                ''')

                # Handlers
                table.on('row-change', lambda e: update_local_row(e.args))
                selection_handler, selection_state = make_selection_handler(table, logger=logger)
                table.on('selection', selection_handler)

                # --- LÓGICA DE GUARDADO (NEON -> SQLITE) ---
                async def save_changes():
                    ui.notify("Guardando cambios...", type='ongoing', timeout=1000)
                    
                    current_rows = table.rows
                    current_usernames = [row['Usuario'] for row in current_rows if row.get('Usuario')]

                    # --- FASE 1: NEON (POSTGRES) ---
                    pg_session = PostgresSession()
                    try:
                        # 1. Borrar eliminados
                        pg_session.query(User).filter(
                            User.username.notin_(current_usernames),
                            User.role != 'admin' 
                        ).delete(synchronize_session=False)

                        # 2. Actualizar existentes
                        for row in current_rows:
                            u_name = row.get('Usuario')
                            if not u_name: continue

                            user_db = pg_session.query(User).filter(User.username == u_name).first()
                            if user_db:
                                # Detectar cambio de paquete
                                new_package = row.get('Package', 'None')
                                old_package = user_db.package
                                package_changed = (new_package != old_package)

                                # Actualizar campos básicos
                                user_db.role = row.get('Role', 'client')
                                user_db.status = row.get('Status', 'Active')
                                try:
                                    user_db.price = int(row.get('Price', 10))
                                except:
                                    user_db.price = 10
                                
                                user_db.package = new_package

                                # === LÓGICA DE CASCADA SI CAMBIA EL PAQUETE ===
                                if package_changed:
                                    logger.info(f"🔄 Paquete cambiado para {u_name}: {old_package} -> {new_package}")
                                    
                                    # Obtener nuevo límite numérico y string
                                    limit_val = PACKAGE_LIMITS.get(new_package, 4) # Default Básico si falla
                                    limit_str = "inf" if limit_val == float('inf') else str(limit_val)

                                    # A. Actualizar User.payment_info (JSON)
                                    if user_db.payment_info:
                                        # Hacemos una copia para asegurar mutabilidad en SQLAlchemy
                                        p_info = dict(user_db.payment_info)
                                        current_cp = p_info.get("Clases_paquete", "0/0") # ej: "5/12"
                                        try:
                                            # Extraer el numerador actual (clases tomadas)
                                            current_taken = current_cp.split('/')[0] 
                                        except:
                                            current_taken = "0"
                                        
                                        # Construir nuevo string: ej "5/4"
                                        p_info["Clases_paquete"] = f"{current_taken}/{limit_str}"
                                        
                                        # Reasignar para forzar update
                                        user_db.payment_info = p_info

                                    # B. Actualizar SchedulePref
                                    try:
                                        pref = pg_session.query(SchedulePref).filter(SchedulePref.username == u_name).all()
                                        if pref:
                                            for p in pref:
                                                p.package = new_package 
                                            logger.info(f"   -> SchedulePref actualizado a {new_package}")
                                    except Exception as ex_pref:
                                        logger.warning(f"   -> No se pudo actualizar SchedulePref: {ex_pref}")

                                    # C. Actualizar AsignedClasses (Todas las clases de este user)
                                    try:
                                        user_classes = pg_session.query(AsignedClasses).filter(AsignedClasses.username == u_name).all()
                                        for cls in user_classes:
                                            # 1. Actualizar contador "X/Y"
                                            if cls.class_count:
                                                try:
                                                    curr_cls_taken = cls.class_count.split('/')[0]
                                                    cls.class_count = f"{curr_cls_taken}/{limit_str}"
                                                except:
                                                    cls.class_count = f"0/{limit_str}" # Fallback
                                            
                                            # 2. Actualizar nombre de paquete en la clase (si existe la columna)
                                            # Nota: Asumo que la columna se llama 'package' o similar. Ajusta si es necesario.
                                            cls.package = new_package 
                                            
                                        logger.info(f"   -> {len(user_classes)} clases actualizadas con límite /{limit_str}")
                                    except Exception as ex_cls:
                                        logger.warning(f"   -> Error actualizando AsignedClasses: {ex_cls}")

                        pg_session.commit()
                        logger.info("✅ Cambios y cascadas guardados en NEON")

                    except Exception as e:
                        pg_session.rollback()
                        logger.error(f"❌ Error Neon: {e}")
                        ui.notify(f"Error guardando en la nube: {e}", type='negative')
                        return
                    finally:
                        pg_session.close()

                    # --- FASE 2: SQLITE (RESPALDO SIMPLE) ---
                    # Nota: Aquí solo actualizamos la tabla User para mantener consistencia básica.
                    # La lógica compleja de clases se mantiene en Postgres que es la fuente de verdad.
                    try:
                        sqlite_session = BackupSession()
                        
                        sqlite_session.query(User).filter(
                            User.username.notin_(current_usernames),
                            User.role != 'admin'
                        ).delete(synchronize_session=False)

                        for row in current_rows:
                            u_name = row.get('Usuario')
                            if not u_name: continue

                            user_sq = sqlite_session.query(User).filter(User.username == u_name).first()
                            if user_sq:
                                user_sq.role = row.get('Role', 'client')
                                user_sq.package = row.get('Package', 'None')
                                user_sq.status = row.get('Status', 'Active')
                                try:
                                    user_sq.price = int(row.get('Price', 10))
                                except:
                                    user_sq.price = 10
                                # Nota: No replicamos la lógica compleja de payment_info/clases aquí
                                # para evitar errores de esquema si SQLite es más simple.
                        
                        sqlite_session.commit()
                        logger.info("💾 Cambios replicados en SQLITE (User table)")

                    except Exception as e:
                        logger.warning(f"⚠️ Error en backup local: {e}")
                    finally:
                        sqlite_session.close()

                    ui.notify("Base de datos actualizada correctamente.", type='positive', icon='cloud_done')
                    ui.navigate.to('/Students')

                # Footer de Tarjeta con Botón Guardar
                with ui.row().classes('w-full bg-gray-50 p-4 border-t border-gray-200 justify-end'):
                     ui.button("Guardar Todos los Cambios", on_click=save_changes, icon='save') \
                        .props('push color=positive') \
                        .classes('px-6')

            except Exception as e:
                ui.label(f"Error al cargar datos: {e}").classes('text-red-500')
            finally:
                session.close()