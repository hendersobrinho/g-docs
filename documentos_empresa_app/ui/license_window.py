from __future__ import annotations

import json
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from documentos_empresa_app.services.license_service import LicenseError, LicenseService
from documentos_empresa_app.ui.styles import configure_app_style
from documentos_empresa_app.utils.common import APP_NAME
from documentos_empresa_app.utils.resources import apply_window_icon


class LicenseWindow(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        license_service: LicenseService,
        status_message: str | None = None,
    ) -> None:
        super().__init__(parent)
        self.parent = parent
        self.license_service = license_service
        self.license_activated = False
        self.status_message = str(status_message or "").strip()

        self.title(f"{APP_NAME} - Ativacao de licenca")
        self.resizable(True, True)
        self.minsize(560, 340)
        parent_toplevel = parent.winfo_toplevel()
        if parent_toplevel.winfo_viewable():
            self.transient(parent_toplevel)
        self.protocol("WM_DELETE_WINDOW", self.close)
        apply_window_icon(self)
        configure_app_style(self)

        self._build_layout()
        self.grab_set()
        self.after(10, self._center_on_parent)

    def _build_layout(self) -> None:
        container = ttk.Frame(self, padding=14)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(2, weight=1)

        ttk.Label(
            container,
            text="Cole ou importe abaixo o JSON completo da licenca para ativar no sistema.",
            justify="left",
        ).grid(row=0, column=0, sticky="w", pady=(0, 10))

        if self.status_message:
            ttk.Label(
                container,
                text=self.status_message,
                justify="left",
                foreground="#8B5E00",
                wraplength=620,
            ).grid(row=1, column=0, sticky="w", pady=(0, 10))

        text_frame = ttk.Frame(container)
        text_frame.grid(row=2, column=0, sticky="nsew")
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)

        self.license_text = tk.Text(text_frame, wrap="word", height=14)
        self.license_text.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.license_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.license_text.configure(yscrollcommand=scrollbar.set)

        button_row = ttk.Frame(container)
        button_row.grid(row=3, column=0, sticky="e", pady=(12, 0))

        ttk.Button(button_row, text="Cancelar", command=self.close, style="Quiet.TButton").pack(side="right")
        ttk.Button(button_row, text="Importar arquivo...", command=self.import_license_file, style="Secondary.TButton").pack(
            side="right",
            padx=(0, 8),
        )
        ttk.Button(button_row, text="Ativar licenca", command=self.activate_license, style="Primary.TButton").pack(side="right", padx=(0, 8))

        self.license_text.focus_set()

    def import_license_file(self) -> None:
        selected_file = filedialog.askopenfilename(
            parent=self,
            title="Selecionar arquivo de licenca",
            filetypes=(("Arquivo JSON", "*.json"), ("Todos os arquivos", "*.*")),
        )
        if not selected_file:
            return
        try:
            raw_text = Path(selected_file).read_text(encoding="utf-8")
        except OSError:
            messagebox.showerror(APP_NAME, "Nao foi possivel ler o arquivo de licenca selecionado.", parent=self)
            return

        self.license_text.delete("1.0", "end")
        self.license_text.insert("1.0", raw_text)

    def activate_license(self) -> None:
        raw_text = self.license_text.get("1.0", "end").strip()
        if not raw_text:
            messagebox.showerror(APP_NAME, "Cole o JSON da licenca antes de ativar.", parent=self)
            return

        try:
            parsed_license = json.loads(raw_text)
        except json.JSONDecodeError:
            messagebox.showerror(APP_NAME, "JSON de licenca invalido.", parent=self)
            return

        try:
            self.license_service.save(parsed_license)
        except LicenseError as exc:
            messagebox.showerror(APP_NAME, str(exc), parent=self)
            return

        self.license_activated = True
        messagebox.showinfo(APP_NAME, "Licenca ativada com sucesso.", parent=self)
        self.destroy()

    def close(self) -> None:
        self.license_activated = False
        self.destroy()

    def _center_on_parent(self) -> None:
        self.update_idletasks()
        toplevel = self.parent.winfo_toplevel()
        if toplevel.winfo_viewable():
            x = toplevel.winfo_rootx() + max((toplevel.winfo_width() - self.winfo_width()) // 2, 0)
            y = toplevel.winfo_rooty() + max((toplevel.winfo_height() - self.winfo_height()) // 2, 0)
        else:
            x = max((self.winfo_screenwidth() - self.winfo_width()) // 2, 0)
            y = max((self.winfo_screenheight() - self.winfo_height()) // 2, 0)
        self.geometry(f"+{x}+{y}")
