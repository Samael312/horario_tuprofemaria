# ui/ui.py
from nicegui import ui, app
from frontend.screen.login_screen import setup_auth_system
from frontend.screen.MainScreen.mainscreen import create_main_screen
from frontend.screen.signup_screen import create_signup_screen
from frontend.screen.reset_screen import reset_password_screen
from frontend.screen.MainScreen.Mainpages.profile import profile
from frontend.screen.MainScreen.Mainpages.myclasses import my_classes
from frontend.screen.MainScreen.Subpages.new_Student import new_student
from frontend.screen.MainScreen.Subpages.old_Student import OldStudent
from frontend.screen.MainAdminScreen.main_admin_screen import main_admin_screen
from frontend.screen.MainAdminScreen.Mainpages.AdminProfile import profileAdmin
from frontend.screen.MainAdminScreen.Mainpages.myclassesAdmin import my_classesAdmin
from frontend.screen.MainScreen.Mainpages.schedule import scheduleMaker
from frontend.screen.MainScreen.Subpages.editProfile import profile_edit
from frontend.screen.MainAdminScreen.Mainpages.students_admin import students
from frontend.screen.MainAdminScreen.Mainpages.Adm_horario import adm_horario
from frontend.screen.MainAdminScreen.Subpages.edit_student import students_edit
from frontend.screen.MainAdminScreen.Subpages.editAdminProfile import profileA_edit
from frontend.screen.MainAdminScreen.Subpages.teacher_edit import teacherAdmin
from frontend.screen.MainScreen.Mainpages.teacher import teacher_profile_view
from frontend.screen.mainpage import render_landing_page
from frontend.screen.MainAdminScreen.Mainpages.materialAdmin import materials_page
from frontend.screen.MainAdminScreen.Mainpages.workAdmin import homework_page
from frontend.screen.MainScreen.Mainpages.material import student_materials_page
from frontend.screen.MainScreen.Mainpages.work import student_homework_page
from frontend.screen.adv_method import adv_method

def init_ui():
    """Puente entre las pantallas de la app."""
    setup_auth_system()       # Esto crea /login y registra el middleware
    adv_method()
    
    # Página principal (solo accesible si el usuario está autenticado)
    @ui.page('/')
    def main_page():
        if not app.storage.user.get('authenticated', False):
            ui.navigate.to('/MainPage')  # Redirige a la página de inicio si no está autenticado
        
            return
        render_landing_page()
        
        
        create_main_screen()  # delega la UI real a mainscreen.py
        create_signup_screen()  # delega la UI real a signup_screen.py
        reset_password_screen()  # delega la UI real a reset_screen.py
        new_student()
        OldStudent()
        profile()
        profile_edit()
        my_classes()
        scheduleMaker()
        teacher_profile_view()
        student_materials_page()
        student_homework_page()
        
        
        

        main_admin_screen()
        my_classesAdmin()
        profileAdmin()
        students()
        adm_horario()
        students_edit()
        profileA_edit()
        teacherAdmin()
        materials_page()
        homework_page()
