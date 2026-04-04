from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from documentos_empresa_app.utils.common import MAX_COMPANY_OBSERVATION_LENGTH
from documentos_empresa_app.utils.helpers import CompanySelector, ValidationError


class CadastroCompletoImportLayoutDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, import_service) -> None:
        super().__init__(parent.winfo_toplevel())
        self.parent = parent
        self.import_service = import_service

        self.title("Cadastro completo - Layout de importacao")
        self.transient(parent.winfo_toplevel())
        self.resizable(True, True)
        self.minsize(780, 400)

        self._build_layout()
        self.grab_set()
        self.after(10, self._center_on_parent)

    def _build_layout(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        ttk.Label(
            self,
            text=(
                "Use uma linha por documento. As quatro primeiras colunas identificam a empresa, "
                "depois vem nome do documento, meio de recebimento, tipo e observacao da empresa. "
                "As colunas de meses no final sao opcionais e aceitam OK para Recebido, P para "
                "Pendente, X para Nao cobrar e vazio para nao preencher nada. Para importar so a "
                "empresa, deixe as colunas de documento em branco. Para continuar a mesma empresa "
                "em linhas seguidas, voce pode deixar as quatro primeiras colunas em branco depois "
                "da primeira linha."
            ),
            justify="left",
            wraplength=760,
        ).grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 8))

        list_frame = ttk.LabelFrame(self, text="Estrutura esperada", padding=10)
        list_frame.grid(row=1, column=0, sticky="nsew", padx=12)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        tree = ttk.Treeview(
            list_frame,
            columns=("ordem", "campo", "obrigatorio", "exemplo"),
            show="headings",
            selectmode="none",
        )
        tree.heading("ordem", text="Ordem")
        tree.heading("campo", text="Coluna")
        tree.heading("obrigatorio", text="Obrigatorio")
        tree.heading("exemplo", text="Exemplo")
        tree.column("ordem", width=70, anchor="center")
        tree.column("campo", width=240)
        tree.column("obrigatorio", width=110, anchor="center")
        tree.column("exemplo", width=260)
        tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        tree.configure(yscrollcommand=scrollbar.set)

        layout = self.import_service.get_cadastro_completo_import_layout()
        for item in layout:
            tree.insert(
                "",
                "end",
                values=(
                    item["index"],
                    item["field"],
                    "Sim" if item["required"] else "Nao",
                    item["example"],
                ),
            )

        sample_values = [item["example"] for item in layout[:11]]
        sample_text = " | ".join(sample_values) + " | ..."
        ttk.Label(
            self,
            text=(
                "Exemplo de linha:\n"
                f"{sample_text}\n\n"
                "A primeira linha pode conter os cabecalhos acima. O sistema ignora esse cabecalho automaticamente."
            ),
            justify="left",
            wraplength=760,
        ).grid(row=2, column=0, sticky="ew", padx=12, pady=(12, 12))

    def _center_on_parent(self) -> None:
        self.update_idletasks()
        parent = self.parent.winfo_toplevel()
        x = parent.winfo_rootx() + max((parent.winfo_width() - self.winfo_width()) // 2, 0)
        y = parent.winfo_rooty() + max((parent.winfo_height() - self.winfo_height()) // 2, 0)
        self.geometry(f"+{x}+{y}")


class EmpresaTab(ttk.Frame):
    def __init__(self, master, services, on_data_changed) -> None:
        super().__init__(master, padding=12)
        self.services = services
        self.on_data_changed = on_data_changed
        self.selected_company_id: int | None = None
        self.selected_company: dict | None = None
        self.form_mode = "idle"
        self._selection_syncing = False

        self.codigo_var = tk.StringVar()
        self.nome_var = tk.StringVar()
        self.email_var = tk.StringVar()
        self.contato_var = tk.StringVar()
        self.info_codigo_var = tk.StringVar(value="-")
        self.info_nome_var = tk.StringVar(value="Nenhuma empresa consultada.")
        self.info_email_var = tk.StringVar(value="-")
        self.info_contato_var = tk.StringVar(value="-")
        self.info_observacao_var = tk.StringVar(value="-")
        self.info_situacao_var = tk.StringVar(value="Nenhuma empresa consultada.")
        self.observacao_counter_var = tk.StringVar(value=f"0/{MAX_COMPANY_OBSERVATION_LENGTH}")
        self.summary_value_labels: list[ttk.Label] = []
        self.summary_status_label: ttk.Label | None = None

        self._configure_form_styles()
        self._build_layout()

    def _configure_form_styles(self) -> None:
        style = ttk.Style(self)
        style.map(
            "CompanyForm.TEntry",
            fieldbackground=[("disabled", "#F3F3F3"), ("!disabled", "#FFFFFF")],
            foreground=[("disabled", "#6A6A6A"), ("!disabled", "#000000")],
            bordercolor=[("disabled", "#D0D0D0"), ("!disabled", "#B8B8B8")],
        )

    def _build_layout(self) -> None:
        self.columnconfigure(0, weight=1)
        consultation = ttk.LabelFrame(self, text="Detalhes do cadastro da empresa", padding=12)
        consultation.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        consultation.columnconfigure(0, weight=1)

        self.company_selector = CompanySelector(
            consultation,
            self.services.empresa_service,
            active_only=False,
            on_selected=self.on_company_selected,
            on_cleared=self._on_company_selector_cleared,
            title="Localizar empresa para consultar",
        )
        self.company_selector.grid(row=0, column=0, sticky="ew")

        ttk.Separator(consultation, orient="horizontal").grid(row=1, column=0, sticky="ew", pady=12)

        summary = ttk.Frame(consultation)
        summary.grid(row=2, column=0, sticky="nsew")
        summary.columnconfigure(1, weight=1)
        summary.bind("<Configure>", self._update_summary_wraplength)

        self.summary_status_label = ttk.Label(summary, textvariable=self.info_situacao_var, justify="left")
        self.summary_status_label.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        self._build_summary_row(summary, 1, "Codigo", self.info_codigo_var)
        self._build_summary_row(summary, 2, "Nome", self.info_nome_var)
        self._build_summary_row(summary, 3, "Email", self.info_email_var)
        self._build_summary_row(summary, 4, "Contato", self.info_contato_var)
        self._build_summary_row(summary, 5, "Observacao", self.info_observacao_var)

        summary_actions = ttk.Frame(summary)
        summary_actions.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        summary_actions.columnconfigure(0, weight=1)
        summary_actions.columnconfigure(1, weight=1)
        summary_actions.columnconfigure(2, weight=1)

        self.edit_button = ttk.Button(summary_actions, text="Editar cadastro", command=self.start_edit_company)
        self.edit_button.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.toggle_active_button = ttk.Button(summary_actions, command=self.toggle_selected_active)
        self.toggle_active_button.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        self.delete_button = ttk.Button(summary_actions, text="Excluir", command=self.delete_company)
        self.delete_button.grid(row=0, column=2, sticky="ew")

        form = ttk.LabelFrame(self, text="Cadastro e manutencao de empresas", padding=12)
        form.grid(row=1, column=0, sticky="ew")

        identity_row = ttk.Frame(form)
        identity_row.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        identity_row.columnconfigure(1, weight=1)

        ttk.Label(identity_row, text="Codigo da empresa").grid(row=0, column=0, sticky="w")
        self.codigo_entry = ttk.Entry(identity_row, textvariable=self.codigo_var, width=18, style="CompanyForm.TEntry")
        self.codigo_entry.grid(row=1, column=0, sticky="ew", padx=(0, 10))

        ttk.Label(identity_row, text="Nome da empresa").grid(row=0, column=1, sticky="w")
        self.nome_entry = ttk.Entry(identity_row, textvariable=self.nome_var, style="CompanyForm.TEntry")
        self.nome_entry.grid(row=1, column=1, sticky="ew")

        contact_row = ttk.Frame(form)
        contact_row.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        contact_row.columnconfigure(0, weight=1)
        contact_row.columnconfigure(1, weight=1)

        ttk.Label(contact_row, text="Email para contato (opcional)").grid(row=0, column=0, sticky="w")
        self.email_entry = ttk.Entry(contact_row, textvariable=self.email_var, style="CompanyForm.TEntry")
        self.email_entry.grid(row=1, column=0, sticky="ew", padx=(0, 10))

        ttk.Label(contact_row, text="Nome de contato (opcional)").grid(row=0, column=1, sticky="w")
        self.contato_entry = ttk.Entry(contact_row, textvariable=self.contato_var, style="CompanyForm.TEntry")
        self.contato_entry.grid(row=1, column=1, sticky="ew")

        observacao_row = ttk.Frame(form)
        observacao_row.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        observacao_row.columnconfigure(0, weight=1)

        ttk.Label(
            observacao_row,
            text=f"Observacao livre (opcional, max {MAX_COMPANY_OBSERVATION_LENGTH} caracteres)",
        ).grid(row=0, column=0, sticky="w")
        self.observacao_text = tk.Text(observacao_row, height=4, wrap="word")
        self.observacao_text.grid(row=1, column=0, sticky="ew")
        self.observacao_text.bind("<<Modified>>", self._handle_observacao_modified)
        ttk.Label(observacao_row, textvariable=self.observacao_counter_var).grid(
            row=2, column=0, sticky="e", pady=(4, 0)
        )

        action_row = ttk.Frame(form)
        action_row.grid(row=3, column=0, sticky="ew")
        action_row.columnconfigure(0, weight=1)
        action_row.columnconfigure(1, weight=1)
        action_row.columnconfigure(2, weight=1)

        self.new_button = ttk.Button(action_row, text="Novo cadastro", command=self.start_new_company)
        self.new_button.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.save_button = ttk.Button(action_row, text="Salvar", command=self.save_company)
        self.save_button.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        self.cancel_button = ttk.Button(action_row, text="Cancelar", command=self.cancel_company_edit)
        self.cancel_button.grid(row=0, column=2, sticky="ew")

        import_row = ttk.Frame(form)
        import_row.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        import_row.columnconfigure(1, weight=1)

        ttk.Label(import_row, text="Importacao completa").grid(row=0, column=0, sticky="w", padx=(0, 10))
        ttk.Button(
            import_row,
            text="Importar planilha",
            command=self.import_full_registrations,
        ).grid(row=0, column=1, sticky="w")

        import_menu_button = ttk.Menubutton(import_row, text="Layout e modelo")
        import_menu = tk.Menu(import_menu_button, tearoff=False)
        import_menu.add_command(label="Ver layout", command=self.show_complete_import_layout)
        import_menu.add_command(label="Baixar modelo", command=self.download_complete_import_template)
        import_menu_button["menu"] = import_menu
        import_menu_button.grid(row=0, column=2, sticky="e")

        form.columnconfigure(0, weight=1)
        self._set_form_mode("idle")

    def _build_summary_row(self, parent: ttk.LabelFrame, row: int, label: str, variable: tk.StringVar) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="nw", padx=(0, 10), pady=(0, 6))
        value_label = ttk.Label(
            parent,
            textvariable=variable,
            justify="left",
            wraplength=360,
        )
        value_label.grid(row=row, column=1, sticky="ew", pady=(0, 6))
        self.summary_value_labels.append(value_label)

    def _update_summary_wraplength(self, event=None) -> None:
        width = max((event.width if event is not None else 360) - 120, 180)
        if self.summary_status_label is not None:
            self.summary_status_label.configure(wraplength=max(width + 80, 220))
        for label in self.summary_value_labels:
            label.configure(wraplength=width)

    def refresh_data(self) -> None:
        self.company_selector.refresh_companies()

    def on_company_selected(self, company: dict) -> None:
        self._sync_company_selection(company, sync_selector=False)

    def _on_company_selector_cleared(self) -> None:
        self._clear_current_company(sync_selector=False)

    def _sync_company_selection(self, company: dict, *, sync_selector: bool = False) -> None:
        self._populate_company(company)
        if self._selection_syncing:
            return

        self._selection_syncing = True
        try:
            if sync_selector:
                self.company_selector.set_company(company["id"])
        finally:
            self._selection_syncing = False

    def _populate_company(self, company: dict) -> None:
        self.selected_company = company
        self.selected_company_id = company["id"]
        self.codigo_var.set(str(company["codigo_empresa"]))
        self.nome_var.set(company["nome_empresa"])
        self.email_var.set(company.get("email_contato") or "")
        self.contato_var.set(company.get("nome_contato") or "")
        self._set_observacao_text(company.get("observacao"))
        self._update_company_summary(company)
        self._set_form_mode("view")

    def clear_form(self) -> None:
        self._clear_current_company(sync_selector=True)

    def _clear_current_company(self, *, sync_selector: bool = False) -> None:
        self.selected_company = None
        self.selected_company_id = None
        self.codigo_var.set("")
        self.nome_var.set("")
        self.email_var.set("")
        self.contato_var.set("")
        self._set_observacao_text("")
        self._update_company_summary(None)
        self._set_form_mode("idle")

        if self._selection_syncing:
            return

        self._selection_syncing = True
        try:
            if sync_selector:
                self.company_selector.clear_selection()
        finally:
            self._selection_syncing = False

    def _update_company_summary(self, company: dict | None) -> None:
        if company is None:
            self.info_codigo_var.set("-")
            self.info_nome_var.set("Nenhuma empresa consultada.")
            self.info_email_var.set("-")
            self.info_contato_var.set("-")
            self.info_observacao_var.set("-")
            self.info_situacao_var.set("Nenhuma empresa consultada.")
            return

        self.info_codigo_var.set(str(company["codigo_empresa"]))
        self.info_nome_var.set(company["nome_empresa"])
        self.info_email_var.set(company.get("email_contato") or "-")
        self.info_contato_var.set(company.get("nome_contato") or "-")
        self.info_observacao_var.set(company.get("observacao") or "-")
        self.info_situacao_var.set("Empresa ativa." if company["ativa"] else "Empresa inativa.")

    def _get_observacao_text(self) -> str:
        return self.observacao_text.get("1.0", "end-1c")

    def _set_observacao_text(self, value: str | None) -> None:
        previous_state = str(self.observacao_text.cget("state"))
        if previous_state == "disabled":
            self.observacao_text.configure(state="normal")
        self.observacao_text.delete("1.0", "end")
        normalized_value = str(value or "")[:MAX_COMPANY_OBSERVATION_LENGTH]
        if normalized_value:
            self.observacao_text.insert("1.0", normalized_value)
        self._update_observacao_counter()
        self.observacao_text.edit_modified(False)
        if previous_state == "disabled":
            self.observacao_text.configure(state="disabled")

    def _apply_observacao_visual_state(self, editable: bool) -> None:
        self.observacao_text.configure(
            bg="#FFFFFF" if editable else "#F3F3F3",
            fg="#000000" if editable else "#6A6A6A",
            insertbackground="#000000",
        )

    def _update_observacao_counter(self) -> None:
        self.observacao_counter_var.set(
            f"{len(self._get_observacao_text())}/{MAX_COMPANY_OBSERVATION_LENGTH}"
        )

    def _handle_observacao_modified(self, _event=None) -> None:
        current_text = self._get_observacao_text()
        if len(current_text) > MAX_COMPANY_OBSERVATION_LENGTH:
            self.observacao_text.delete("1.0", "end")
            self.observacao_text.insert("1.0", current_text[:MAX_COMPANY_OBSERVATION_LENGTH])
            self.bell()
        self._update_observacao_counter()
        self.observacao_text.edit_modified(False)

    def save_company(self) -> None:
        if self.form_mode not in {"new", "edit"}:
            messagebox.showwarning("Empresas", "Clique em Novo ou Editar para habilitar o cadastro.", parent=self)
            return

        target_company_id = self.selected_company_id
        try:
            if self.form_mode == "edit" and self.selected_company_id:
                self.services.empresa_service.update_empresa(
                    self.selected_company_id,
                    self.nome_var.get(),
                    self.email_var.get(),
                    self.contato_var.get(),
                    self._get_observacao_text(),
                )
                messagebox.showinfo("Empresas", "Empresa atualizada com sucesso.", parent=self)
            else:
                target_company_id = self.services.empresa_service.create_empresa(
                    self.codigo_var.get(),
                    self.nome_var.get(),
                    self.email_var.get(),
                    self.contato_var.get(),
                    self._get_observacao_text(),
                )
                messagebox.showinfo("Empresas", "Empresa cadastrada com sucesso.", parent=self)
        except ValidationError as exc:
            messagebox.showerror("Empresas", str(exc), parent=self)
            return

        self.on_data_changed()
        if target_company_id:
            self.company_selector.set_company(target_company_id)
        else:
            self.clear_form()

    def toggle_selected_active(self) -> None:
        if not self.selected_company_id:
            messagebox.showwarning("Empresas", "Selecione uma empresa para continuar.", parent=self)
            return

        active = not bool(self.selected_company and self.selected_company.get("ativa"))
        self.services.empresa_service.set_empresa_ativa(self.selected_company_id, active)
        estado = "reativada" if active else "inativada"
        messagebox.showinfo("Empresas", f"Empresa {estado} com sucesso.", parent=self)
        self.on_data_changed()
        if self.selected_company_id:
            self.company_selector.set_company(self.selected_company_id)

    def delete_company(self) -> None:
        if not self.selected_company_id:
            messagebox.showwarning("Empresas", "Selecione uma empresa para continuar.", parent=self)
            return

        if not messagebox.askyesno(
            "Excluir empresa",
            "Deseja excluir a empresa selecionada? Os documentos e status mensais vinculados tambem serao apagados.",
            parent=self,
        ):
            return

        self.services.empresa_service.delete_empresa(self.selected_company_id)
        self.clear_form()
        self.on_data_changed()
        messagebox.showinfo("Empresas", "Empresa excluida com sucesso.", parent=self)

    def start_new_company(self) -> None:
        self.clear_form()
        self._set_form_mode("new")

    def start_edit_company(self) -> None:
        if not self.selected_company_id:
            messagebox.showwarning("Empresas", "Selecione uma empresa para editar.", parent=self)
            return

        company = self.services.empresa_service.get_empresa(self.selected_company_id)
        self._populate_company(company)
        self._set_form_mode("edit")

    def cancel_company_edit(self) -> None:
        if self.selected_company_id:
            company = self.services.empresa_service.get_empresa(self.selected_company_id)
            self._populate_company(company)
            return
        self.clear_form()

    def _set_form_mode(self, mode: str) -> None:
        self.form_mode = mode
        editable = mode in {"new", "edit"}
        has_selection = self.selected_company_id is not None

        self.codigo_entry.configure(state="normal" if mode == "new" else "disabled")
        self.nome_entry.configure(state="normal" if editable else "disabled")
        self.email_entry.configure(state="normal" if editable else "disabled")
        self.contato_entry.configure(state="normal" if editable else "disabled")
        self.observacao_text.configure(state="normal" if editable else "disabled")
        self._apply_observacao_visual_state(editable)
        self.save_button.configure(state="normal" if editable else "disabled")
        self.cancel_button.configure(state="normal" if editable else "disabled")
        self.new_button.configure(state="disabled" if editable else "normal")
        self.edit_button.configure(state="normal" if has_selection and not editable else "disabled")
        self.delete_button.configure(state="normal" if has_selection and not editable else "disabled")
        self._update_company_action_buttons()

    def _update_company_action_buttons(self) -> None:
        has_selection = self.selected_company_id is not None
        editable = self.form_mode in {"new", "edit"}
        self.edit_button.configure(state="normal" if has_selection and not editable else "disabled")
        self.delete_button.configure(state="normal" if has_selection and not editable else "disabled")

        if not has_selection:
            self.toggle_active_button.configure(text="Inativar", state="disabled")
            return

        is_active = bool(self.selected_company and self.selected_company.get("ativa"))
        self.toggle_active_button.configure(
            text="Inativar" if is_active else "Reativar",
            state="normal" if not editable else "disabled",
        )

    def show_complete_import_layout(self) -> None:
        dialog = CadastroCompletoImportLayoutDialog(self, self.services.import_service)
        self.wait_window(dialog)

    def import_full_registrations(self) -> None:
        file_path = filedialog.askopenfilename(
            parent=self,
            title="Selecione o arquivo Excel do cadastro completo",
            filetypes=[("Arquivos Excel", "*.xlsx *.xlsm"), ("Todos os arquivos", "*.*")],
        )
        if not file_path:
            return

        try:
            result = self.services.import_service.import_cadastros_completos(file_path)
        except ValidationError as exc:
            messagebox.showerror("Importacao de cadastro completo", str(exc), parent=self)
            return

        self.on_data_changed()
        summary = [
            f'Linhas processadas: {result["processed_rows"]}',
            f'Empresas criadas: {result["companies_created"]}',
            f'Empresas atualizadas: {result["companies_updated"]}',
            f'Empresas reutilizadas: {result["companies_reused"]}',
            f'Tipos criados: {result["types_created"]}',
            f'Documentos importados: {result["documents_imported"]}',
            f'Status importados: {result["statuses_imported"]}',
            f'Linhas com falha: {result["failed"]}',
        ]
        if result["errors"]:
            summary.append("")
            summary.append("Erros encontrados:")
            summary.extend(result["errors"][:10])
        messagebox.showinfo("Importacao de cadastro completo", "\n".join(summary), parent=self)

    def download_complete_import_template(self) -> None:
        file_path = filedialog.asksaveasfilename(
            parent=self,
            title="Salvar modelo de importacao completa",
            defaultextension=".xlsx",
            initialfile="modelo_importacao_cadastro_completo.xlsx",
            filetypes=[("Planilha Excel", "*.xlsx")],
        )
        if not file_path:
            return

        try:
            self.services.import_service.export_cadastro_completo_template(file_path)
        except ValidationError as exc:
            messagebox.showerror("Empresas", str(exc), parent=self)
            return

        messagebox.showinfo(
            "Empresas",
            f"Modelo salvo com sucesso em:\n{file_path}",
            parent=self,
        )
