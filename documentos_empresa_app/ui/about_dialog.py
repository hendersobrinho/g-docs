from __future__ import annotations
import webbrowser
import tkinter as tk
from tkinter import ttk

from documentos_empresa_app import __version__
from documentos_empresa_app.ui.styles import configure_app_style
from documentos_empresa_app.utils.common import APP_NAME
from documentos_empresa_app.utils.resources import apply_window_icon, iter_icon_candidates


CONTACT_EMAIL = "hnd.lab.dev@gmail.com"
DEVELOPER_NAME = "Henderson Pereira S. Júnior"
SITE_DEVELOPER = "www.henderlab.com.br"
SITE_DEVELOPER_URL = "https://www.henderlab.com.br"

class AboutDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent)
        self.parent = parent
        self.icon_image: tk.PhotoImage | None = None

        self.title(f"Sobre o {APP_NAME}")
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        apply_window_icon(self)
        configure_app_style(self)

        self._build_layout()
        self.grab_set()
        self.after(10, self._center_on_parent)
        self.wait_visibility()

    def _build_layout(self) -> None:
        container = ttk.Frame(self, padding=18)
        container.pack(fill="both", expand=True)

        header = ttk.Frame(container)
        header.pack(fill="x")

        icon_path = next((path for path in iter_icon_candidates() if path.suffix.lower() == ".png"), None)
        if icon_path:
            self.icon_image = tk.PhotoImage(file=str(icon_path)).subsample(8, 8)
            ttk.Label(header, image=self.icon_image).pack(side="left", padx=(0, 14))

        title_block = ttk.Frame(header)
        title_block.pack(side="left", fill="x", expand=True)
        ttk.Label(title_block, text=APP_NAME, font=("TkDefaultFont", 16, "bold")).pack(anchor="w")
        ttk.Label(title_block, text=f"Versao {__version__}", style="Subtle.TLabel").pack(anchor="w", pady=(2, 0))

        body = ttk.Frame(container)
        body.pack(fill="x", pady=(16, 0))
        ttk.Label(body, text="Controle mensal de documentos empresariais.").pack(anchor="w")
        ttk.Label(body, text=f"Desenvolvido por: {DEVELOPER_NAME}.").pack(anchor="w", pady=(10, 0))
        ttk.Label(body, text=f"Contato: {CONTACT_EMAIL}").pack(anchor="w", pady=(2, 0))
        site_row = ttk.Frame(body)
        site_row.pack(anchor="w", pady=(3, 0))

        ttk.Label(site_row, text="Site org: ").pack(side="left")

        site_link = ttk.Label(
            site_row,
            text=SITE_DEVELOPER,
            foreground="#2563EB",
            cursor="hand2",
            font=("TkDefaultFont", 9, "underline"),
        )
        site_link.pack(side="left")
        site_link.bind("<Button-1>", self._open_site)

        button_row = ttk.Frame(container)
        button_row.pack(fill="x", pady=(18, 0))
        ttk.Button(button_row, text="Copiar email", command=self._copy_email, style="Secondary.TButton").pack(side="left")
        ttk.Button(button_row, text="Fechar", command=self.destroy, style="Quiet.TButton").pack(side="right")

    def _copy_email(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(CONTACT_EMAIL)
    
    def _open_site(self, event: tk.Event | None = None) -> None:
        webbrowser.open(SITE_DEVELOPER_URL)

    def _center_on_parent(self) -> None:
        self.update_idletasks()
        toplevel = self.parent.winfo_toplevel()
        x = toplevel.winfo_rootx() + max((toplevel.winfo_width() - self.winfo_width()) // 2, 0)
        y = toplevel.winfo_rooty() + max((toplevel.winfo_height() - self.winfo_height()) // 2, 0)
        self.geometry(f"+{x}+{y}")
