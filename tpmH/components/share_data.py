import zoneinfo

days_of_week = ['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo']
duration_options = ['30 minutos', '1 hora']
availability_options = ['Ocupado', 'Libre']
pack_of_classes = ["Plan1", "Plan2", "Plan3"]
PACKAGE_LIMITS = {

    "Plan1":4,
    "Plan2":8,
    "Plan3":12,
    "Ninguno": 0

}

max_days_per_plan = {"Plan1": 1, "Plan2": 2, "Plan3": 3}
max_classes_per_plan = {"Plan1": 1, "Plan2": 1, "Plan3": 3}

hours_of_day = [f'{h:02d}:{m:02d}' for h in range(24) for m in (0, 30)]

# Tablas globales
group_data = {h: {d: '' for d in days_of_week} for h in hours_of_day}
group_data1 = {h: {d: '' for d in days_of_week} for h in hours_of_day}
group_data2 = {h: {d: '' for d in days_of_week} for h in hours_of_day}
group_data3 = {}
group_data4 = {h: {d: "" for d in days_of_week} for h in hours_of_day}
group_data5 = {h: {d: "" for d in days_of_week} for h in hours_of_day}
group_data6 = {}


