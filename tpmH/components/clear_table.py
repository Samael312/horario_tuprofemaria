from nicegui import ui

def clear_table(table, group_dict):
    for h in group_dict:
        for d in group_dict[h]:
            group_dict[h][d] = ''

    table.rows = []
    table.update()

    ui.notify("Tabla limpiada", color="positive")

