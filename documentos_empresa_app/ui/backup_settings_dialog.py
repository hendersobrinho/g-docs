from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from documentos_empresa_app.utils.common import APP_NAME
from documentos_empresa_app.ui.status_icons import set_button_icon
from documentos_empresa_app.ui.styles import configure_app_style
from documentos_empresa_app.utils.auto_backup import (
    MAX_AUTO_BACKUP_INTERVAL_DAYS,
    MAX_AUTO_BACKUP_KEEP_LAST,
    MIN_AUTO_BACKUP_INTERVAL_DAYS,
    MIN_AUTO_BACKUP_KEEP_LAST,
    normalize_auto_backup_settings,
)
from documentos_empresa_app.utils.resources import apply_window_icon


class BackupSettingsDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, settings: dict) -> None:
        super().__init__(parent)
        self.parent = parent
        self.original_settings = normalize_auto_backup_settings(settings)
        self.result: dict | None = None

        self.enabled_var = tk.BooleanVar(value=self.original_settings["enabled"])
        self.directory_var = tk.StringVar(value=self.original_settings["directory"])
        self.interval_days_var = tk.StringVar(value=str(self.original_settings["interval_days"]))
        self.keep_last_var = tk.StringVar(value=str(self.original_settings["keep_last"]))

        self.title(f"{APP_NAME} - Backup automatico")
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        apply_window_icon(self)
        configure_app_style(self)

        self._build_layout()
        self._toggle_fields()
        self.grab_set()
        self.after(10, self._center_on_parent)
        self.wait_visibility()

    def _build_layout(self) -> None:
        container = ttk.Frame(self, padding=14)
        container.pack(fill="both", expand=True)

        self.enabled_check = ttk.Checkbutton(
            container,
            text="Ativar backup automatico",
            variable=self.enabled_var,
            command=self._toggle_fields,
        )
        self.enabled_check.grid(row=0, column=0, columnspan=3, sticky="w")

        ttk.Label(container, text="Pasta de backup").grid(row=1, column=0, columnspan=3, sticky="w", pady=(12, 0))
        self.directory_entry = ttk.Entry(container, textvariable=self.directory_var, width=62)
        self.directory_entry.grid(row=2, column=0, columnspan=2, sticky="ew", padx=(0, 8))
        self.choose_button = ttk.Button(container, text="Escolher...", command=self.choose_directory, style="Secondary.TButton")
        self.choose_button.grid(row=2, column=2, sticky="ew")

        ttk.Label(container, text="Intervalo em dias").grid(row=3, column=0, sticky="w", pady=(12, 0))
        self.interval_spinbox = ttk.Spinbox(
            container,
            textvariable=self.interval_days_var,
            from_=MIN_AUTO_BACKUP_INTERVAL_DAYS,
            to=MAX_AUTO_BACKUP_INTERVAL_DAYS,
            width=8,
        )
        self.interval_spinbox.grid(row=4, column=0, sticky="w")

        ttk.Label(container, text="Manter ultimos").grid(row=3, column=1, sticky="w", pady=(12, 0))
        self.keep_last_spinbox = ttk.Spinbox(
            container,
            textvariable=self.keep_last_var,
            from_=MIN_AUTO_BACKUP_KEEP_LAST,
            to=MAX_AUTO_BACKUP_KEEP_LAST,
            width=8,
        )
        self.keep_last_spinbox.grid(row=4, column=1, sticky="w")

        last_backup_at = self.original_settings.get("last_backup_at") or "Nunca"
        last_backup_path = self.original_settings.get("last_backup_path") or "-"
        ttk.Label(container, text=f"Ultimo backup: {last_backup_at}", foreground="#4F4F4F").grid(
            row=5,
            column=0,
            columnspan=3,
            sticky="w",
            pady=(14, 0),
        )
        ttk.Label(container, text=f"Arquivo: {last_backup_path}", foreground="#4F4F4F", wraplength=620).grid(
            row=6,
            column=0,
            columnspan=3,
            sticky="w",
            pady=(2, 0),
        )

        button_row = ttk.Frame(container)
        button_row.grid(row=7, column=0, columnspan=3, sticky="e", pady=(18, 0))
        ttk.Button(button_row, text="Cancelar", command=self.cancel, style="Quiet.TButton").pack(side="right")
        self.save_button = ttk.Button(button_row, text="Salvar", command=self.confirm, style="Primary.TButton")
        self.save_button.pack(side="right", padx=(0, 8))
        set_button_icon(self.save_button)

        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)

    def choose_directory(self) -> None:
        initial_dir = Path(self.directory_var.get()).expanduser()
        if not initial_dir.exists():
            initial_dir = Path.home()
        selected = filedialog.askdirectory(
            parent=self,
            title="Escolha a pasta dos backups automaticos",
            initialdir=str(initial_dir),
            mustexist=False,
        )
        if selected:
            self.directory_var.set(selected)

    def confirm(self) -> None:
        settings = normalize_auto_backup_settings(
            {
                "enabled": self.enabled_var.get(),
                "directory": self.directory_var.get(),
                "interval_days": self.interval_days_var.get(),
                "keep_last": self.keep_last_var.get(),
                "last_backup_at": self.original_settings.get("last_backup_at"),
                "last_backup_path": self.original_settings.get("last_backup_path"),
            }
        )

        if settings["enabled"]:
            backup_dir = Path(settings["directory"]).expanduser()
            try:
                backup_dir.mkdir(parents=True, exist_ok=True)
            except OSError:
                messagebox.showerror(APP_NAME, "Nao foi possivel criar ou acessar a pasta de backup.", parent=self)
                return
            if not backup_dir.is_dir():
                messagebox.showerror(APP_NAME, "Informe uma pasta valida para o backup automatico.", parent=self)
                return

        self.result = settings
        self.destroy()

    def cancel(self) -> None:
        self.result = None
        self.destroy()

    def _toggle_fields(self) -> None:
        state = "normal" if self.enabled_var.get() else "disabled"
        self.directory_entry.configure(state=state)
        self.choose_button.configure(state=state)
        self.interval_spinbox.configure(state=state)
        self.keep_last_spinbox.configure(state=state)

    def _center_on_parent(self) -> None:
        self.update_idletasks()
        toplevel = self.parent.winfo_toplevel()
        x = toplevel.winfo_rootx() + max((toplevel.winfo_width() - self.winfo_width()) // 2, 0)
        y = toplevel.winfo_rooty() + max((toplevel.winfo_height() - self.winfo_height()) // 2, 0)
        self.geometry(f"+{x}+{y}")
