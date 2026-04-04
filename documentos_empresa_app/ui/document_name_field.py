from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from documentos_empresa_app.utils.common import ValidationError


class DocumentNameManagerDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        documento_service,
        tipo_service,
        dialog_title: str,
        initial_tipo_id: int | None = None,
    ) -> None:
        super().__init__(parent.winfo_toplevel())
        self.parent = parent
        self.documento_service = documento_service
        self.tipo_service = tipo_service
        self.dialog_title = dialog_title
        self.initial_tipo_id = initial_tipo_id
        self.selected_name_id: int | None = None
        self.tipo_map: dict[str, int] = {}
        self.nome_var = tk.StringVar()
        self.tipo_var = tk.StringVar()

        self.title(f"{dialog_title} - Nomes padrao")
        self.transient(parent.winfo_toplevel())
        self.resizable(True, True)
        self.minsize(520, 340)

        self._build_layout()
        self.refresh_type_options()
        self.refresh_names()
        self.grab_set()
        self.after(10, self._center_on_parent)

    def _build_layout(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        ttk.Label(
            self,
            text=(
                "Cadastre aqui os nomes padrao sugeridos pelo sistema. "
                "Essa lista nao usa documentos importados como sugestao automatica."
            ),
            justify="left",
            wraplength=500,
        ).grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 8))

        list_frame = ttk.LabelFrame(self, text="Nomes padrao cadastrados", padding=10)
        list_frame.grid(row=1, column=0, sticky="nsew", padx=12)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            list_frame,
            columns=("nome", "tipo"),
            show="headings",
            selectmode="browse",
            height=10,
        )
        self.tree.heading("nome", text="Nome do documento")
        self.tree.heading("tipo", text="Tipo")
        self.tree.column("nome", width=280)
        self.tree.column("tipo", width=180)
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self.load_selected_name)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        editor = ttk.LabelFrame(self, text="Editar lista", padding=10)
        editor.grid(row=2, column=0, sticky="ew", padx=12, pady=(12, 12))
        editor.columnconfigure(0, weight=1)
        editor.columnconfigure(1, weight=1)

        ttk.Label(editor, text="Tipo do documento").grid(row=0, column=0, sticky="w")
        self.tipo_combo = ttk.Combobox(editor, textvariable=self.tipo_var, state="readonly")
        self.tipo_combo.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(0, 8))

        ttk.Label(editor, text="Nome padrao").grid(row=0, column=1, sticky="w")
        entry = ttk.Entry(editor, textvariable=self.nome_var)
        entry.grid(row=1, column=1, sticky="ew", pady=(0, 8))
        entry.bind("<Return>", self.save_name)

        self.save_button = ttk.Button(editor, text="Adicionar", command=self.save_name)
        self.save_button.grid(row=2, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(editor, text="Limpar", command=self.clear_selection).grid(row=2, column=1, sticky="ew")
        ttk.Button(editor, text="Excluir do sistema", command=self.delete_selected_name).grid(
            row=3, column=0, columnspan=2, sticky="ew", pady=(8, 0)
        )

    def _center_on_parent(self) -> None:
        self.update_idletasks()
        parent = self.parent.winfo_toplevel()
        x = parent.winfo_rootx() + max((parent.winfo_width() - self.winfo_width()) // 2, 0)
        y = parent.winfo_rooty() + max((parent.winfo_height() - self.winfo_height()) // 2, 0)
        self.geometry(f"+{x}+{y}")

    def refresh_type_options(self) -> None:
        tipos = self.tipo_service.list_tipos()
        self.tipo_map = {tipo["nome_tipo"]: tipo["id"] for tipo in tipos}
        self.tipo_combo["values"] = list(self.tipo_map.keys())

        if self.tipo_var.get() in self.tipo_map:
            return

        if self.initial_tipo_id:
            initial_type = next((tipo for tipo in tipos if tipo["id"] == self.initial_tipo_id), None)
            if initial_type:
                self.tipo_var.set(initial_type["nome_tipo"])
                return

        if tipos and not self.tipo_var.get():
            self.tipo_var.set(tipos[0]["nome_tipo"])

    def refresh_names(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for item in self.documento_service.list_system_document_names():
            self.tree.insert(
                "",
                "end",
                iid=str(item["id"]),
                values=(item["nome_documento"], item["nome_tipo"]),
            )

        if self.selected_name_id and self.tree.exists(str(self.selected_name_id)):
            self.tree.selection_set(str(self.selected_name_id))
            self.tree.focus(str(self.selected_name_id))
            self.tree.see(str(self.selected_name_id))
            return

        self.clear_selection()

    def load_selected_name(self, _event=None) -> None:
        selection = self.tree.selection()
        if not selection:
            return

        system_name = self.documento_service.get_system_document_name(int(selection[0]))
        self.selected_name_id = system_name["id"]
        self.nome_var.set(system_name["nome_documento"])
        self.tipo_var.set(system_name["nome_tipo"])
        self.save_button.configure(text="Salvar alteracoes")

    def clear_selection(self) -> None:
        self.selected_name_id = None
        self.nome_var.set("")
        self.save_button.configure(text="Adicionar")
        selection = self.tree.selection()
        if selection:
            self.tree.selection_remove(*selection)
        if self.tipo_var.get() not in self.tipo_map:
            self.refresh_type_options()

    def save_name(self, _event=None) -> None:
        tipo_id = self.tipo_map.get(self.tipo_var.get())
        if not tipo_id:
            messagebox.showwarning(self.dialog_title, "Selecione um tipo valido.", parent=self)
            return

        try:
            if self.selected_name_id:
                self.documento_service.update_system_document_name(
                    self.selected_name_id,
                    tipo_id,
                    self.nome_var.get(),
                )
                messagebox.showinfo(self.dialog_title, "Nome padrao atualizado com sucesso.", parent=self)
            else:
                self.selected_name_id = self.documento_service.create_system_document_name(
                    tipo_id,
                    self.nome_var.get(),
                )
                messagebox.showinfo(self.dialog_title, "Nome padrao cadastrado com sucesso.", parent=self)
        except ValidationError as exc:
            messagebox.showerror(self.dialog_title, str(exc), parent=self)
            return

        self.refresh_names()

    def delete_selected_name(self) -> None:
        if not self.selected_name_id:
            messagebox.showwarning(self.dialog_title, "Selecione um nome padrao na lista.", parent=self)
            return

        system_name = self.documento_service.get_system_document_name(self.selected_name_id)
        prompt = (
            f'Deseja excluir "{system_name["nome_documento"]}" '
            f'do tipo "{system_name["nome_tipo"]}" da lista do sistema?'
        )
        if not messagebox.askyesno(self.dialog_title, prompt, parent=self):
            return

        self.documento_service.delete_system_document_name(self.selected_name_id)
        self.refresh_names()
        messagebox.showinfo(self.dialog_title, "Nome padrao removido da lista do sistema.", parent=self)
