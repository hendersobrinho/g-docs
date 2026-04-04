from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from documentos_empresa_app.ui.delivery_methods_field import DeliveryMethodsField
from documentos_empresa_app.utils.common import TYPE_OCCURRENCE_CHOICES, TYPE_OCCURRENCE_MENSAL
from documentos_empresa_app.utils.helpers import CompanySelector, ValidationError


class DocumentoTab(ttk.Frame):
    def __init__(self, master, services, on_data_changed) -> None:
        super().__init__(master, padding=12)
        self.services = services
        self.on_data_changed = on_data_changed
        self.current_company_id: int | None = None
        self.selected_documento_id: int | None = None
        self.selected_tipo_id: int | None = None

        self.nome_var = tk.StringVar()
        self.tipo_var = tk.StringVar()
        self.tipo_nome_var = tk.StringVar()
        self.tipo_ocorrencia_label_var = tk.StringVar()
        self.nome_sugestao_var = tk.StringVar(value="Selecione um tipo para reutilizar nomenclaturas ja cadastradas.")
        self.tipo_map: dict[str, int] = {}
        self.occurrence_label_by_value = {value: label for value, label in TYPE_OCCURRENCE_CHOICES}
        self.occurrence_value_by_label = {label: value for value, label in TYPE_OCCURRENCE_CHOICES}

        self._build_layout()
        self.tipo_ocorrencia_label_var.set(self._occurrence_label(TYPE_OCCURRENCE_MENSAL))

    def _build_layout(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self.company_selector = CompanySelector(
            self,
            self.services.empresa_service,
            active_only=False,
            on_selected=self.on_company_selected,
            on_cleared=self._clear_company_context,
        )
        self.company_selector.grid(row=0, column=0, sticky="ew", pady=(0, 12))

        workspace = ttk.PanedWindow(self, orient="horizontal")
        workspace.grid(row=1, column=0, sticky="nsew")

        document_panel = ttk.Frame(workspace)
        document_panel.columnconfigure(0, weight=1)
        document_panel.rowconfigure(1, weight=1)
        workspace.add(document_panel, weight=5)

        type_panel = ttk.Frame(workspace)
        type_panel.columnconfigure(0, weight=1)
        type_panel.rowconfigure(0, weight=1)
        workspace.add(type_panel, weight=3)

        form = ttk.LabelFrame(document_panel, text="Cadastro e manutencao de documentos", padding=12)
        form.grid(row=0, column=0, sticky="ew", pady=(0, 12))

        field_row = ttk.Frame(form)
        field_row.grid(row=0, column=0, sticky="ew")
        field_row.columnconfigure(0, weight=2)
        field_row.columnconfigure(1, weight=1)

        ttk.Label(field_row, text="Nome do documento").grid(row=0, column=0, sticky="w")
        self.nome_combo = ttk.Combobox(field_row, textvariable=self.nome_var)
        self.nome_combo.grid(row=1, column=0, sticky="ew", padx=(0, 10))
        self.nome_combo.bind("<KeyRelease>", self._on_document_name_typed)
        self.nome_combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh_document_name_suggestions())

        ttk.Label(field_row, text="Tipo do documento").grid(row=0, column=1, sticky="w")
        self.tipo_combo = ttk.Combobox(field_row, textvariable=self.tipo_var, state="readonly")
        self.tipo_combo.grid(row=1, column=1, sticky="ew")
        self.tipo_combo.bind("<<ComboboxSelected>>", self._on_document_type_changed)

        self.delivery_field = DeliveryMethodsField(
            form,
            title="Meios de recebimento do documento",
            dialog_title="Documentos",
            delivery_method_service=self.services.delivery_method_service,
        )
        self.delivery_field.grid(row=1, column=0, sticky="ew", pady=(10, 0))

        action_row = ttk.Frame(form)
        action_row.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        action_row.columnconfigure(0, weight=1)
        action_row.columnconfigure(1, weight=1)

        self.save_button = ttk.Button(action_row, text="Cadastrar documento", command=self.save_document)
        self.save_button.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(action_row, text="Limpar", command=self.clear_form).grid(row=0, column=1, sticky="ew")

        ttk.Label(
            form,
            textvariable=self.nome_sugestao_var,
            justify="left",
            wraplength=560,
        ).grid(row=3, column=0, sticky="w", pady=(8, 0))

        ttk.Label(
            form,
            text="Os tipos podem ser cadastrados e mantidos no painel ao lado.",
            justify="left",
            wraplength=560,
        ).grid(row=4, column=0, sticky="w", pady=(6, 0))

        form.columnconfigure(0, weight=1)

        list_frame = ttk.LabelFrame(document_panel, text="Documentos vinculados", padding=10)
        list_frame.grid(row=1, column=0, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            list_frame,
            columns=("nome", "recebimento", "tipo"),
            show="headings",
            selectmode="extended",
        )
        self.tree.heading("nome", text="Nome do documento")
        self.tree.heading("recebimento", text="Recebimento")
        self.tree.heading("tipo", text="Tipo")
        self.tree.column("nome", width=360)
        self.tree.column("recebimento", width=220)
        self.tree.column("tipo", width=180)
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self.load_selected_document)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        document_actions = ttk.Frame(list_frame)
        document_actions.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        ttk.Button(document_actions, text="Excluir selecionados", command=self.delete_selected_documents).pack(
            side="left"
        )

        type_container = ttk.Frame(type_panel)
        type_container.grid(row=0, column=0, sticky="nsew")
        type_container.columnconfigure(0, weight=1)
        type_container.rowconfigure(1, weight=1)

        type_editor = ttk.LabelFrame(type_container, text="Tipos de documento", padding=12)
        type_editor.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        type_editor.columnconfigure(0, weight=1)
        type_editor.columnconfigure(1, weight=1)

        ttk.Label(
            type_editor,
            text=(
                "Gerencie os tipos sem sair desta aba. Tipos vinculados a documentos continuam protegidos contra exclusao."
            ),
            justify="left",
            wraplength=320,
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        ttk.Label(type_editor, text="Nome do tipo").grid(row=1, column=0, columnspan=2, sticky="w")
        ttk.Entry(type_editor, textvariable=self.tipo_nome_var).grid(
            row=2, column=0, columnspan=2, sticky="ew", pady=(0, 8)
        )
        ttk.Label(type_editor, text="Ocorrencia").grid(row=3, column=0, columnspan=2, sticky="w")
        self.tipo_ocorrencia_combo = ttk.Combobox(
            type_editor,
            textvariable=self.tipo_ocorrencia_label_var,
            state="readonly",
            values=[label for _value, label in TYPE_OCCURRENCE_CHOICES],
        )
        self.tipo_ocorrencia_combo.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        self.type_save_button = ttk.Button(type_editor, text="Cadastrar tipo", command=self.save_tipo)
        self.type_save_button.grid(row=5, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(type_editor, text="Limpar", command=self.clear_tipo_form).grid(
            row=5, column=1, sticky="ew"
        )
        ttk.Button(type_editor, text="Usar no documento", command=self.apply_selected_type_to_document).grid(
            row=6, column=0, sticky="ew", padx=(0, 8), pady=(8, 0)
        )
        ttk.Button(type_editor, text="Excluir tipo selecionado", command=self.delete_tipo).grid(
            row=6, column=1, sticky="ew", pady=(8, 0)
        )
        ttk.Label(
            type_editor,
            text="Mensal: todos os meses. Trimestral: libera 01, 04, 07 e 10. Anual em janeiro: libera apenas janeiro.",
            justify="left",
            wraplength=320,
            foreground="#5A5A5A",
        ).grid(row=7, column=0, columnspan=2, sticky="w", pady=(8, 0))

        type_list = ttk.LabelFrame(type_container, text="Tipos cadastrados", padding=10)
        type_list.grid(row=1, column=0, sticky="nsew")
        type_list.columnconfigure(0, weight=1)
        type_list.rowconfigure(0, weight=1)

        self.tipo_tree = ttk.Treeview(
            type_list,
            columns=("nome", "ocorrencia"),
            show="headings",
            selectmode="browse",
            height=14,
        )
        self.tipo_tree.heading("nome", text="Tipos cadastrados")
        self.tipo_tree.heading("ocorrencia", text="Ocorrencia")
        self.tipo_tree.column("nome", width=210)
        self.tipo_tree.column("ocorrencia", width=120, anchor="center")
        self.tipo_tree.grid(row=0, column=0, sticky="nsew")
        self.tipo_tree.bind("<<TreeviewSelect>>", self.load_selected_tipo)
        self.tipo_tree.bind("<Double-1>", lambda _event: self.apply_selected_type_to_document())

        type_scrollbar = ttk.Scrollbar(type_list, orient="vertical", command=self.tipo_tree.yview)
        type_scrollbar.grid(row=0, column=1, sticky="ns")
        self.tipo_tree.configure(yscrollcommand=type_scrollbar.set)

    def refresh_data(self) -> None:
        self.refresh_type_options()
        self.company_selector.refresh_companies()
        self.refresh_document_list()

    def refresh_type_options(self) -> None:
        tipos = self.services.tipo_service.list_tipos()
        self.tipo_map = {tipo["nome_tipo"]: tipo["id"] for tipo in tipos}
        self.tipo_combo["values"] = list(self.tipo_map.keys())

        current_document_type = self.tipo_var.get()
        self.tipo_tree.delete(*self.tipo_tree.get_children())
        for tipo in tipos:
            self.tipo_tree.insert(
                "",
                "end",
                iid=str(tipo["id"]),
                values=(tipo["nome_tipo"], self._occurrence_label(tipo.get("regra_ocorrencia"))),
            )

        if current_document_type and current_document_type not in self.tipo_map:
            self.tipo_var.set("")

        if self.selected_tipo_id and self.tipo_tree.exists(str(self.selected_tipo_id)):
            self.tipo_tree.selection_set(str(self.selected_tipo_id))
            self.tipo_tree.focus(str(self.selected_tipo_id))
            self.tipo_tree.see(str(self.selected_tipo_id))
            self._populate_tipo_form(self.services.tipo_service.get_tipo(self.selected_tipo_id))
            self._refresh_document_name_suggestions()
            return

        self._clear_tipo_form_state(clear_selection=False)
        self._refresh_document_name_suggestions()

    def refresh_document_list(self) -> None:
        self.tree.delete(*self.tree.get_children())
        company_id = self.company_selector.get_selected_company_id()
        if not company_id:
            self.current_company_id = None
            self._clear_document_form(clear_selection=False)
            return

        for documento in self.services.documento_service.list_documentos_empresa(company_id):
            self.tree.insert(
                "",
                "end",
                iid=str(documento["id"]),
                values=(
                    documento["nome_documento"],
                    documento.get("meios_recebimento") or "-",
                    documento["nome_tipo"],
                ),
            )

        if self.selected_documento_id and self.tree.exists(str(self.selected_documento_id)):
            self.tree.selection_set(str(self.selected_documento_id))
            self.tree.focus(str(self.selected_documento_id))
            self.tree.see(str(self.selected_documento_id))

    def on_company_selected(self, company: dict) -> None:
        company_changed = self.current_company_id != company["id"]
        self.current_company_id = company["id"]
        if company_changed:
            self.clear_form()
        self.refresh_document_list()

    def _clear_company_context(self) -> None:
        self.current_company_id = None
        self.tree.delete(*self.tree.get_children())
        self._clear_document_form(clear_selection=False)
        self._refresh_document_name_suggestions()

    def clear_form(self) -> None:
        self._clear_document_form(clear_selection=True)

    def _clear_document_form(self, *, clear_selection: bool) -> None:
        self.selected_documento_id = None
        self.nome_var.set("")
        self.tipo_var.set("")
        self.delivery_field.clear()
        self.save_button.configure(text="Cadastrar documento")
        if clear_selection:
            selection = self.tree.selection()
            if selection:
                self.tree.selection_remove(*selection)
        self._refresh_document_name_suggestions()

    def load_selected_document(self, _event=None) -> None:
        selection = self.tree.selection()
        if len(selection) != 1:
            self.selected_documento_id = None
            self.nome_var.set("")
            self.tipo_var.set("")
            self.delivery_field.clear()
            self.save_button.configure(text="Cadastrar documento")
            return

        self.selected_documento_id = int(selection[0])
        documento = self.services.documento_service.get_documento(self.selected_documento_id)
        tipo = self.services.tipo_service.get_tipo(documento["tipo_documento_id"])
        self.nome_var.set(documento["nome_documento"])
        self.tipo_var.set(tipo["nome_tipo"])
        self.delivery_field.set_values(documento.get("meios_recebimento"))
        self.save_button.configure(text="Salvar alteracoes")
        self._refresh_document_name_suggestions()

    def _on_document_type_changed(self, _event=None) -> None:
        self._refresh_document_name_suggestions()

    def _on_document_name_typed(self, _event=None) -> None:
        self._refresh_document_name_suggestions()

    def _refresh_document_name_suggestions(self) -> None:
        tipo_id = self.tipo_map.get(self.tipo_var.get())
        search = self.nome_var.get().strip()
        suggestions = self.services.documento_service.list_document_name_suggestions(tipo_documento_id=tipo_id, search=search)
        self.nome_combo["values"] = suggestions

        if tipo_id:
            if suggestions:
                self.nome_sugestao_var.set(
                    f"Sugestoes do tipo selecionado: {len(suggestions)} nomenclaturas ja usadas no sistema."
                )
            else:
                self.nome_sugestao_var.set(
                    "Nenhuma nomenclatura encontrada para esse tipo ainda. Voce pode cadastrar uma nova."
                )
            return

        if search:
            if suggestions:
                self.nome_sugestao_var.set(
                    f"Sugestoes globais encontradas: {len(suggestions)} nomenclaturas semelhantes no sistema."
                )
            else:
                self.nome_sugestao_var.set(
                    "Nenhuma nomenclatura semelhante encontrada. Selecione um tipo para filtrar melhor."
                )
            return

        self.nome_sugestao_var.set("Selecione um tipo para reutilizar nomenclaturas ja cadastradas.")

    def save_document(self) -> None:
        company_id = self.company_selector.get_selected_company_id()
        if not company_id:
            messagebox.showwarning("Documentos", "Selecione uma empresa primeiro.", parent=self)
            return

        selection = self.tree.selection()
        if len(selection) > 1:
            messagebox.showwarning(
                "Documentos",
                "Selecione apenas um documento para editar ou limpe a selecao para cadastrar.",
                parent=self,
            )
            return

        tipo_id = self.tipo_map.get(self.tipo_var.get())
        if not tipo_id:
            messagebox.showwarning("Documentos", "Selecione um tipo valido.", parent=self)
            return

        try:
            if self.selected_documento_id:
                self.services.documento_service.update_documento(
                    self.selected_documento_id,
                    tipo_id,
                    self.nome_var.get(),
                    self.delivery_field.get_values(),
                )
                messagebox.showinfo("Documentos", "Documento atualizado com sucesso.", parent=self)
            else:
                self.services.documento_service.create_documento(
                    company_id,
                    tipo_id,
                    self.nome_var.get(),
                    self.delivery_field.get_values(),
                )
                messagebox.showinfo("Documentos", "Documento cadastrado com sucesso.", parent=self)
        except ValidationError as exc:
            messagebox.showerror("Documentos", str(exc), parent=self)
            return

        self.clear_form()
        self.on_data_changed()
        self.company_selector.set_company(company_id)

    def delete_selected_documents(self) -> None:
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Documentos", "Selecione um ou mais documentos para excluir.", parent=self)
            return

        if not messagebox.askyesno(
            "Excluir documentos",
            "Os documentos selecionados e os respectivos status mensais serao excluidos. Deseja continuar?",
            parent=self,
        ):
            return

        company_id = self.company_selector.get_selected_company_id()
        self.services.documento_service.delete_documentos([int(item) for item in selection])
        self.clear_form()
        self.on_data_changed()
        self.company_selector.set_company(company_id)
        messagebox.showinfo("Documentos", "Documentos excluidos com sucesso.", parent=self)

    def load_selected_tipo(self, _event=None) -> None:
        selection = self.tipo_tree.selection()
        if not selection:
            return

        tipo = self.services.tipo_service.get_tipo(int(selection[0]))
        self._populate_tipo_form(tipo)

    def _populate_tipo_form(self, tipo: dict) -> None:
        self.selected_tipo_id = tipo["id"]
        self.tipo_nome_var.set(tipo["nome_tipo"])
        self.tipo_ocorrencia_label_var.set(self._occurrence_label(tipo.get("regra_ocorrencia")))
        self.type_save_button.configure(text="Salvar alteracoes")

    def clear_tipo_form(self) -> None:
        self._clear_tipo_form_state(clear_selection=True)

    def _clear_tipo_form_state(self, *, clear_selection: bool) -> None:
        self.selected_tipo_id = None
        self.tipo_nome_var.set("")
        self.tipo_ocorrencia_label_var.set(self._occurrence_label(TYPE_OCCURRENCE_MENSAL))
        self.type_save_button.configure(text="Cadastrar tipo")
        if clear_selection:
            selection = self.tipo_tree.selection()
            if selection:
                self.tipo_tree.selection_remove(*selection)

    def apply_selected_type_to_document(self) -> None:
        if not self.selected_tipo_id:
            messagebox.showwarning("Tipos", "Selecione um tipo na lista.", parent=self)
            return

        self.tipo_var.set(self.tipo_nome_var.get())

    def save_tipo(self) -> None:
        try:
            if self.selected_tipo_id:
                previous_name = self.services.tipo_service.get_tipo(self.selected_tipo_id)["nome_tipo"]
                self.services.tipo_service.update_tipo(
                    self.selected_tipo_id,
                    self.tipo_nome_var.get(),
                    self._selected_occurrence_value(),
                )
                saved_tipo = self.services.tipo_service.get_tipo(self.selected_tipo_id)
                if self.tipo_var.get() == previous_name:
                    self.tipo_var.set(saved_tipo["nome_tipo"])
                messagebox.showinfo("Tipos", "Tipo atualizado com sucesso.", parent=self)
            else:
                self.selected_tipo_id = self.services.tipo_service.create_tipo(
                    self.tipo_nome_var.get(),
                    self._selected_occurrence_value(),
                )
                saved_tipo = self.services.tipo_service.get_tipo(self.selected_tipo_id)
                self.tipo_var.set(saved_tipo["nome_tipo"])
                messagebox.showinfo("Tipos", "Tipo cadastrado com sucesso.", parent=self)
        except ValidationError as exc:
            messagebox.showerror("Tipos", str(exc), parent=self)
            return

        self.on_data_changed()

    def delete_tipo(self) -> None:
        if not self.selected_tipo_id:
            messagebox.showwarning("Tipos", "Selecione um tipo na lista.", parent=self)
            return

        if not messagebox.askyesno("Excluir tipo", "Deseja excluir o tipo selecionado?", parent=self):
            return

        deleted_name = self.tipo_nome_var.get()
        try:
            self.services.tipo_service.delete_tipo(self.selected_tipo_id)
        except ValidationError as exc:
            messagebox.showerror("Tipos", str(exc), parent=self)
            return

        if self.tipo_var.get() == deleted_name:
            self.tipo_var.set("")

        self.clear_tipo_form()
        self.on_data_changed()
        messagebox.showinfo("Tipos", "Tipo excluido com sucesso.", parent=self)

    def _occurrence_label(self, occurrence_value: str | None) -> str:
        return self.occurrence_label_by_value.get(occurrence_value or TYPE_OCCURRENCE_MENSAL, "Mensal")

    def _selected_occurrence_value(self) -> str:
        label = self.tipo_ocorrencia_label_var.get().strip()
        return self.occurrence_value_by_label.get(label, TYPE_OCCURRENCE_MENSAL)
