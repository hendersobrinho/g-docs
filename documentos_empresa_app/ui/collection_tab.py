from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from documentos_empresa_app.services.collection_service import CollectionService
from documentos_empresa_app.ui.status_icons import set_button_icon
from documentos_empresa_app.utils.helpers import ValidationError, open_email_draft


class CollectionTab(ttk.Frame):
    FILTER_ALL = "Todas"
    FILTER_ALERT = "Prontas para alerta"

    def __init__(self, master, services, on_data_changed, on_open_control=None) -> None:
        super().__init__(master, padding=12)
        self.services = services
        self.on_data_changed = on_data_changed
        self.on_open_control = on_open_control
        self.current_items: list[dict] = []
        self.item_by_key: dict[str, dict] = {}

        self.search_var = tk.StringVar()
        self.phase_var = tk.StringVar(value=self.FILTER_ALL)
        self.active_only_var = tk.BooleanVar(value=True)
        self.summary_var = tk.StringVar(value="Clique em Atualizar para carregar a central de cobrancas.")
        self.global_cobranca_inicio_var = tk.StringVar()
        self.global_cobranca_fim_var = tk.StringVar()
        self.global_cobranca_alerta_var = tk.StringVar()
        self.global_config_mode = "view"

        self.phase_key_by_label = {
            self.FILTER_ALL: None,
            self.FILTER_ALERT: self.FILTER_ALERT,
            CollectionService.PHASE_LABELS[CollectionService.PHASE_EM_COBRANCA]: CollectionService.PHASE_EM_COBRANCA,
            CollectionService.PHASE_LABELS[CollectionService.PHASE_EM_ATRASO]: CollectionService.PHASE_EM_ATRASO,
        }

        self._build_layout()

    def _build_layout(self) -> None:
        global_frame = ttk.LabelFrame(self, text="Configuracao global de cobranca", padding=10)
        global_frame.pack(fill="x", pady=(0, 8))
        global_frame.columnconfigure(0, weight=1)
        global_frame.columnconfigure(1, weight=1)
        global_frame.columnconfigure(2, weight=1)

        ttk.Label(
            global_frame,
            text=(
                "Essa e a regra padrao do sistema. Todas as empresas sem configuracao propria "
                "na aba Empresas vao usar esses valores automaticamente."
            ),
            justify="left",
            wraplength=900,
        ).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 8))
        ttk.Label(global_frame, text="Dia inicial da cobranca").grid(row=1, column=0, sticky="w")
        self.global_cobranca_inicio_entry = ttk.Entry(
            global_frame,
            textvariable=self.global_cobranca_inicio_var,
            width=18,
        )
        self.global_cobranca_inicio_entry.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=(0, 10),
        )
        ttk.Label(global_frame, text="Dia final da cobranca").grid(row=1, column=1, sticky="w")
        self.global_cobranca_fim_entry = ttk.Entry(
            global_frame,
            textvariable=self.global_cobranca_fim_var,
            width=18,
        )
        self.global_cobranca_fim_entry.grid(
            row=2,
            column=1,
            sticky="ew",
            padx=(0, 10),
        )
        ttk.Label(global_frame, text="Dias para virar alerta").grid(row=1, column=2, sticky="w")
        self.global_cobranca_alerta_entry = ttk.Entry(
            global_frame,
            textvariable=self.global_cobranca_alerta_var,
            width=18,
        )
        self.global_cobranca_alerta_entry.grid(
            row=2,
            column=2,
            sticky="ew",
            padx=(0, 10),
        )
        config_actions = ttk.Frame(global_frame)
        config_actions.grid(row=2, column=3, sticky="e")
        self.edit_global_button = ttk.Button(
            config_actions,
            text="Editar",
            command=self.start_edit_global_collection_settings,
        )
        self.edit_global_button.pack(side="left")
        self.save_global_button = ttk.Button(
            config_actions,
            text="Salvar",
            command=self.save_global_collection_settings,
            style="Primary.TButton",
        )
        self.save_global_button.pack(side="left", padx=(8, 0))
        set_button_icon(self.save_global_button)
        self.cancel_global_button = ttk.Button(
            config_actions,
            text="Cancelar",
            command=self.cancel_edit_global_collection_settings,
        )
        self.cancel_global_button.pack(side="left", padx=(8, 0))

        filter_frame = ttk.LabelFrame(self, text="Central de cobrancas", padding=10)
        filter_frame.pack(fill="x", pady=(0, 8))
        filter_frame.columnconfigure(3, weight=1)

        ttk.Label(filter_frame, text="Fase").grid(row=0, column=0, sticky="w")
        phase_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.phase_var,
            state="readonly",
            width=22,
            values=[
                self.FILTER_ALL,
                self.FILTER_ALERT,
                CollectionService.PHASE_LABELS[CollectionService.PHASE_EM_COBRANCA],
                CollectionService.PHASE_LABELS[CollectionService.PHASE_EM_ATRASO],
            ],
        )
        phase_combo.grid(row=1, column=0, sticky="w", padx=(0, 10))
        phase_combo.bind("<<ComboboxSelected>>", lambda _event: self._populate_tree())

        ttk.Label(filter_frame, text="Buscar empresa").grid(row=0, column=1, sticky="w")
        search_entry = ttk.Entry(filter_frame, textvariable=self.search_var, width=30)
        search_entry.grid(row=1, column=1, sticky="ew", padx=(0, 10))
        search_entry.bind("<KeyRelease>", lambda _event: self._populate_tree())

        ttk.Checkbutton(
            filter_frame,
            text="Somente ativas",
            variable=self.active_only_var,
            command=self.load_queue,
        ).grid(row=1, column=2, sticky="w", padx=(0, 10))

        action_frame = ttk.Frame(filter_frame)
        action_frame.grid(row=1, column=3, sticky="e")
        ttk.Button(action_frame, text="Atualizar", command=self.load_queue).pack(side="left", padx=(0, 8))
        ttk.Button(action_frame, text="Limpar filtros", command=self.clear_filters).pack(side="left", padx=(0, 8))
        ttk.Button(action_frame, text="Preparar email", command=self.prepare_email).pack(side="left", padx=(0, 8))
        ttk.Button(action_frame, text="Copiar WhatsApp", command=self.copy_whatsapp).pack(side="left", padx=(0, 8))
        ttk.Button(action_frame, text="Abrir no Controle", command=self.open_selected_item).pack(side="left")

        ttk.Label(self, textvariable=self.summary_var).pack(fill="x", pady=(0, 8))

        list_frame = ttk.LabelFrame(self, text="Fila agrupada por empresa", padding=10)
        list_frame.pack(fill="both", expand=True)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            list_frame,
            columns=("empresa", "periodos", "fase", "docs", "inicio", "fim", "dias", "canal"),
            show="headings",
            selectmode="browse",
        )
        self.tree.heading("empresa", text="Empresa")
        self.tree.heading("periodos", text="Periodos")
        self.tree.heading("fase", text="Fase")
        self.tree.heading("docs", text="Docs")
        self.tree.heading("inicio", text="Inicio")
        self.tree.heading("fim", text="Fechamento")
        self.tree.heading("dias", text="Dias apos fim")
        self.tree.heading("canal", text="Canal sugerido")
        self.tree.column("empresa", width=320)
        self.tree.column("periodos", width=240, anchor="center")
        self.tree.column("fase", width=120, anchor="center")
        self.tree.column("docs", width=70, anchor="center")
        self.tree.column("inicio", width=95, anchor="center")
        self.tree.column("fim", width=95, anchor="center")
        self.tree.column("dias", width=110, anchor="center")
        self.tree.column("canal", width=120, anchor="center")
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<Double-1>", lambda _event: self.open_selected_item())

        scrollbar_y = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x = ttk.Scrollbar(list_frame, orient="horizontal", command=self.tree.xview)
        scrollbar_x.grid(row=1, column=0, sticky="ew")
        self.tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        detail_frame = ttk.LabelFrame(self, text="Periodos e documentos da cobranca selecionada", padding=10)
        detail_frame.pack(fill="both", expand=False)
        detail_frame.columnconfigure(0, weight=1)
        detail_frame.rowconfigure(0, weight=1)

        self.detail_list = tk.Listbox(detail_frame, height=7)
        self.detail_list.grid(row=0, column=0, sticky="nsew")
        self.detail_list.bind("<Double-1>", lambda _event: self.open_selected_item())
        detail_scrollbar = ttk.Scrollbar(detail_frame, orient="vertical", command=self.detail_list.yview)
        detail_scrollbar.grid(row=0, column=1, sticky="ns")
        self.detail_list.configure(yscrollcommand=detail_scrollbar.set)

        self.tree.tag_configure(CollectionService.PHASE_EM_COBRANCA, background="#FFF2CC")
        self.tree.tag_configure(CollectionService.PHASE_EM_ATRASO, background="#FAD4D4")
        self.tree.tag_configure("alert_ready", background="#F4B7B7")
        self.tree.bind("<<TreeviewSelect>>", lambda _event: self._populate_details())
        self._set_global_config_mode("view")

    def refresh_data(self) -> None:
        self._load_global_collection_settings()
        self.load_queue()

    def load_queue(self) -> None:
        view = self.services.collection_service.build_collection_queue(active_only=self.active_only_var.get())
        self.current_items = view["items"]
        self._populate_tree()

    def _load_global_collection_settings(self) -> None:
        settings = self.services.collection_service.get_global_settings()
        self.global_cobranca_inicio_var.set(str(settings["inicio_cobranca_dia"]))
        self.global_cobranca_fim_var.set(str(settings["encerramento_cobranca_dia"]))
        self.global_cobranca_alerta_var.set(str(settings["alerta_apos_dias"]))
        if self.global_config_mode != "edit":
            self._set_global_config_mode("view")

    def start_edit_global_collection_settings(self) -> None:
        self._set_global_config_mode("edit")

    def cancel_edit_global_collection_settings(self) -> None:
        self._load_global_collection_settings()
        self._set_global_config_mode("view")

    def save_global_collection_settings(self) -> None:
        try:
            self.services.collection_service.update_global_settings(
                self.global_cobranca_inicio_var.get(),
                self.global_cobranca_fim_var.get(),
                self.global_cobranca_alerta_var.get(),
            )
        except ValidationError as exc:
            messagebox.showerror("Cobrancas", str(exc), parent=self)
            return
        self._load_global_collection_settings()
        self.load_queue()
        if self.on_data_changed:
            self.on_data_changed()
        self._set_global_config_mode("view")
        messagebox.showinfo("Cobrancas", "Regra global de cobranca salva com sucesso.", parent=self)

    def _set_global_config_mode(self, mode: str) -> None:
        self.global_config_mode = mode
        editable = mode == "edit"
        entry_state = "normal" if editable else "disabled"
        self.global_cobranca_inicio_entry.configure(state=entry_state)
        self.global_cobranca_fim_entry.configure(state=entry_state)
        self.global_cobranca_alerta_entry.configure(state=entry_state)
        self.edit_global_button.configure(state="disabled" if editable else "normal")
        self.save_global_button.configure(state="normal" if editable else "disabled")
        self.cancel_global_button.configure(state="normal" if editable else "disabled")

    def _populate_tree(self) -> None:
        self.tree.delete(*self.tree.get_children())
        self.item_by_key = {}

        filtered_items = self._filtered_items()
        for item in filtered_items:
            row_key = self._item_key(item)
            self.item_by_key[row_key] = item
            tag = "alert_ready" if item["alert_ready"] else item["phase_key"]
            self.tree.insert(
                "",
                "end",
                iid=row_key,
                values=(
                    f'{item["codigo_empresa"]} - {item["nome_empresa"]}',
                    item["period_summary"],
                    item["phase_label"],
                    item["document_count"],
                    item["window_start"].strftime("%d/%m/%Y"),
                    item["window_end"].strftime("%d/%m/%Y"),
                    item["days_after_end"],
                    item["suggested_channel"],
                ),
                tags=(tag,),
            )

        self._update_summary(filtered_items)
        self._populate_details()

    def _filtered_items(self) -> list[dict]:
        search = self.search_var.get().strip().casefold()
        phase_filter = self.phase_key_by_label.get(self.phase_var.get())

        items: list[dict] = []
        for item in self.current_items:
            if phase_filter == self.FILTER_ALERT and not item["alert_ready"]:
                continue
            if phase_filter in {CollectionService.PHASE_EM_COBRANCA, CollectionService.PHASE_EM_ATRASO}:
                if item["phase_key"] != phase_filter:
                    continue

            company_text = f'{item["codigo_empresa"]} {item["nome_empresa"]}'.casefold()
            if search and search not in company_text:
                continue
            items.append(item)
        return items

    def _update_summary(self, filtered_items: list[dict]) -> None:
        total = len(self.current_items)
        visible = len(filtered_items)
        alert_ready = sum(1 for item in filtered_items if item["alert_ready"])
        overdue = sum(1 for item in filtered_items if item["phase_key"] == CollectionService.PHASE_EM_ATRASO)
        in_collection = sum(1 for item in filtered_items if item["phase_key"] == CollectionService.PHASE_EM_COBRANCA)
        self.summary_var.set(
            f"{visible} de {total} cobranca(s). "
            f"Em cobranca: {in_collection} | Em atraso: {overdue} | Prontas para alerta: {alert_ready}"
        )

    def _populate_details(self) -> None:
        self.detail_list.delete(0, "end")
        item = self._selected_item()
        if not item:
            return
        for period_item in item["period_items"]:
            phase_text = f'{period_item["periodo_label"]} | {period_item["phase_label"]}'
            self.detail_list.insert("end", phase_text)
            for document in period_item["documents"]:
                channel = ", ".join(document["meios_recebimento"]) if document["meios_recebimento"] else "Sem meio informado"
                self.detail_list.insert("end", f'  - {document["nome_documento"]} | {document["status"]} | {channel}')
            self.detail_list.insert("end", "")

    def clear_filters(self) -> None:
        self.search_var.set("")
        self.phase_var.set(self.FILTER_ALL)
        self._populate_tree()

    def _selected_item(self) -> dict | None:
        selection = self.tree.selection()
        if not selection:
            return None
        return self.item_by_key.get(selection[0])

    def prepare_email(self) -> None:
        item = self._selected_item()
        if not item:
            messagebox.showwarning("Cobrancas", "Selecione uma cobranca para preparar o email.", parent=self)
            return
        try:
            draft = self.services.collection_service.build_email_draft(item)
        except ValidationError as exc:
            messagebox.showwarning("Cobrancas", str(exc), parent=self)
            return

        try:
            handler_name = open_email_draft(draft["to"], draft["subject"], draft["body"])
        except ValidationError as exc:
            messagebox.showwarning("Cobrancas", str(exc), parent=self)
            return
        messagebox.showinfo(
            "Cobrancas",
            f'O cliente de email configurado no sistema foi aberto com a mensagem preenchida.\n\nHandler: {handler_name}',
            parent=self,
        )

    def copy_whatsapp(self) -> None:
        item = self._selected_item()
        if not item:
            messagebox.showwarning("Cobrancas", "Selecione uma cobranca para gerar a mensagem.", parent=self)
            return
        text = self.services.collection_service.build_whatsapp_message(item)
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo(
            "Cobrancas",
            "Mensagem copiada para a area de transferencia.",
            parent=self,
        )

    def open_selected_item(self) -> str | None:
        item = self._selected_item()
        if not item:
            messagebox.showwarning("Cobrancas", "Selecione uma cobranca para abrir no Controle.", parent=self)
            return "break"
        if not self.on_open_control:
            return "break"
        self.on_open_control(item["empresa_id"], item["primary_period_id"])
        return "break"

    @staticmethod
    def _item_key(item: dict) -> str:
        return str(item["empresa_id"])
