from __future__ import annotations

from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from documentos_empresa_app.app_context import ApplicationServices
from documentos_empresa_app.ui.about_dialog import AboutDialog
from documentos_empresa_app.ui.backup_settings_dialog import BackupSettingsDialog
from documentos_empresa_app.ui.controle_tab import ControleTab
from documentos_empresa_app.ui.documento_tab import DocumentoTab
from documentos_empresa_app.ui.empresa_tab import EmpresaTab
from documentos_empresa_app.ui.log_tab import LogTab
from documentos_empresa_app.ui.panorama_tab import PanoramaTab
from documentos_empresa_app.ui.periodo_tab import PeriodoTab
from documentos_empresa_app.ui.user_tab import UserTab
from documentos_empresa_app.utils.auto_backup import (
    load_auto_backup_settings,
    mark_auto_backup_created,
    save_auto_backup_settings,
    should_run_auto_backup,
)
from documentos_empresa_app.utils.common import ValidationError
from documentos_empresa_app.utils.display import get_preferred_screen_bounds
from documentos_empresa_app.utils.helpers import APP_NAME, open_directory_in_file_manager, save_login_preferences
from documentos_empresa_app.utils.resources import apply_window_icon


class MainWindow(tk.Tk):
    def __init__(self, db_path: str | Path, services: ApplicationServices) -> None:
        super().__init__()
        self.db_path = Path(db_path)
        self.services = services
        self.logout_requested = False
        self.restart_requested = False
        self.title(APP_NAME)

        self._configure_style()
        self._configure_window_geometry()
        self._configure_icon()
        self._build_layout()
        self.after(800, self.run_auto_backup_if_due)

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("TNotebook.Tab", padding=(14, 8))
        style.configure("Header.TLabel", font=("TkDefaultFont", 10, "bold"))

    def _configure_window_geometry(self) -> None:
        default_width = 1440
        default_height = 880
        fallback_padding = 80

        pointer_x = self.winfo_pointerx()
        pointer_y = self.winfo_pointery()
        bounds = get_preferred_screen_bounds(pointer_x, pointer_y)
        if bounds:
            available_width = bounds.width
            available_height = bounds.height
            origin_x = bounds.x
            origin_y = bounds.y
        else:
            available_width = self.winfo_screenwidth()
            available_height = self.winfo_screenheight()
            origin_x = 0
            origin_y = 0

        width = min(default_width, max(960, available_width - fallback_padding))
        height = min(default_height, max(700, available_height - fallback_padding))

        x = origin_x + max((available_width - width) // 2, 0)
        y = origin_y + max((available_height - height) // 2, 0)

        self.geometry(f"{width}x{height}+{x}+{y}")
        self.minsize(min(1024, width), min(720, height))

    def _configure_icon(self) -> None:
        apply_window_icon(self)

    def _build_layout(self) -> None:
        container = ttk.Frame(self, padding=12)
        container.pack(fill="both", expand=True)

        header = ttk.Frame(container)
        header.pack(fill="x", pady=(0, 8))

        ttk.Label(header, text=APP_NAME, style="Header.TLabel").pack(side="left")

        header_right = ttk.Frame(header)
        header_right.pack(side="right")

        ttk.Button(header_right, text="Logout", command=self.logout).pack(side="right")
        self.help_menu_button = ttk.Menubutton(header_right, text="Ajuda")
        self.help_menu = tk.Menu(self.help_menu_button, tearoff=False)
        self.help_menu.add_command(label="Sobre...", command=self.show_about)
        self.help_menu_button["menu"] = self.help_menu
        self.help_menu_button.pack(side="right", padx=(0, 8))

        self.database_menu_button = ttk.Menubutton(header_right, text="Banco")
        self.database_menu = tk.Menu(self.database_menu_button, tearoff=False)
        self.database_menu.add_command(label="Fazer backup...", command=self.backup_database)
        self.database_menu.add_command(label="Configurar backup automatico...", command=self.configure_auto_backup)
        self.database_menu.add_command(label="Abrir pasta de backup automatico", command=self.open_auto_backup_directory)
        self.database_menu.add_separator()
        self.database_menu.add_command(label="Restaurar backup...", command=self.restore_database)
        if not self.services.session_service.is_admin():
            self.database_menu.entryconfigure("Restaurar backup...", state="disabled")
        self.database_menu_button["menu"] = self.database_menu
        self.database_menu_button.pack(side="right", padx=(0, 8))
        ttk.Label(header_right, text=f"Banco: {self.db_path}", foreground="#4F4F4F").pack(side="right", padx=(0, 12))
        self.user_info_label = ttk.Label(header_right, foreground="#4F4F4F")
        self.user_info_label.pack(side="right", padx=(0, 12))

        self.notebook = ttk.Notebook(container)
        self.notebook.pack(fill="both", expand=True)

        self.controle_tab = ControleTab(self.notebook, self.services, self.refresh_all_tabs)
        self.panorama_tab = PanoramaTab(
            self.notebook,
            self.services,
            self.refresh_all_tabs,
            on_open_control=self.open_control_for_company_period,
        )

        self.tabs = [
            self.panorama_tab,
            self.controle_tab,
            EmpresaTab(self.notebook, self.services, self.refresh_all_tabs),
            DocumentoTab(self.notebook, self.services, self.refresh_all_tabs),
            PeriodoTab(self.notebook, self.services, self.refresh_all_tabs),
        ]

        tab_titles = [
            "Panorama",
            "Controle",
            "Empresas",
            "Documentos",
            "Periodos",
        ]

        if self.services.session_service.is_admin():
            self.tabs.extend(
                [
                    UserTab(self.notebook, self.services, self.refresh_all_tabs),
                    LogTab(self.notebook, self.services, self.refresh_all_tabs),
                ]
            )
            tab_titles.extend(["Usuarios", "Logs"])

        for tab, title in zip(self.tabs, tab_titles, strict=True):
            self.notebook.add(tab, text=title)

        self.refresh_all_tabs()

    def open_control_for_company_period(self, company_id: int, period_id: int) -> None:
        if self.controle_tab.open_company_period(company_id, period_id):
            self.notebook.select(self.controle_tab)

    def refresh_all_tabs(self) -> None:
        self._refresh_user_info()
        for tab in self.tabs:
            if hasattr(tab, "refresh_data"):
                tab.refresh_data()

    def _refresh_user_info(self) -> None:
        user = self.services.session_service.current_user
        if not user:
            self.user_info_label.configure(text="Usuario: nao autenticado")
            return
        self.user_info_label.configure(
            text=f'Usuario: {user["username"]} ({user["tipo_usuario"]})'
        )

    def logout(self) -> None:
        if not messagebox.askyesno(APP_NAME, "Deseja encerrar a sessao atual e voltar para o login?", parent=self):
            return
        current_user = self.services.session_service.current_user
        current_username = current_user["username"] if current_user else ""
        self.services.auth_service.revoke_remembered_session(self.services.session_service.get_remembered_token())
        save_login_preferences(
            current_username,
            remember_credential=False,
            remembered_token=None,
        )
        self.logout_requested = True
        self.services.session_service.logout()
        self.destroy()

    def show_about(self) -> None:
        AboutDialog(self)

    def backup_database(self) -> None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = filedialog.asksaveasfilename(
            parent=self,
            title="Salvar backup do banco",
            defaultextension=".db",
            initialdir=str(self.db_path.parent),
            initialfile=f"{self.db_path.stem}_backup_{timestamp}.db",
            filetypes=[
                ("Banco SQLite", "*.db"),
                ("Todos os arquivos", "*.*"),
            ],
        )
        if not file_path:
            return

        try:
            result = self.services.database_maintenance_service.create_backup(file_path)
        except ValidationError as exc:
            messagebox.showerror(APP_NAME, str(exc), parent=self)
            return

        messagebox.showinfo(
            APP_NAME,
            (
                "Backup gerado com sucesso.\n\n"
                f'Arquivo: {result["path"]}\n'
                f'Tamanho: {result["size_bytes"]} bytes'
            ),
            parent=self,
        )

    def configure_auto_backup(self) -> None:
        dialog = BackupSettingsDialog(self, load_auto_backup_settings())
        self.wait_window(dialog)
        if dialog.result is None:
            return

        settings = save_auto_backup_settings(dialog.result)
        state_label = "ativado" if settings["enabled"] else "desativado"
        messagebox.showinfo(
            APP_NAME,
            f"Backup automatico {state_label}.",
            parent=self,
        )

    def open_auto_backup_directory(self) -> None:
        settings = load_auto_backup_settings()
        backup_dir = Path(settings["directory"]).expanduser()
        try:
            backup_dir.mkdir(parents=True, exist_ok=True)
            open_directory_in_file_manager(backup_dir)
        except (OSError, ValidationError) as exc:
            messagebox.showerror(APP_NAME, str(exc), parent=self)

    def run_auto_backup_if_due(self) -> None:
        settings = load_auto_backup_settings()
        if not should_run_auto_backup(settings):
            return

        try:
            result = self.services.database_maintenance_service.create_timestamped_backup(
                settings["directory"],
                keep_last=settings["keep_last"],
            )
            mark_auto_backup_created(result)
        except ValidationError as exc:
            messagebox.showwarning(
                APP_NAME,
                f"Nao foi possivel gerar o backup automatico.\n\n{exc}",
                parent=self,
            )

    def restore_database(self) -> None:
        file_path = filedialog.askopenfilename(
            parent=self,
            title="Selecionar backup para restaurar",
            initialdir=str(self.db_path.parent),
            filetypes=[
                ("Banco SQLite", "*.db"),
                ("Todos os arquivos", "*.*"),
            ],
        )
        if not file_path:
            return
        if not messagebox.askyesno(
            APP_NAME,
            (
                "A restauracao substituira os dados atuais do banco em uso.\n\n"
                "Deseja continuar?"
            ),
            parent=self,
        ):
            return
        if not messagebox.askyesno(
            APP_NAME,
            "Confirma a restauracao definitiva desse backup?",
            parent=self,
        ):
            return

        try:
            self.services.database_maintenance_service.restore_backup(file_path)
        except ValidationError as exc:
            messagebox.showerror(APP_NAME, str(exc), parent=self)
            return

        messagebox.showinfo(
            APP_NAME,
            "Backup restaurado com sucesso. O sistema sera recarregado para aplicar os dados restaurados.",
            parent=self,
        )
        self.restart_requested = True
        self.destroy()
