from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from documentos_empresa_app.ui.document_name_field import DocumentNameManagerDialog
from documentos_empresa_app.ui.document_type_manager_dialog import DocumentTypeManagerDialog
from documentos_empresa_app.ui.delivery_methods_field import DeliveryMethodsField
from documentos_empresa_app.utils.helpers import CompanySelector, ValidationError


class DocumentoTab(ttk.Frame):
    def __init__(self, master, services, on_data_changed) -> None:
        super().__init__(master, padding=12)
        self.services = services
        self.on_data_changed = on_data_changed
        self.current_company_id: int | None = None
        self.selected_documento_id: int | None = None
        self.document_form_mode = "idle"

        self.nome_var = tk.StringVar()
        self.tipo_var = tk.StringVar()
        self.nome_sugestao_var = tk.StringVar(value="Use ... para manter os nomes padrao sugeridos pelo sistema.")
        self.tipo_map: dict[str, int] = {}

        self._build_layout()

    def _build_layout(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        self.company_selector = CompanySelector(
            self,
            self.services.empresa_service,
            active_only=False,
            on_selected=self.on_company_selected,
            on_cleared=self._clear_company_context,
        )
        self.company_selector.grid(row=0, column=0, sticky="ew", pady=(0, 12))

        form = ttk.LabelFrame(self, text="Cadastro e manutencao de documentos", padding=12)
        form.grid(row=1, column=0, sticky="ew", pady=(0, 12))

        field_row = ttk.Frame(form)
        field_row.grid(row=0, column=0, sticky="ew")
        field_row.columnconfigure(0, weight=2)
        field_row.columnconfigure(1, weight=1)

        ttk.Label(field_row, text="Nome do documento").grid(row=0, column=0, sticky="w")
        name_input = ttk.Frame(field_row)
        name_input.grid(row=1, column=0, sticky="ew", padx=(0, 10))
        name_input.columnconfigure(0, weight=1)

        self.nome_combo = ttk.Combobox(name_input, textvariable=self.nome_var)
        self.nome_combo.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.nome_combo.bind("<KeyRelease>", self._on_document_name_typed)
        self.nome_combo.bind("<<ComboboxSelected>>", lambda _event: self._refresh_document_name_suggestions())
        self.document_name_button = ttk.Button(name_input, text="...", width=3, command=self.open_document_name_manager)
        self.document_name_button.grid(
            row=0, column=1, sticky="ew"
        )

        ttk.Label(field_row, text="Tipo do documento").grid(row=0, column=1, sticky="w")
        type_input = ttk.Frame(field_row)
        type_input.grid(row=1, column=1, sticky="ew")
        type_input.columnconfigure(0, weight=1)

        self.tipo_combo = ttk.Combobox(type_input, textvariable=self.tipo_var, state="readonly")
        self.tipo_combo.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.tipo_combo.bind("<<ComboboxSelected>>", self._on_document_type_changed)
        self.type_manager_button = ttk.Button(type_input, text="...", width=3, command=self.open_type_manager)
        self.type_manager_button.grid(row=0, column=1, sticky="ew")

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
        action_row.columnconfigure(2, weight=1)
        action_row.columnconfigure(3, weight=1)

        self.new_button = ttk.Button(action_row, text="Novo", command=self.start_new_document)
        self.new_button.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.edit_button = ttk.Button(action_row, text="Editar", command=self.start_edit_document)
        self.edit_button.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        self.save_button = ttk.Button(action_row, text="Salvar", command=self.save_document)
        self.save_button.grid(row=0, column=2, sticky="ew", padx=(0, 8))
        self.cancel_button = ttk.Button(action_row, text="Cancelar", command=self.cancel_document_edit)
        self.cancel_button.grid(row=0, column=3, sticky="ew")

        form.columnconfigure(0, weight=1)

        list_frame = ttk.LabelFrame(self, text="Documentos vinculados", padding=10)
        list_frame.grid(row=2, column=0, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            list_frame,
            columns=("nome", "recebimento", "tipo"),
            show="headings",
            selectmode="extended",
            height=20,
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
        self.delete_documents_button = ttk.Button(document_actions, text="Excluir selecionados", command=self.delete_selected_documents)
        self.delete_documents_button.pack(
            side="left"
        )
        self._set_document_form_mode("idle")

    def refresh_data(self) -> None:
        self.refresh_type_options()
        self.company_selector.refresh_companies()
        self.refresh_document_list()

    def refresh_type_options(self) -> None:
        current_type_id = self.tipo_map.get(self.tipo_var.get())
        tipos = self.services.tipo_service.list_tipos()
        self.tipo_map = {tipo["nome_tipo"]: tipo["id"] for tipo in tipos}
        self.tipo_combo["values"] = list(self.tipo_map.keys())

        if current_type_id:
            updated_type = next((tipo for tipo in tipos if tipo["id"] == current_type_id), None)
            if updated_type:
                self.tipo_var.set(updated_type["nome_tipo"])
            else:
                self.tipo_var.set("")
        elif self.tipo_var.get() and self.tipo_var.get() not in self.tipo_map:
            self.tipo_var.set("")

        self._refresh_document_name_suggestions()

    def refresh_document_list(self) -> None:
        self.tree.delete(*self.tree.get_children())
        company_id = self.company_selector.get_selected_company_id()
        if not company_id:
            self.current_company_id = None
            self._reset_document_form(clear_selection=False)
            self._set_document_form_mode("idle")
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
            self.load_selected_document()
            return

        self._reset_document_form(clear_selection=False)
        self._set_document_form_mode("idle")

    def on_company_selected(self, company: dict) -> None:
        company_changed = self.current_company_id != company["id"]
        self.current_company_id = company["id"]
        if company_changed:
            self._reset_document_form(clear_selection=True)
        self.refresh_document_list()
        self._set_document_form_mode("idle")

    def _clear_company_context(self) -> None:
        self.current_company_id = None
        self.tree.delete(*self.tree.get_children())
        self._reset_document_form(clear_selection=False)
        self._refresh_document_name_suggestions()
        self._set_document_form_mode("idle")

    def clear_form(self) -> None:
        self._reset_document_form(clear_selection=True)
        self._set_document_form_mode("idle")

    def _reset_document_form(self, *, clear_selection: bool) -> None:
        self.selected_documento_id = None
        self.nome_var.set("")
        self.tipo_var.set("")
        self.delivery_field.clear()
        if clear_selection:
            selection = self.tree.selection()
            if selection:
                self.tree.selection_remove(*selection)
        self._refresh_document_name_suggestions()
        self._update_document_action_buttons()

    def load_selected_document(self, _event=None) -> None:
        selection = self.tree.selection()
        if len(selection) != 1:
            self.selected_documento_id = None
            self._reset_document_form(clear_selection=False)
            self._set_document_form_mode("idle")
            return

        self.selected_documento_id = int(selection[0])
        documento = self.services.documento_service.get_documento(self.selected_documento_id)
        tipo = self.services.tipo_service.get_tipo(documento["tipo_documento_id"])
        self.nome_var.set(documento["nome_documento"])
        self.tipo_var.set(tipo["nome_tipo"])
        self.delivery_field.set_values(documento.get("meios_recebimento"))
        self._refresh_document_name_suggestions()
        self._set_document_form_mode("view")

    def _on_document_type_changed(self, _event=None) -> None:
        self._refresh_document_name_suggestions()

    def _on_document_name_typed(self, _event=None) -> None:
        self._refresh_document_name_suggestions()

    def open_document_name_manager(self) -> None:
        dialog = DocumentNameManagerDialog(
            self,
            self.services.documento_service,
            self.services.tipo_service,
            "Documentos",
            initial_tipo_id=self.tipo_map.get(self.tipo_var.get()),
        )
        self.wait_window(dialog)
        self._refresh_document_name_suggestions()

    def open_type_manager(self) -> None:
        dialog = DocumentTypeManagerDialog(
            self,
            self.services.tipo_service,
            "Documentos",
            initial_tipo_id=self.tipo_map.get(self.tipo_var.get()),
            allow_apply_to_document=self.document_form_mode in {"new", "edit"},
        )
        self.wait_window(dialog)

        self.refresh_type_options()
        if dialog.applied_type_id:
            try:
                self.tipo_var.set(self.services.tipo_service.get_tipo(dialog.applied_type_id)["nome_tipo"])
            except ValidationError:
                self.tipo_var.set("")

        if dialog.data_changed and self.document_form_mode not in {"new", "edit"}:
            self.refresh_document_list()

        self._refresh_document_name_suggestions()

    def start_new_document(self) -> None:
        if not self.current_company_id:
            messagebox.showwarning("Documentos", "Selecione uma empresa primeiro.", parent=self)
            return
        self._reset_document_form(clear_selection=True)
        self._set_document_form_mode("new")

    def start_edit_document(self) -> None:
        if not self.selected_documento_id:
            messagebox.showwarning("Documentos", "Selecione um documento para editar.", parent=self)
            return
        self._set_document_form_mode("edit")

    def cancel_document_edit(self) -> None:
        if self.selected_documento_id and self.tree.exists(str(self.selected_documento_id)):
            self.tree.selection_set(str(self.selected_documento_id))
            self.load_selected_document()
            return
        self._reset_document_form(clear_selection=True)
        self._set_document_form_mode("idle")

    def _refresh_document_name_suggestions(self) -> None:
        tipo_id = self.tipo_map.get(self.tipo_var.get())
        search = self.nome_var.get().strip()
        suggestions = self.services.documento_service.list_document_name_suggestions(tipo_documento_id=tipo_id, search=search)
        self.nome_combo["values"] = suggestions

        if tipo_id:
            if suggestions:
                self.nome_sugestao_var.set(
                    f"Sugestoes padrao do tipo selecionado: {len(suggestions)} nome(s) cadastrados no sistema."
                )
            else:
                self.nome_sugestao_var.set(
                    "Nenhum nome padrao cadastrado para esse tipo ainda. Use ... para incluir novos padroes."
                )
            return

        if search:
            if suggestions:
                self.nome_sugestao_var.set(
                    f"Sugestoes padrao encontradas: {len(suggestions)} nome(s) semelhantes cadastrados no sistema."
                )
            else:
                self.nome_sugestao_var.set(
                    "Nenhum nome padrao semelhante encontrado. Selecione um tipo ou use ... para cadastrar."
                )
            return

        self.nome_sugestao_var.set("Use ... para manter os nomes padrao sugeridos pelo sistema.")

    def save_document(self) -> None:
        if self.document_form_mode not in {"new", "edit"}:
            messagebox.showwarning("Documentos", "Clique em Novo ou Editar para habilitar alteracoes.", parent=self)
            return

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

        target_document_id: int | None = self.selected_documento_id
        try:
            if self.document_form_mode == "edit" and self.selected_documento_id:
                self.services.documento_service.update_documento(
                    self.selected_documento_id,
                    tipo_id,
                    self.nome_var.get(),
                    self.delivery_field.get_values(),
                )
                target_document_id = self.selected_documento_id
                messagebox.showinfo("Documentos", "Documento atualizado com sucesso.", parent=self)
            else:
                target_document_id = self.services.documento_service.create_documento(
                    company_id,
                    tipo_id,
                    self.nome_var.get(),
                    self.delivery_field.get_values(),
                )
                messagebox.showinfo("Documentos", "Documento cadastrado com sucesso.", parent=self)
        except ValidationError as exc:
            messagebox.showerror("Documentos", str(exc), parent=self)
            return

        self.selected_documento_id = target_document_id
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

    def _set_document_form_mode(self, mode: str) -> None:
        self.document_form_mode = mode
        editable = mode in {"new", "edit"} and bool(self.current_company_id)

        self.nome_combo.configure(state="normal" if editable else "disabled")
        self.document_name_button.configure(state="normal" if editable else "disabled")
        self.tipo_combo.configure(state="readonly" if editable else "disabled")
        self.type_manager_button.configure(state="normal")
        self.delivery_field.set_editable(editable)
        self.save_button.configure(state="normal" if editable else "disabled")
        self.cancel_button.configure(state="normal" if editable else "disabled")
        self._update_document_action_buttons()

    def _update_document_action_buttons(self) -> None:
        has_company = bool(self.current_company_id)
        is_editing = self.document_form_mode in {"new", "edit"}
        has_single_selection = len(self.tree.selection()) == 1 and self.selected_documento_id is not None
        has_any_selection = bool(self.tree.selection())

        self.new_button.configure(state="normal" if has_company and not is_editing else "disabled")
        self.edit_button.configure(state="normal" if has_single_selection and not is_editing else "disabled")
        self.delete_documents_button.configure(state="normal" if has_any_selection and not is_editing else "disabled")
