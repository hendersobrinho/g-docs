from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from documentos_empresa_app.utils.common import TYPE_OCCURRENCE_CHOICES, TYPE_OCCURRENCE_MENSAL
from documentos_empresa_app.utils.helpers import ValidationError


class DocumentTypeManagerDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        tipo_service,
        dialog_title: str,
        initial_tipo_id: int | None = None,
        allow_apply_to_document: bool = True,
    ) -> None:
        super().__init__(parent.winfo_toplevel())
        self.parent = parent
        self.tipo_service = tipo_service
        self.dialog_title = dialog_title
        self.initial_tipo_id = initial_tipo_id
        self.allow_apply_to_document = allow_apply_to_document
        self.selected_tipo_id: int | None = None
        self.applied_type_id: int | None = None
        self.data_changed = False
        self.nome_var = tk.StringVar()
        self.ocorrencia_label_var = tk.StringVar()
        self.occurrence_label_by_value = {value: label for value, label in TYPE_OCCURRENCE_CHOICES}
        self.occurrence_value_by_label = {label: value for value, label in TYPE_OCCURRENCE_CHOICES}

        self.title(f"{dialog_title} - Tipos de documento")
        self.transient(parent.winfo_toplevel())
        self.resizable(True, True)
        self.minsize(620, 420)

        self._build_layout()
        self.ocorrencia_label_var.set(self._occurrence_label(TYPE_OCCURRENCE_MENSAL))
        self.refresh_types()
        self.grab_set()
        self.after(10, self._center_on_parent)

    def _build_layout(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        ttk.Label(
            self,
            text=(
                "Gerencie aqui os tipos de documento sem poluir a tela principal. "
                "Voce pode cadastrar, ajustar a ocorrencia, excluir tipos sem uso e aplicar um tipo direto no formulario."
            ),
            justify="left",
            wraplength=600,
        ).grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 8))

        list_frame = ttk.LabelFrame(self, text="Tipos cadastrados", padding=10)
        list_frame.grid(row=1, column=0, sticky="nsew", padx=12)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            list_frame,
            columns=("nome", "ocorrencia"),
            show="headings",
            selectmode="browse",
            height=12,
        )
        self.tree.heading("nome", text="Nome do tipo")
        self.tree.heading("ocorrencia", text="Ocorrencia")
        self.tree.column("nome", width=330)
        self.tree.column("ocorrencia", width=190, anchor="center")
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self.load_selected_tipo)
        self.tree.bind("<Double-1>", self.apply_selected_type)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        editor = ttk.LabelFrame(self, text="Editar lista", padding=10)
        editor.grid(row=2, column=0, sticky="ew", padx=12, pady=(12, 12))
        editor.columnconfigure(0, weight=1)
        editor.columnconfigure(1, weight=1)

        ttk.Label(editor, text="Nome do tipo").grid(row=0, column=0, sticky="w")
        ttk.Entry(editor, textvariable=self.nome_var).grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(0, 8))

        ttk.Label(editor, text="Ocorrencia").grid(row=0, column=1, sticky="w")
        self.ocorrencia_combo = ttk.Combobox(
            editor,
            textvariable=self.ocorrencia_label_var,
            state="readonly",
            values=[label for _value, label in TYPE_OCCURRENCE_CHOICES],
        )
        self.ocorrencia_combo.grid(row=1, column=1, sticky="ew", pady=(0, 8))

        self.save_button = ttk.Button(editor, text="Cadastrar tipo", command=self.save_tipo)
        self.save_button.grid(row=2, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(editor, text="Limpar", command=self.clear_form).grid(row=2, column=1, sticky="ew")

        self.use_button = ttk.Button(editor, text="Usar no documento", command=self.apply_selected_type)
        self.use_button.grid(row=3, column=0, sticky="ew", padx=(0, 8), pady=(8, 0))
        self.delete_button = ttk.Button(editor, text="Excluir tipo selecionado", command=self.delete_tipo)
        self.delete_button.grid(row=3, column=1, sticky="ew", pady=(8, 0))

        ttk.Label(
            editor,
            text="Mensal: todos os meses. Trimestral: libera 01, 04, 07 e 10. Anual em janeiro: libera apenas janeiro.",
            justify="left",
            wraplength=580,
            foreground="#5A5A5A",
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(8, 0))

    def _center_on_parent(self) -> None:
        self.update_idletasks()
        parent = self.parent.winfo_toplevel()
        x = parent.winfo_rootx() + max((parent.winfo_width() - self.winfo_width()) // 2, 0)
        y = parent.winfo_rooty() + max((parent.winfo_height() - self.winfo_height()) // 2, 0)
        self.geometry(f"+{x}+{y}")

    def refresh_types(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for tipo in self.tipo_service.list_tipos():
            self.tree.insert(
                "",
                "end",
                iid=str(tipo["id"]),
                values=(tipo["nome_tipo"], self._occurrence_label(tipo.get("regra_ocorrencia"))),
            )

        target_id = self.selected_tipo_id or self.initial_tipo_id
        if target_id and self.tree.exists(str(target_id)):
            self.tree.selection_set(str(target_id))
            self.tree.focus(str(target_id))
            self.tree.see(str(target_id))
            self.load_selected_tipo()
            return

        self.clear_form(clear_selection=False)

    def load_selected_tipo(self, _event=None) -> None:
        selection = self.tree.selection()
        if not selection:
            return

        tipo = self.tipo_service.get_tipo(int(selection[0]))
        self.selected_tipo_id = tipo["id"]
        self.nome_var.set(tipo["nome_tipo"])
        self.ocorrencia_label_var.set(self._occurrence_label(tipo.get("regra_ocorrencia")))
        self.save_button.configure(text="Salvar alteracoes")
        self._update_action_buttons()

    def clear_form(self, *, clear_selection: bool = True) -> None:
        self.selected_tipo_id = None
        self.nome_var.set("")
        self.ocorrencia_label_var.set(self._occurrence_label(TYPE_OCCURRENCE_MENSAL))
        self.save_button.configure(text="Cadastrar tipo")
        if clear_selection:
            selection = self.tree.selection()
            if selection:
                self.tree.selection_remove(*selection)
        self._update_action_buttons()

    def save_tipo(self) -> None:
        target_tipo_id = self.selected_tipo_id
        try:
            if self.selected_tipo_id:
                self.tipo_service.update_tipo(
                    self.selected_tipo_id,
                    self.nome_var.get(),
                    self._selected_occurrence_value(),
                )
                messagebox.showinfo("Tipos", "Tipo atualizado com sucesso.", parent=self)
            else:
                target_tipo_id = self.tipo_service.create_tipo(
                    self.nome_var.get(),
                    self._selected_occurrence_value(),
                )
                messagebox.showinfo("Tipos", "Tipo cadastrado com sucesso.", parent=self)
        except ValidationError as exc:
            messagebox.showerror("Tipos", str(exc), parent=self)
            return

        self.selected_tipo_id = target_tipo_id
        self.data_changed = True
        self.refresh_types()

    def delete_tipo(self) -> None:
        if not self.selected_tipo_id:
            messagebox.showwarning("Tipos", "Selecione um tipo na lista.", parent=self)
            return

        if not messagebox.askyesno("Excluir tipo", "Deseja excluir o tipo selecionado?", parent=self):
            return

        try:
            self.tipo_service.delete_tipo(self.selected_tipo_id)
        except ValidationError as exc:
            messagebox.showerror("Tipos", str(exc), parent=self)
            return

        self.data_changed = True
        self.initial_tipo_id = None
        self.clear_form()
        self.refresh_types()
        messagebox.showinfo("Tipos", "Tipo excluido com sucesso.", parent=self)

    def apply_selected_type(self, _event=None) -> str | None:
        if not self.selected_tipo_id:
            messagebox.showwarning("Tipos", "Selecione um tipo na lista.", parent=self)
            return "break"

        self.applied_type_id = self.selected_tipo_id
        self.destroy()
        return "break"

    def _update_action_buttons(self) -> None:
        has_selection = self.selected_tipo_id is not None
        self.use_button.configure(state="normal" if self.allow_apply_to_document and has_selection else "disabled")
        self.delete_button.configure(state="normal" if has_selection else "disabled")

    def _occurrence_label(self, occurrence_value: str | None) -> str:
        return self.occurrence_label_by_value.get(occurrence_value or TYPE_OCCURRENCE_MENSAL, "Mensal")

    def _selected_occurrence_value(self) -> str:
        label = self.ocorrencia_label_var.get().strip()
        return self.occurrence_value_by_label.get(label, TYPE_OCCURRENCE_MENSAL)
