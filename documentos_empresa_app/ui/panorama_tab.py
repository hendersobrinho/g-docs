from __future__ import annotations

from datetime import datetime
import re
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from documentos_empresa_app.services.collection_service import CollectionService
from documentos_empresa_app.services.panorama_service import PanoramaService
from documentos_empresa_app.ui.status_icons import get_status_icon, set_button_icon
from documentos_empresa_app.ui.styles import configure_app_style
from documentos_empresa_app.utils.common import MONTH_NAMES
from documentos_empresa_app.utils.helpers import CompanyMultiSelectDialog, ValidationError, open_email_draft
from documentos_empresa_app.utils.resources import apply_window_icon


class PanoramaTab(ttk.Frame):
    ALL_SITUATIONS = "Todas"
    WORK_QUEUE = "Fila de trabalho"
    COLLECTION_ALL = "Todas"
    COLLECTION_UP_TO_DATE = "Em dia"
    FILTER_ALL_LABEL = "Todos"
    COLUMN_KEYS = (
        "codigo",
        "empresa",
        "situacao",
        "progresso",
        "cobranca",
        "historico",
        "ultima_marcacao",
    )
    COLUMN_HEADINGS = {
        "codigo": "Codigo",
        "empresa": "Empresa",
        "situacao": "Situacao do mes",
        "progresso": "Progresso",
        "cobranca": "Cobranca",
        "historico": "Pendencias anteriores",
        "ultima_marcacao": "Ultima marcacao",
    }
    MONTH_STATUS_OVERDUE = "mes_em_atraso"
    UI_SITUATION_LABELS = {
        MONTH_STATUS_OVERDUE: "Em atraso",
        PanoramaService.SITUATION_COM_PENDENCIA: "Com pendencia",
        PanoramaService.SITUATION_EM_ANDAMENTO: "Em andamento",
        PanoramaService.SITUATION_NAO_INICIADA: "Dentro do prazo",
        PanoramaService.SITUATION_SEM_DOCUMENTOS: "Sem documentos",
        PanoramaService.SITUATION_CONCLUIDA: "Concluida",
        PanoramaService.SITUATION_SEM_COBRANCA: "Sem cobranca",
    }
    UI_SITUATION_PRIORITIES = {
        MONTH_STATUS_OVERDUE: 0,
        PanoramaService.SITUATION_COM_PENDENCIA: 1,
        PanoramaService.SITUATION_EM_ANDAMENTO: 2,
        PanoramaService.SITUATION_NAO_INICIADA: 3,
        PanoramaService.SITUATION_SEM_DOCUMENTOS: 4,
        PanoramaService.SITUATION_CONCLUIDA: 5,
        PanoramaService.SITUATION_SEM_COBRANCA: 6,
    }
    WORK_QUEUE_KEYS = {
        MONTH_STATUS_OVERDUE,
        PanoramaService.SITUATION_COM_PENDENCIA,
        PanoramaService.SITUATION_EM_ANDAMENTO,
        PanoramaService.SITUATION_NAO_INICIADA,
    }

    def __init__(self, master, services, on_data_changed, on_open_control=None) -> None:
        super().__init__(master, padding=12)
        self.services = services
        self.on_data_changed = on_data_changed
        self.on_open_control = on_open_control
        self.periods_by_year: dict[int, list[dict]] = {}
        self.period_map_by_year_month: dict[tuple[int, int], int] = {}
        self.periods_by_id: dict[int, dict] = {}
        self.current_rows: list[dict] = []
        self.current_summary: dict[str, int] = {key: 0 for key in PanoramaService.SITUATION_LABELS}
        self.current_queue_by_company: dict[int, dict] = {}
        self.row_by_company_id: dict[str, dict] = {}
        self.dashboard_cards: list[tk.Canvas] = []
        self.global_config_mode = "view"

        self.year_var = tk.StringVar()
        self.month_var = tk.StringVar()
        self.competence_var = tk.StringVar()
        self.situation_var = tk.StringVar(value=self.ALL_SITUATIONS)
        self.collection_var = tk.StringVar(value=self.COLLECTION_ALL)
        self.search_var = tk.StringVar()
        self.active_only_var = tk.BooleanVar(value=True)
        self.summary_var = tk.StringVar(value="Selecione um periodo para carregar a conferencia mensal.")
        self.detail_summary_var = tk.StringVar(
            value="Selecione uma empresa para ver o detalhe do mes e as pendencias anteriores."
        )
        self.dashboard_period_var = tk.StringVar(value="Selecione um periodo para ver o resumo mensal.")
        self.dashboard_pending_var = tk.StringVar(value="0")
        self.dashboard_completed_var = tk.StringVar(value="0")
        self.dashboard_not_started_var = tk.StringVar(value="0")
        self.global_cobranca_inicio_var = tk.StringVar()
        self.global_cobranca_fim_var = tk.StringVar()
        self.global_cobranca_alerta_var = tk.StringVar()
        self.company_code_sort_desc: bool | None = False
        self.company_name_sort_desc: bool | None = None
        self.column_filters = {key: "" for key in self.COLUMN_KEYS}

        self.situation_key_by_label = {label: key for key, label in self.UI_SITUATION_LABELS.items()}
        self.collection_key_by_label = {
            self.COLLECTION_ALL: None,
            self.COLLECTION_UP_TO_DATE: "em_dia",
            CollectionService.PHASE_LABELS[CollectionService.PHASE_EM_COBRANCA]: CollectionService.PHASE_EM_COBRANCA,
            CollectionService.PHASE_LABELS[CollectionService.PHASE_EM_ATRASO]: CollectionService.PHASE_EM_ATRASO,
        }

        self._configure_styles()
        self._build_layout()

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        style.configure("Panorama.Treeview", rowheight=40)
        style.configure("Panorama.Treeview.Heading", font=("TkDefaultFont", 9, "bold"))
        style.configure("Muted.TLabel", foreground="#5F6B7A")
        style.configure("SectionTitle.TLabel", font=("TkDefaultFont", 10, "bold"))
        style.configure("Summary.TLabel", foreground="#314153")
        style.configure("Compact.TEntry", padding=(4, 3))
        style.configure(
            "Compact.TButton",
            padding=(8, 4),
            borderwidth=1,
            relief="solid",
        )
        style.configure(
            "CompactPrimary.TButton",
            background="#2F6FED",
            foreground="#FFFFFF",
            bordercolor="#255FD0",
            lightcolor="#5D8FF0",
            darkcolor="#255FD0",
            focuscolor="#DCE9FF",
            padding=(8, 4),
            borderwidth=1,
            relief="solid",
        )
        style.map(
            "CompactPrimary.TButton",
            background=[("disabled", "#BFD0F6"), ("pressed", "#1E4FAA"), ("active", "#255FD0")],
            foreground=[("disabled", "#F7FAFF"), ("!disabled", "#FFFFFF")],
            bordercolor=[("disabled", "#B0C3EF"), ("focus", "#1E4FAA"), ("!disabled", "#255FD0")],
        )

    def _build_layout(self) -> None:
        filter_frame = ttk.LabelFrame(self, text="Panorama operacional", padding=10)
        filter_frame.pack(fill="x", pady=(0, 6))
        filter_frame.columnconfigure(2, weight=1)

        ttk.Label(filter_frame, text="Competencia (MM/AAAA)").grid(row=0, column=0, sticky="w")
        self.competence_entry = ttk.Entry(filter_frame, textvariable=self.competence_var, width=14)
        self.competence_entry.grid(row=1, column=0, sticky="w", padx=(0, 10))
        self.competence_entry.bind("<Return>", lambda _event: self.load_panorama())
        self.competence_entry.bind("<FocusOut>", lambda _event: self._normalize_competence_input())

        ttk.Label(filter_frame, text="Buscar empresa").grid(row=0, column=1, sticky="w")
        search_entry = ttk.Entry(filter_frame, textvariable=self.search_var, width=28)
        search_entry.grid(row=1, column=1, sticky="w", padx=(0, 10))
        search_entry.bind("<KeyRelease>", lambda _event: self._populate_tree())

        action_frame = ttk.Frame(filter_frame)
        action_frame.grid(row=1, column=3, sticky="e")
        ttk.Checkbutton(
            action_frame,
            text="Somente ativas",
            variable=self.active_only_var,
            command=self.load_panorama,
        ).pack(side="left", padx=(0, 8))
        ttk.Button(action_frame, text="Atualizar", command=self.load_panorama).pack(side="left", padx=(0, 8))
        ttk.Button(action_frame, text="Limpar filtros", command=self.clear_search).pack(side="left", padx=(0, 8))
        self.actions_menu_button = ttk.Menubutton(action_frame, text="Ferramentas", style="Secondary.TMenubutton")
        self.actions_menu = tk.Menu(self.actions_menu_button, tearoff=False)
        self.actions_menu.add_command(label="Exportar relatorio...", command=self.open_pending_report_export_dialog)
        self.actions_menu.add_separator()
        self.actions_menu.add_command(label="Gerar periodos do ano...", command=self.generate_year_periods)
        self.actions_menu.add_command(label="Excluir ano...", command=self.delete_year_periods)
        self.actions_menu.add_separator()
        self.actions_menu.add_command(label="Preparar email", command=self.prepare_email)
        self.actions_menu.add_command(label="Copiar WhatsApp", command=self.copy_whatsapp)
        self.actions_menu_button["menu"] = self.actions_menu
        self.actions_menu_button.pack(side="left", padx=(0, 8))
        ttk.Button(action_frame, text="Abrir no Controle", command=self.open_selected_company).pack(side="left")
        legend_row = ttk.Frame(filter_frame)
        legend_row.grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Label(legend_row, text="Legenda:", style="Muted.TLabel").pack(side="left")
        self._build_legend_item(legend_row, "not_started", "dentro do prazo").pack(side="left", padx=(8, 0))
        self._build_legend_item(legend_row, "in_progress", "em andamento").pack(side="left", padx=(12, 0))
        self._build_legend_item(legend_row, "attention", "pendencia").pack(side="left", padx=(12, 0))
        self._build_legend_item(legend_row, "overdue", "em atraso").pack(side="left", padx=(12, 0))
        self._build_legend_item(legend_row, "completed", "concluida").pack(side="left", padx=(12, 0))

        compact_config = ttk.Frame(filter_frame)
        compact_config.grid(row=2, column=2, columnspan=2, sticky="e", pady=(8, 0))
        ttk.Label(compact_config, text="Cobranca global:", style="Muted.TLabel").pack(side="left", padx=(0, 8))
        ttk.Label(compact_config, text="Inicio").pack(side="left", padx=(0, 4))
        self.global_cobranca_inicio_entry = ttk.Entry(
            compact_config,
            textvariable=self.global_cobranca_inicio_var,
            width=5,
            style="Compact.TEntry",
        )
        self.global_cobranca_inicio_entry.pack(side="left", padx=(0, 8))
        ttk.Label(compact_config, text="Fim").pack(side="left", padx=(0, 4))
        self.global_cobranca_fim_entry = ttk.Entry(
            compact_config,
            textvariable=self.global_cobranca_fim_var,
            width=5,
            style="Compact.TEntry",
        )
        self.global_cobranca_fim_entry.pack(side="left", padx=(0, 8))
        ttk.Label(compact_config, text="Alerta").pack(side="left", padx=(0, 4))
        self.global_cobranca_alerta_entry = ttk.Entry(
            compact_config,
            textvariable=self.global_cobranca_alerta_var,
            width=5,
            style="Compact.TEntry",
        )
        self.global_cobranca_alerta_entry.pack(side="left", padx=(0, 10))

        self.edit_global_button = ttk.Button(
            compact_config,
            text="Editar",
            command=self.start_edit_global_collection_settings,
            style="Compact.TButton",
        )
        self.edit_global_button.pack(side="left")
        self.save_global_button = ttk.Button(
            compact_config,
            text="Salvar",
            command=self.save_global_collection_settings,
            style="CompactPrimary.TButton",
        )
        self.save_global_button.pack(side="left", padx=(6, 0))
        set_button_icon(self.save_global_button, size=14)
        self.cancel_global_button = ttk.Button(
            compact_config,
            text="Cancelar",
            command=self.cancel_edit_global_collection_settings,
            style="Compact.TButton",
        )
        self.cancel_global_button.pack(side="left", padx=(6, 0))

        dashboard_frame = ttk.LabelFrame(self, text="Dashboard mensal", padding=6)
        dashboard_frame.pack(fill="x", pady=(0, 4))
        dashboard_frame.columnconfigure(0, weight=1)
        dashboard_frame.columnconfigure(1, weight=1)
        dashboard_frame.columnconfigure(2, weight=1)

        ttk.Label(dashboard_frame, textvariable=self.dashboard_period_var).grid(
            row=0,
            column=0,
            columnspan=3,
            sticky="w",
            pady=(0, 8),
        )

        self.pending_card = self._build_dashboard_card(
            dashboard_frame,
            column=0,
            title="Em atraso",
            icon_name="overdue",
            value_var=self.dashboard_pending_var,
            background="#FFF1EF",
            foreground="#8C2F22",
            accent="#E26A5B",
        )
        self.completed_card = self._build_dashboard_card(
            dashboard_frame,
            column=1,
            title="Concluidas",
            icon_name="completed",
            value_var=self.dashboard_completed_var,
            background="#EEF9F0",
            foreground="#246A39",
            accent="#55A76A",
        )
        self.not_started_card = self._build_dashboard_card(
            dashboard_frame,
            column=2,
            title="Dentro do prazo",
            icon_name="not_started",
            value_var=self.dashboard_not_started_var,
            background="#FFF6EA",
            foreground="#8A5A12",
            accent="#E0A03B",
        )

        summary_frame = ttk.Frame(self, padding=(2, 0, 2, 0))
        summary_frame.pack(fill="x", pady=(0, 6))
        ttk.Label(summary_frame, textvariable=self.summary_var, style="Summary.TLabel").pack(fill="x")

        content_pane = ttk.Panedwindow(self, orient="vertical")
        content_pane.pack(fill="both", expand=True)

        list_frame = ttk.LabelFrame(content_pane, text="Empresas", padding=10)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            list_frame,
            columns=(
                "codigo",
                "empresa",
                "situacao",
                "progresso",
                "cobranca",
                "historico",
                "ultima_marcacao",
            ),
            show="tree headings",
            selectmode="browse",
            height=16,
            style="Panorama.Treeview",
        )
        self.tree.heading("#0", text="")
        for column_key in self.COLUMN_KEYS:
            self.tree.heading(
                column_key,
                text=self.COLUMN_HEADINGS[column_key],
                command=lambda key=column_key: self._show_column_filter_menu(key),
            )
        self.tree.column("#0", width=56, minwidth=56, stretch=False, anchor="center")
        self.tree.column("codigo", width=90, anchor="center")
        self.tree.column("empresa", width=300)
        self.tree.column("situacao", width=150, anchor="center")
        self.tree.column("progresso", width=90, anchor="center")
        self.tree.column("cobranca", width=120, anchor="center")
        self.tree.column("historico", width=280)
        self.tree.column("ultima_marcacao", width=200, anchor="center")
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<Double-1>", self._on_tree_double_click)
        self.tree.bind("<Return>", lambda _event: self.open_selected_company())
        self.tree.bind("<<TreeviewSelect>>", lambda _event: self._populate_details())

        scrollbar_y = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x = ttk.Scrollbar(list_frame, orient="horizontal", command=self.tree.xview)
        scrollbar_x.grid(row=1, column=0, sticky="ew")
        self.tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        detail_frame = ttk.LabelFrame(content_pane, text="Detalhes da empresa selecionada", padding=10)
        detail_frame.columnconfigure(0, weight=1)
        detail_frame.rowconfigure(1, weight=1)

        ttk.Label(detail_frame, textvariable=self.detail_summary_var, justify="left", style="SectionTitle.TLabel").grid(
            row=0,
            column=0,
            sticky="ew",
            pady=(0, 8),
        )
        self.detail_text = tk.Text(
            detail_frame,
            height=8,
            wrap="word",
            bd=0,
            relief="flat",
            padx=4,
            pady=4,
            background="#FBFCFE",
            font=("TkDefaultFont", 10),
        )
        self.detail_text.grid(row=1, column=0, sticky="nsew")
        self.detail_text.bind("<Double-1>", lambda _event: self.open_selected_company())
        detail_scrollbar = ttk.Scrollbar(detail_frame, orient="vertical", command=self.detail_text.yview)
        detail_scrollbar.grid(row=1, column=1, sticky="ns")
        self.detail_text.configure(yscrollcommand=detail_scrollbar.set)
        self._configure_detail_tags()

        content_pane.add(list_frame, weight=6)
        content_pane.add(detail_frame, weight=2)

        self._set_global_config_mode("view")

    def _configure_detail_tags(self) -> None:
        self.detail_text.tag_configure("section", font=("TkDefaultFont", 10, "bold"), foreground="#213244", spacing3=8)
        self.detail_text.tag_configure("subsection", font=("TkDefaultFont", 10, "bold"), foreground="#39516B")
        self.detail_text.tag_configure("muted", foreground="#6A7685", spacing3=6)
        self.detail_text.tag_configure("item", lmargin1=18, lmargin2=18, spacing3=2)
        self.detail_text.tag_configure("ok", foreground="#256A3C")
        self.detail_text.tag_configure("warn", foreground="#8C5A12")
        self.detail_text.tag_configure("danger", foreground="#8C2F22")
        self.detail_text.tag_configure("info", foreground="#2F4E73")
        self.detail_text.configure(state="disabled")

    def refresh_data(self) -> None:
        selected_period_id = self._selected_period_id()
        self._load_period_options()
        self._load_global_collection_settings()

        if selected_period_id and self._set_period_by_id(selected_period_id):
            self.load_panorama()
            return

        if self._select_default_period():
            self.load_panorama()
            return

        self.current_rows = []
        self.current_summary = {key: 0 for key in PanoramaService.SITUATION_LABELS}
        self.current_queue_by_company = {}
        self.row_by_company_id = {}
        self.tree.delete(*self.tree.get_children())
        self._clear_detail_text()
        self._update_dashboard_cards()
        self.summary_var.set("Nenhum periodo cadastrado para carregar a conferencia mensal.")
        self.detail_summary_var.set("Selecione uma empresa para ver o detalhe do mes e as pendencias anteriores.")

    def _load_period_options(self) -> None:
        periodos = self.services.periodo_service.list_periodos()
        self.periods_by_year = {}
        self.period_map_by_year_month = {}
        self.periods_by_id = {}

        for periodo in periodos:
            self.periods_by_year.setdefault(periodo["ano"], []).append(periodo)
            self.period_map_by_year_month[(periodo["ano"], periodo["mes"])] = periodo["id"]
            self.periods_by_id[periodo["id"]] = periodo

        for items in self.periods_by_year.values():
            items.sort(key=lambda item: item["mes"])

        if self.competence_var.get().strip() and not self._sync_selected_competence():
            self.competence_var.set("")
            self.year_var.set("")
            self.month_var.set("")

    def _select_default_period(self) -> bool:
        if not self.period_map_by_year_month:
            self.year_var.set("")
            self.month_var.set("")
            self.competence_var.set("")
            return False

        today = datetime.now()
        default_key = (today.year, today.month)
        if default_key not in self.period_map_by_year_month:
            default_key = max(self.period_map_by_year_month)

        year, month = default_key
        self._set_competence_by_year_month(year, month)
        return True

    def _set_period_by_id(self, periodo_id: int) -> bool:
        periodo = self.periods_by_id.get(periodo_id)
        if not periodo:
            return False
        self._set_competence_by_year_month(periodo["ano"], periodo["mes"])
        return True

    def _month_label(self, month: int) -> str:
        return f"{month:02d} - {MONTH_NAMES[month]}"

    def _competence_label(self, year: int, month: int) -> str:
        return f"{month:02d}/{year}"

    def _set_competence_by_year_month(self, year: int, month: int) -> None:
        self.year_var.set(str(year))
        self.month_var.set(self._month_label(month))
        self.competence_var.set(self._competence_label(year, month))

    def _parse_competence_value(self, value: str) -> tuple[int, int] | None:
        text = value.strip()
        if not text:
            return None

        digits = re.sub(r"\D", "", text)
        if len(digits) == 6:
            return int(digits[2:]), int(digits[:2])

        match = re.search(r"(?P<month>0?[1-9]|1[0-2])\s*/\s*(?P<year>\d{4})", text)
        if match:
            return int(match.group("year")), int(match.group("month"))

        match = re.search(r"(?P<year>\d{4})\s*[-/]\s*(?P<month>0?[1-9]|1[0-2])", text)
        if match:
            return int(match.group("year")), int(match.group("month"))

        match = re.search(r"(?P<month>0?[1-9]|1[0-2])\s*-\s*(?P<year>\d{4})", text)
        if match:
            return int(match.group("year")), int(match.group("month"))

        return None

    def _sync_selected_competence(self) -> bool:
        parsed = self._parse_competence_value(self.competence_var.get())
        if not parsed:
            return False

        year, month = parsed
        if (year, month) not in self.period_map_by_year_month:
            return False

        self._set_competence_by_year_month(year, month)
        return True

    def _normalize_competence_input(self) -> None:
        self._sync_selected_competence()

    def _selected_period_id(self) -> int | None:
        if not self.competence_var.get().strip():
            return None
        if not self._sync_selected_competence():
            return None

        selected_key = (
            int(self.year_var.get()),
            int(self.month_var.get().split(" - ", 1)[0]),
        )
        return self.period_map_by_year_month.get(selected_key)

    def _selected_period_short_label(self) -> str:
        period_id = self._selected_period_id()
        periodo = self.periods_by_id.get(period_id) if period_id else None
        if periodo:
            return f'{periodo["mes"]:02d}/{periodo["ano"]}'
        return self.competence_var.get().strip()

    def load_panorama(self) -> None:
        period_id = self._selected_period_id()
        if not period_id:
            messagebox.showwarning("Panorama", "Informe uma competencia cadastrada para carregar a conferencia.", parent=self)
            return

        try:
            monthly_view = self.services.panorama_service.build_monthly_view(
                period_id,
                active_only=self.active_only_var.get(),
            )
            queue_view = self.services.collection_service.build_collection_queue(
                active_only=self.active_only_var.get()
            )
        except ValidationError as exc:
            messagebox.showerror("Panorama", str(exc), parent=self)
            return

        self.current_summary = monthly_view["summary"]
        self.current_queue_by_company = {
            item["empresa_id"]: self._build_queue_item_until_selected_period(item, period_id)
            for item in queue_view["items"]
        }
        self.current_rows = self._merge_monthly_rows_with_queue(monthly_view["rows"], period_id)
        self._update_dashboard_cards()
        self._populate_tree()

    def _merge_monthly_rows_with_queue(self, rows: list[dict], selected_period_id: int) -> list[dict]:
        merged_rows: list[dict] = []
        selected_period_key = self._period_sort_key(selected_period_id)

        for row in rows:
            merged = dict(row)
            queue_item = self.current_queue_by_company.get(row["empresa_id"])
            previous_period_items = self._previous_period_items(queue_item, selected_period_key)
            merged["queue_item"] = queue_item
            merged["previous_period_items"] = previous_period_items
            merged["previous_pending_count"] = len(previous_period_items)
            merged["previous_pending_summary"] = self._build_previous_pending_summary(previous_period_items)
            merged["selected_period_collection_item"] = self._selected_period_collection_item(
                queue_item,
                selected_period_id,
            )
            merged["month_status_key"] = self._row_month_status_key(merged)

            if not queue_item:
                merged["collection_status_key"] = "em_dia"
                merged["collection_status"] = self.COLLECTION_UP_TO_DATE
            elif previous_period_items:
                merged["collection_status_key"] = CollectionService.PHASE_EM_ATRASO
                merged["collection_status"] = CollectionService.PHASE_LABELS[CollectionService.PHASE_EM_ATRASO]
            else:
                merged["collection_status_key"] = queue_item["phase_key"]
                merged["collection_status"] = queue_item["phase_label"]

            merged_rows.append(merged)

        merged_rows.sort(
            key=lambda item: (
                self._collection_priority(item["collection_status_key"]),
                self.UI_SITUATION_PRIORITIES.get(item["month_status_key"], 99),
                item["codigo_empresa"],
                item["nome_empresa"].casefold(),
            )
        )
        return merged_rows

    def _build_queue_item_until_selected_period(self, item: dict, selected_period_id: int) -> dict | None:
        selected_period_key = self._period_sort_key(selected_period_id)
        if selected_period_key is None:
            return None

        relevant_period_items = [
            {
                **period_item,
                "documents": [dict(document) for document in period_item["documents"]],
            }
            for period_item in item["period_items"]
            if (self._period_sort_key(period_item["periodo_id"]) or 0) <= selected_period_key
        ]
        if not relevant_period_items:
            return None

        relevant_period_items.sort(key=lambda period_item: self._period_sort_key(period_item["periodo_id"]) or 0)
        phase_key = (
            CollectionService.PHASE_EM_ATRASO
            if any(period_item["phase_key"] == CollectionService.PHASE_EM_ATRASO for period_item in relevant_period_items)
            else CollectionService.PHASE_EM_COBRANCA
        )
        primary_period = self._pick_primary_period(relevant_period_items)
        documents = [
            {
                **document,
                "periodo_id": period_item["periodo_id"],
                "periodo_label": period_item["periodo_label"],
            }
            for period_item in relevant_period_items
            for document in period_item["documents"]
        ]
        return {
            "empresa_id": item["empresa_id"],
            "codigo_empresa": item["codigo_empresa"],
            "nome_empresa": item["nome_empresa"],
            "empresa_ativa": item["empresa_ativa"],
            "email_contato": item["email_contato"],
            "nome_contato": item["nome_contato"],
            "period_items": relevant_period_items,
            "period_count": len(relevant_period_items),
            "document_count": len(documents),
            "documents": documents,
            "days_after_end": max(period_item["days_after_end"] for period_item in relevant_period_items),
            "alert_ready": any(period_item["alert_ready"] for period_item in relevant_period_items),
            "settings_source": item["settings_source"],
            "phase_key": phase_key,
            "phase_label": CollectionService.PHASE_LABELS[phase_key],
            "primary_period": primary_period,
            "primary_period_id": primary_period["periodo_id"],
            "primary_period_label": primary_period["periodo_label"],
            "window_start": primary_period["window_start"],
            "window_end": primary_period["window_end"],
            "alerta_apos_dias": primary_period["alerta_apos_dias"],
            "period_summary": self._build_period_summary(relevant_period_items),
            "suggested_channel": self._resolve_suggested_channel(item, documents),
        }

    def _period_sort_key(self, period_id: int | None) -> int | None:
        if period_id is None:
            return None
        periodo = self.periods_by_id.get(period_id)
        if not periodo:
            return None
        return (periodo["ano"] * 100) + periodo["mes"]

    def _previous_period_items(self, queue_item: dict | None, selected_period_key: int | None) -> list[dict]:
        if not queue_item or selected_period_key is None:
            return []
        return [
            period_item
            for period_item in queue_item["period_items"]
            if (self._period_sort_key(period_item["periodo_id"]) or 0) < selected_period_key
        ]

    def _selected_period_collection_item(self, queue_item: dict | None, selected_period_id: int) -> dict | None:
        if not queue_item:
            return None
        return next(
            (
                period_item
                for period_item in queue_item["period_items"]
                if period_item["periodo_id"] == selected_period_id
            ),
            None,
        )

    def _row_month_status_key(self, row: dict) -> str:
        selected_period_collection = row.get("selected_period_collection_item")
        if selected_period_collection and selected_period_collection["phase_key"] == CollectionService.PHASE_EM_ATRASO:
            return self.MONTH_STATUS_OVERDUE
        return row["situacao_key"]

    def _count_month_statuses(self, rows: list[dict]) -> dict[str, int]:
        counts = {key: 0 for key in self.UI_SITUATION_LABELS}
        for row in rows:
            counts[self._row_month_status_key(row)] += 1
        return counts

    def _collection_priority(self, collection_status_key: str) -> int:
        if collection_status_key == CollectionService.PHASE_EM_ATRASO:
            return 0
        if collection_status_key == CollectionService.PHASE_EM_COBRANCA:
            return 1
        return 2

    def _build_previous_pending_summary(self, period_items: list[dict]) -> str:
        if not period_items:
            return "-"
        labels = [period_item["periodo_label"] for period_item in period_items]
        if len(labels) == 1:
            return labels[0]
        if len(labels) == 2:
            return f"{labels[0]} e {labels[1]}"
        return f"{labels[0]}, {labels[1]} e mais {len(labels) - 2} mes(es)"

    def _pick_primary_period(self, period_items: list[dict]) -> dict:
        overdue_items = [item for item in period_items if item["phase_key"] == CollectionService.PHASE_EM_ATRASO]
        target_items = overdue_items or period_items
        return sorted(
            target_items,
            key=lambda item: (self._period_sort_key(item["periodo_id"]) or 0, -item["days_after_end"]),
        )[0]

    def _build_period_summary(self, period_items: list[dict]) -> str:
        if len(period_items) == 1:
            return period_items[0]["periodo_label"]
        first_label = period_items[0]["periodo_label"]
        last_label = period_items[-1]["periodo_label"]
        return f"{first_label} ate {last_label} ({len(period_items)} meses)"

    def _resolve_suggested_channel(self, item: dict, documents: list[dict]) -> str:
        available_methods: list[str] = []
        for document in documents:
            available_methods.extend(document.get("meios_recebimento") or [])
        available_set = {method.casefold(): method for method in available_methods}
        if item.get("email_contato"):
            return "Email"
        if "whatsapp" in available_set:
            return "WhatsApp"
        if available_methods:
            return available_methods[0]
        return "Manual"

    def _build_dashboard_card(
        self,
        master,
        column: int,
        title: str,
        icon_name: str,
        value_var: tk.StringVar,
        background: str,
        foreground: str,
        accent: str,
    ) -> tk.Canvas:
        card = tk.Canvas(
            master,
            height=70,
            bd=0,
            highlightthickness=0,
            relief="flat",
            background=self.winfo_toplevel().cget("bg"),
        )
        card.grid(row=1, column=column, sticky="ew", padx=(0, 8) if column < 2 else (0, 0))
        card.card_config = {
            "title": title,
            "icon_name": icon_name,
            "value_var": value_var,
            "background": background,
            "foreground": foreground,
            "accent": accent,
        }
        card.bind("<Configure>", lambda _event, canvas=card: self._render_dashboard_card(canvas))
        self.dashboard_cards.append(card)
        self._render_dashboard_card(card)
        return card

    def _render_dashboard_card(self, card: tk.Canvas) -> None:
        config = card.card_config
        width = max(card.winfo_width(), 140)
        height = max(card.winfo_height(), 70)
        card.delete("all")

        shadow_offset = 2
        self._draw_rounded_rectangle(
            card,
            2,
            4,
            width - shadow_offset,
            height - shadow_offset,
            radius=15,
            fill="#DADDE3",
            outline="",
        )
        self._draw_rounded_rectangle(
            card,
            1,
            2,
            width - 3,
            height - 4,
            radius=15,
            fill=config["background"],
            outline="#E3E6EB",
        )
        dashboard_icon = get_status_icon(self, config["icon_name"], size=18)
        card.create_image(width - 24, 18, image=dashboard_icon)
        card.create_text(
            14,
            12,
            text=config["title"],
            anchor="nw",
            fill=config["foreground"],
            font=("TkDefaultFont", 9, "bold"),
        )
        card.create_text(
            14,
            37,
            text=config["value_var"].get(),
            anchor="w",
            fill=config["foreground"],
            font=("TkDefaultFont", 18, "bold"),
        )
        card.create_text(
            14,
            height - 12,
            text="empresas",
            anchor="sw",
            fill=config["foreground"],
            font=("TkDefaultFont", 8),
        )

    def _build_legend_item(self, master: tk.Misc, icon_name: str, text: str) -> ttk.Frame:
        item = ttk.Frame(master)
        icon = get_status_icon(self, icon_name, size=16)
        ttk.Label(item, image=icon).pack(side="left")
        ttk.Label(item, text=text, style="Muted.TLabel").pack(side="left", padx=(5, 0))
        return item

    def _draw_rounded_rectangle(
        self,
        canvas: tk.Canvas,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        radius: float,
        *,
        fill: str,
        outline: str,
    ) -> None:
        radius = min(radius, (x2 - x1) / 2, (y2 - y1) / 2)
        canvas.create_arc(x1, y1, x1 + (radius * 2), y1 + (radius * 2), start=90, extent=90, fill=fill, outline=outline)
        canvas.create_arc(x2 - (radius * 2), y1, x2, y1 + (radius * 2), start=0, extent=90, fill=fill, outline=outline)
        canvas.create_arc(x1, y2 - (radius * 2), x1 + (radius * 2), y2, start=180, extent=90, fill=fill, outline=outline)
        canvas.create_arc(
            x2 - (radius * 2),
            y2 - (radius * 2),
            x2,
            y2,
            start=270,
            extent=90,
            fill=fill,
            outline=outline,
        )
        canvas.create_rectangle(x1 + radius, y1, x2 - radius, y2, fill=fill, outline=outline)
        canvas.create_rectangle(x1, y1 + radius, x2, y2 - radius, fill=fill, outline=outline)

    def _update_dashboard_cards(self) -> None:
        period_id = self._selected_period_id()
        if not period_id or not self.current_rows:
            self.dashboard_period_var.set("Selecione um periodo para ver o resumo mensal.")
            self.dashboard_pending_var.set("0")
            self.dashboard_completed_var.set("0")
            self.dashboard_not_started_var.set("0")
            for card in self.dashboard_cards:
                self._render_dashboard_card(card)
            return

        period_label = self._selected_period_short_label()
        mode_label = "somente empresas ativas" if self.active_only_var.get() else "empresas ativas e inativas"
        month_counts = self._count_month_statuses(self.current_rows)
        self.dashboard_period_var.set(f"Resumo de {period_label} considerando {mode_label}.")
        self.dashboard_pending_var.set(str(month_counts[self.MONTH_STATUS_OVERDUE]))
        self.dashboard_completed_var.set(str(month_counts[PanoramaService.SITUATION_CONCLUIDA]))
        self.dashboard_not_started_var.set(str(month_counts[PanoramaService.SITUATION_NAO_INICIADA]))
        for card in self.dashboard_cards:
            self._render_dashboard_card(card)

    def _populate_tree(self) -> None:
        if not hasattr(self, "tree"):
            return

        self._update_filter_headings()
        self.tree.delete(*self.tree.get_children())
        self.row_by_company_id = {}
        filtered_rows = self._filtered_rows()
        filtered_rows = self._sorted_rows(filtered_rows)

        for index, row in enumerate(filtered_rows):
            row_key = str(row["empresa_id"])
            self.row_by_company_id[row_key] = row
            base_tag = "evenrow" if index % 2 == 0 else "oddrow"
            emphasis_tag = self._row_emphasis_tag(row)
            self.tree.insert(
                "",
                "end",
                iid=row_key,
                text="",
                image=get_status_icon(self.tree, self._row_icon_name(row), size=26),
                values=tuple(self._row_column_display(row, key) for key in self.COLUMN_KEYS),
                tags=(base_tag, emphasis_tag),
            )

        self.tree.tag_configure("evenrow", background="#FBFCFE")
        self.tree.tag_configure("oddrow", background="#F3F6FA")
        self.tree.tag_configure("emphasis_overdue", foreground="#8C2F22")
        self.tree.tag_configure("emphasis_current", foreground="#8A5A12")
        self.tree.tag_configure("emphasis_ok", foreground="#256A3C")
        self.tree.tag_configure("emphasis_neutral", foreground="#172033")

        self._update_summary(filtered_rows)
        self._populate_details()

    def _show_column_filter_menu(self, column_key: str) -> None:
        menu = tk.Menu(self, tearoff=False)
        current_value = self.column_filters.get(column_key, "")

        if column_key == "codigo":
            menu.add_command(label="Ordenar codigo crescente", command=lambda: self._set_company_code_sort(False))
            menu.add_command(label="Ordenar codigo decrescente", command=lambda: self._set_company_code_sort(True))
            menu.add_separator()

        if column_key == "empresa":
            menu.add_command(label="Ordenar empresa A-Z", command=lambda: self._set_company_name_sort(False))
            menu.add_command(label="Ordenar empresa Z-A", command=lambda: self._set_company_name_sort(True))
            try:
                menu.tk_popup(self.winfo_pointerx(), self.winfo_pointery())
            finally:
                menu.grab_release()
            return

        all_label = self._menu_filter_label(self.FILTER_ALL_LABEL, current_value == "")
        menu.add_command(label=all_label, command=lambda: self._set_column_filter(column_key, ""))

        options = self._column_filter_options(column_key)
        if options:
            menu.add_separator()
        for option in options:
            label = self._menu_filter_label(option or "(vazio)", option == current_value)
            menu.add_command(
                label=label,
                command=lambda value=option: self._set_column_filter(column_key, value),
            )

        try:
            menu.tk_popup(self.winfo_pointerx(), self.winfo_pointery())
        finally:
            menu.grab_release()

    def _menu_filter_label(self, label: str, selected: bool) -> str:
        return f"[x] {label}" if selected else label

    def _set_column_filter(self, column_key: str, value: str) -> None:
        self.column_filters[column_key] = value
        self._populate_tree()

    def _set_company_code_sort(self, descending: bool) -> None:
        self.company_code_sort_desc = descending
        self.company_name_sort_desc = None
        self.column_filters["empresa"] = ""
        self._populate_tree()

    def _set_company_name_sort(self, descending: bool) -> None:
        self.company_name_sort_desc = descending
        self.company_code_sort_desc = None
        self.column_filters["empresa"] = ""
        self._populate_tree()

    def _update_filter_headings(self) -> None:
        for column_key in self.COLUMN_KEYS:
            text = self.COLUMN_HEADINGS[column_key]
            if column_key == "codigo" and self.company_code_sort_desc is not None:
                text = f"{text} {'v' if self.company_code_sort_desc else '^'}"
            if column_key == "empresa" and self.company_name_sort_desc is not None:
                text = f"{text} {'Z-A' if self.company_name_sort_desc else 'A-Z'}"

            filter_value = self.column_filters.get(column_key, "")
            if filter_value:
                text = f"{text}: {self._short_filter_label(filter_value)}"

            self.tree.heading(
                column_key,
                text=text,
                command=lambda key=column_key: self._show_column_filter_menu(key),
            )

    def _short_filter_label(self, value: str, limit: int = 22) -> str:
        return value if len(value) <= limit else f"{value[: limit - 3]}..."

    def _row_column_display(self, row: dict, column_key: str) -> str:
        if column_key == "codigo":
            return str(row["codigo_empresa"])
        if column_key == "empresa":
            return row["nome_empresa"] if row["ativa"] else f'{row["nome_empresa"]} [Inativa]'
        if column_key == "situacao":
            return self._format_month_status(row)
        if column_key == "progresso":
            return f'{row["marcados"]}/{row["total_cobravel"]}'
        if column_key == "cobranca":
            return self._format_collection_status(row)
        if column_key == "historico":
            return self._format_previous_pending_display(row)
        if column_key == "ultima_marcacao":
            return self._format_last_marker(row)
        return ""

    def _column_filter_options(self, column_key: str) -> list[str]:
        values = {
            self._row_column_display(row, column_key)
            for row in self._filtered_rows(excluded_filter=column_key)
        }
        return sorted(values, key=lambda value: self._filter_value_sort_key(column_key, value))

    def _filter_value_sort_key(self, column_key: str, value: str) -> tuple:
        if column_key == "codigo":
            try:
                return (0, int(value))
            except ValueError:
                return (1, value.casefold())
        return (0, value.casefold())

    def _row_emphasis_tag(self, row: dict) -> str:
        if self._row_month_status_key(row) == self.MONTH_STATUS_OVERDUE:
            return "emphasis_overdue"
        if row["situacao_key"] == PanoramaService.SITUATION_COM_PENDENCIA:
            return "emphasis_current"
        if row["situacao_key"] == PanoramaService.SITUATION_CONCLUIDA and row["collection_status_key"] == "em_dia":
            return "emphasis_ok"
        return "emphasis_neutral"

    def _row_icon_name(self, row: dict) -> str:
        return self._month_status_icon_name(self._row_month_status_key(row))

    def _filtered_rows(self, *, excluded_filter: str | None = None) -> list[dict]:
        search = self.search_var.get().strip().casefold()

        rows = []
        for row in self.current_rows:
            company_text = f'{row["codigo_empresa"]} {row["nome_empresa"]}'.casefold()
            if search and search not in company_text:
                continue

            matches_column_filters = True
            for column_key, expected in self.column_filters.items():
                if column_key == excluded_filter or not expected:
                    continue
                if self._row_column_display(row, column_key) != expected:
                    matches_column_filters = False
                    break
            if not matches_column_filters:
                continue

            rows.append(row)
        return rows

    def _sorted_rows(self, rows: list[dict]) -> list[dict]:
        if self.company_name_sort_desc is not None:
            return sorted(
                rows,
                key=lambda row: (row["nome_empresa"].casefold(), self._company_code_sort_value(row["codigo_empresa"])),
                reverse=self.company_name_sort_desc,
            )
        if self.company_code_sort_desc is None:
            return rows
        return sorted(
            rows,
            key=lambda row: (self._company_code_sort_value(row["codigo_empresa"]), row["nome_empresa"].casefold()),
            reverse=self.company_code_sort_desc,
        )

    def _company_code_sort_value(self, value) -> tuple:
        try:
            return (0, int(value))
        except (TypeError, ValueError):
            return (1, str(value).casefold())

    def toggle_company_code_sort(self) -> None:
        self.company_code_sort_desc = False if self.company_code_sort_desc is None else not self.company_code_sort_desc
        self.company_name_sort_desc = None
        self._populate_tree()

    def _format_last_marker(self, row: dict) -> str:
        updated_at = row.get("ultima_marcacao_em")
        if not updated_at:
            return "-"

        try:
            formatted = datetime.strptime(updated_at, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
        except ValueError:
            formatted = str(updated_at)

        actor = row.get("ultima_marcacao_por") or ""
        return f"{formatted} - {actor}" if actor else formatted

    def _update_summary(self, filtered_rows: list[dict]) -> None:
        if not self.current_rows:
            self.summary_var.set("Nenhuma empresa encontrada para o filtro informado.")
            return

        period_label = self._selected_period_short_label()

        counts = self._count_month_statuses(filtered_rows)
        collection_counts = {
            "em_dia": 0,
            CollectionService.PHASE_EM_COBRANCA: 0,
            CollectionService.PHASE_EM_ATRASO: 0,
        }
        for row in filtered_rows:
            collection_counts[row["collection_status_key"]] += 1

        parts = [
            f'{self.UI_SITUATION_LABELS[key]}: {counts[key]}'
            for key in (
                self.MONTH_STATUS_OVERDUE,
                PanoramaService.SITUATION_COM_PENDENCIA,
                PanoramaService.SITUATION_EM_ANDAMENTO,
                PanoramaService.SITUATION_NAO_INICIADA,
                PanoramaService.SITUATION_SEM_DOCUMENTOS,
                PanoramaService.SITUATION_CONCLUIDA,
                PanoramaService.SITUATION_SEM_COBRANCA,
            )
        ]
        parts.append(f'Cobranca em dia: {collection_counts["em_dia"]}')
        parts.append(f'Em cobranca: {collection_counts[CollectionService.PHASE_EM_COBRANCA]}')
        parts.append(f'Cobranca em atraso: {collection_counts[CollectionService.PHASE_EM_ATRASO]}')
        self.summary_var.set(
            f"{len(filtered_rows)} de {len(self.current_rows)} empresa(s) em {period_label}. "
            + " | ".join(parts)
        )

    def _populate_details(self) -> None:
        self._clear_detail_text()
        row = self._selected_row()
        period_id = self._selected_period_id()
        if not row or not period_id:
            self.detail_summary_var.set(
                "Selecione uma empresa para ver o detalhe do mes e as pendencias anteriores."
            )
            return

        self.detail_summary_var.set(
            f'{row["codigo_empresa"]} - {row["nome_empresa"]} | '
            f'Mes: {self._format_month_status(row)} | Cobranca: {self._format_collection_status(row)}'
        )

        self._append_detail_line(
            f'Periodo selecionado: {self._selected_period_short_label()}',
            "section",
        )
        self._append_detail_line(
            f'Progresso atual: {row["marcados"]}/{row["total_cobravel"]} | Recebidos: {row["recebidos"]} | Pendentes: {row["pendentes"]} | Faltando: {row["faltando"]}',
            "muted",
            icon_name=self._row_icon_name(row),
        )
        self._append_detail_line("")
        self._populate_current_month_details(row["empresa_id"], period_id)

        self._append_detail_line("")
        self._append_detail_line("Documentos em aberto de meses anteriores", "section")
        self._append_detail_line("")
        previous_period_items = row.get("previous_period_items") or []
        if not previous_period_items:
            self._append_detail_line(
                "Nenhum documento em aberto de meses anteriores para essa empresa.",
                "ok",
                icon_name="completed",
            )
            return

        for period_item in previous_period_items:
            self._append_detail_line(
                f'{period_item["periodo_label"]} | {period_item["phase_label"]}',
                "subsection",
                icon_name=self._phase_icon_name(period_item["phase_key"]),
            )
            for document in period_item["documents"]:
                channel = ", ".join(document["meios_recebimento"]) if document["meios_recebimento"] else "Sem meio informado"
                self._append_detail_line(
                    f'{document["nome_documento"]} | {document["status"]} | {channel}',
                    self._detail_tag_for_status(document["status"]),
                    icon_name=self._document_status_icon_name(document["status"]),
                )
            self._append_detail_line("")

    def _populate_current_month_details(self, company_id: int, period_id: int) -> None:
        try:
            view = self.services.status_service.build_control_view(company_id, period_id, period_id)
        except ValidationError as exc:
            self._append_detail_line(str(exc), "danger")
            return

        groups = view.get("groups") or []
        if not groups:
            self._append_detail_line("Nenhum documento cobravel encontrado para esse periodo.", "info")
            return

        self._append_detail_line("Mes atual", "section")
        for group in groups:
            self._append_detail_line(group["tipo_nome"], "subsection")
            for document in group["documentos"]:
                cell = document["cells"][0]
                status = cell["status"] or "Nao iniciado"
                channel = document.get("meios_recebimento") or "Sem meio informado"
                self._append_detail_line(
                    f'{document["nome_documento"]} | {status} | {channel}',
                    self._detail_tag_for_status(status),
                    icon_name=self._document_status_icon_name(status),
                )
            self._append_detail_line("")

    def _detail_tag_for_status(self, status: str) -> str:
        if status == "Recebido":
            return "ok"
        if status == "Pendente":
            return "warn"
        if status == "Nao iniciado":
            return "info"
        if status == "Encerrado":
            return "muted"
        return "item"

    def _append_detail_line(self, text: str, tag: str | None = None, *, icon_name: str | None = None) -> None:
        self.detail_text.configure(state="normal")
        applied_tag = tag or "item"
        if icon_name:
            self.detail_text.image_create("end", image=get_status_icon(self.detail_text, icon_name, size=16), padx=2)
            self.detail_text.insert("end", " ", applied_tag)
        self.detail_text.insert("end", f"{text}\n", applied_tag)
        self.detail_text.configure(state="disabled")

    def _clear_detail_text(self) -> None:
        self.detail_text.configure(state="normal")
        self.detail_text.delete("1.0", "end")
        self.detail_text.configure(state="disabled")

    def _format_month_status(self, row: dict) -> str:
        status_key = self._row_month_status_key(row)
        label = self.UI_SITUATION_LABELS[status_key]
        if status_key == self.MONTH_STATUS_OVERDUE:
            return f"🚨 {label}"
        if status_key == PanoramaService.SITUATION_COM_PENDENCIA:
            return f"⚠ {label}"
        return label

    def _format_collection_status(self, row: dict) -> str:
        status = str(row["collection_status"])
        if row["collection_status_key"] == CollectionService.PHASE_EM_ATRASO:
            return f"🚨 {status}"
        if row["collection_status_key"] == CollectionService.PHASE_EM_COBRANCA:
            return f"⚠ {status}"
        return status

    def _format_previous_pending_display(self, row: dict) -> str:
        summary = row.get("previous_pending_summary") or "-"
        if summary == "-":
            return "Em dia"
        return f"🚨 {summary}"

    def _month_status_icon_name(self, situation_key: str) -> str:
        icon_by_key = {
            self.MONTH_STATUS_OVERDUE: "overdue",
            PanoramaService.SITUATION_COM_PENDENCIA: "attention",
            PanoramaService.SITUATION_EM_ANDAMENTO: "in_progress",
            PanoramaService.SITUATION_NAO_INICIADA: "not_started",
            PanoramaService.SITUATION_CONCLUIDA: "completed",
            PanoramaService.SITUATION_SEM_DOCUMENTOS: "neutral",
            PanoramaService.SITUATION_SEM_COBRANCA: "neutral",
        }
        return icon_by_key.get(situation_key, "neutral")

    def _phase_icon_name(self, phase_key: str) -> str:
        icon_by_key = {
            "em_dia": "completed",
            CollectionService.PHASE_EM_COBRANCA: "in_progress",
            CollectionService.PHASE_EM_ATRASO: "overdue",
        }
        return icon_by_key.get(phase_key, "neutral")

    def _document_status_icon_name(self, status: str) -> str:
        icon_by_status = {
            "Recebido": "completed",
            "Pendente": "attention",
            "Encerrado": "closed",
            "Nao iniciado": "not_started",
        }
        return icon_by_status.get(status or "", "neutral")

    def clear_search(self) -> None:
        self.search_var.set("")
        self.situation_var.set(self.ALL_SITUATIONS)
        self.collection_var.set(self.COLLECTION_ALL)
        self.column_filters = {key: "" for key in self.COLUMN_KEYS}
        self.company_code_sort_desc = False
        self.company_name_sort_desc = None
        self._populate_tree()

    def _selected_row(self) -> dict | None:
        selection = self.tree.selection()
        if not selection:
            return None
        return self.row_by_company_id.get(selection[0])

    def _selected_queue_item(self) -> dict | None:
        row = self._selected_row()
        if not row:
            return None
        return row.get("queue_item")

    def _on_tree_double_click(self, event: tk.Event) -> str | None:
        if self.tree.identify_region(event.x, event.y) == "heading":
            return "break"
        return self.open_selected_company()

    def open_selected_company(self) -> str | None:
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Panorama", "Selecione uma empresa para abrir no Controle.", parent=self)
            return "break"

        period_id = self._selected_period_id()
        if not period_id:
            messagebox.showwarning("Panorama", "Informe a competencia antes de abrir no Controle.", parent=self)
            return "break"

        if not self.on_open_control:
            return "break"

        self.on_open_control(int(selection[0]), period_id)
        return "break"

    def open_pending_report_export_dialog(self) -> None:
        visible_company_ids = [row["empresa_id"] for row in self._sorted_rows(self._filtered_rows())]
        PendingReportExportDialog(
            self,
            self.services,
            periods_by_year=self.periods_by_year,
            period_map_by_year_month=self.period_map_by_year_month,
            default_year=self.year_var.get(),
            default_month=self.month_var.get(),
            visible_company_ids=visible_company_ids,
        )

    def generate_year_periods(self) -> None:
        year = simpledialog.askstring(
            "Gerar periodos",
            "Informe o ano para gerar os 12 meses:",
            parent=self,
        )
        if year is None:
            return

        try:
            result = self.services.periodo_service.generate_year(year)
        except ValidationError as exc:
            messagebox.showerror("Gerar periodos", str(exc), parent=self)
            return

        if self.on_data_changed:
            self.on_data_changed()
        messagebox.showinfo(
            "Gerar periodos",
            (
                f'Ano {result["ano"]} processado com sucesso.\n'
                f'Meses criados: {result["created"]}\n'
                f'Meses ja existentes: {result["existing"]}'
            ),
            parent=self,
        )

    def delete_year_periods(self) -> None:
        years = [str(year) for year in self.services.periodo_service.list_available_years()]
        if not years:
            messagebox.showwarning("Excluir ano", "Nenhum ano cadastrado para excluir.", parent=self)
            return

        year = simpledialog.askstring(
            "Excluir ano",
            "Informe o ano que deseja excluir.\n\nAnos existentes: " + ", ".join(years),
            parent=self,
        )
        if year is None:
            return
        year = year.strip()
        if year not in years:
            messagebox.showwarning("Excluir ano", "Selecione um ano existente.", parent=self)
            return

        if not messagebox.askyesno(
            "Excluir ano",
            (
                "Todos os periodos e controles mensais desse ano serao apagados.\n"
                "Empresas, tipos e documentos base nao serao excluidos.\n\n"
                "Deseja continuar?"
            ),
            parent=self,
        ):
            return
        if not messagebox.askyesno(
            "Confirmacao final",
            f"Confirma a exclusao definitiva do ano {year}?",
            parent=self,
        ):
            return

        try:
            result = self.services.periodo_service.delete_year(year)
        except ValidationError as exc:
            messagebox.showerror("Excluir ano", str(exc), parent=self)
            return

        if self.on_data_changed:
            self.on_data_changed()
        messagebox.showinfo(
            "Excluir ano",
            f'{result["deleted"]} periodos do ano {result["ano"]} foram removidos.',
            parent=self,
        )

    def prepare_email(self) -> None:
        item = self._selected_queue_item()
        if not item:
            messagebox.showwarning(
                "Panorama",
                "A empresa selecionada nao possui cobranca ativa ate o periodo escolhido.",
                parent=self,
            )
            return
        try:
            draft = self.services.collection_service.build_email_draft(item)
        except ValidationError as exc:
            messagebox.showwarning("Panorama", str(exc), parent=self)
            return

        try:
            handler_name = open_email_draft(draft["to"], draft["subject"], draft["body"])
        except ValidationError as exc:
            messagebox.showwarning("Panorama", str(exc), parent=self)
            return

        messagebox.showinfo(
            "Panorama",
            f'O cliente de email configurado no sistema foi aberto com a mensagem preenchida.\n\nHandler: {handler_name}',
            parent=self,
        )

    def copy_whatsapp(self) -> None:
        item = self._selected_queue_item()
        if not item:
            messagebox.showwarning(
                "Panorama",
                "A empresa selecionada nao possui cobranca ativa ate o periodo escolhido.",
                parent=self,
            )
            return
        text = self.services.collection_service.build_whatsapp_message(item)
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("Panorama", "Mensagem copiada para a area de transferencia.", parent=self)

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
            messagebox.showerror("Panorama", str(exc), parent=self)
            return

        self._load_global_collection_settings()
        self.load_panorama()
        if self.on_data_changed:
            self.on_data_changed()
        self._set_global_config_mode("view")
        messagebox.showinfo("Panorama", "Regra global de cobranca salva com sucesso.", parent=self)

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


class PendingReportExportDialog(tk.Toplevel):
    SCOPE_ALL = "all"
    SCOPE_VISIBLE = "visible"
    SCOPE_SELECTED = "selected"
    FORMAT_PDF = "pdf"
    FORMAT_EXCEL = "excel"

    def __init__(
        self,
        parent: tk.Misc,
        services,
        *,
        periods_by_year: dict[int, list[dict]],
        period_map_by_year_month: dict[tuple[int, int], int],
        default_year: str,
        default_month: str,
        visible_company_ids: list[int],
    ) -> None:
        super().__init__(parent.winfo_toplevel())
        self.parent = parent
        self.services = services
        self.periods_by_year = periods_by_year
        self.period_map_by_year_month = period_map_by_year_month
        self.visible_company_ids = list(dict.fromkeys(visible_company_ids))
        self.selected_company_ids: list[int] = []

        self.start_period_var = tk.StringVar()
        self.end_period_var = tk.StringVar()
        self.company_scope_var = tk.StringVar(value=self.SCOPE_VISIBLE if self.visible_company_ids else self.SCOPE_ALL)
        self.company_summary_var = tk.StringVar()
        self.format_var = tk.StringVar(value=self.FORMAT_PDF)

        self.title("Exportar relatorio de pendencias")
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        apply_window_icon(self)
        configure_app_style(self)

        self._build_layout()
        self._set_default_period(default_year, default_month)
        self._refresh_company_summary()
        self.grab_set()
        self.after(10, self._center_on_parent)
        self.wait_visibility()

    def _build_layout(self) -> None:
        container = ttk.Frame(self, padding=14)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)

        period_box = ttk.LabelFrame(container, text="Periodo do relatorio", padding=10)
        period_box.grid(row=0, column=0, sticky="ew")

        period_box.columnconfigure(0, weight=1)
        period_box.columnconfigure(1, weight=1)
        ttk.Label(period_box, text="Periodo inicial (MM/AAAA)").grid(row=0, column=0, sticky="w")
        self.start_period_entry = ttk.Entry(
            period_box,
            textvariable=self.start_period_var,
            width=16,
        )
        self.start_period_entry.grid(row=1, column=0, sticky="ew", padx=(0, 12))
        self.start_period_entry.bind("<FocusOut>", lambda _event: self._normalize_period_entry(self.start_period_var))
        self.start_period_entry.bind("<Return>", lambda _event: self.end_period_entry.focus_set())

        ttk.Label(period_box, text="Periodo final (MM/AAAA, opcional)").grid(row=0, column=1, sticky="w")
        self.end_period_entry = ttk.Entry(
            period_box,
            textvariable=self.end_period_var,
            width=16,
        )
        self.end_period_entry.grid(row=1, column=1, sticky="ew")
        self.end_period_entry.bind("<FocusOut>", lambda _event: self._normalize_period_entry(self.end_period_var))
        self.end_period_entry.bind("<Return>", lambda _event: self._export())

        company_box = ttk.LabelFrame(container, text="Empresas", padding=10)
        company_box.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        company_box.columnconfigure(0, weight=1)
        ttk.Radiobutton(
            company_box,
            text="Todas as empresas",
            variable=self.company_scope_var,
            value=self.SCOPE_ALL,
            command=self._on_company_scope_changed,
        ).grid(row=0, column=0, sticky="w")
        self.visible_radio = ttk.Radiobutton(
            company_box,
            text="Somente empresas visiveis no Panorama",
            variable=self.company_scope_var,
            value=self.SCOPE_VISIBLE,
            command=self._on_company_scope_changed,
        )
        self.visible_radio.grid(row=1, column=0, sticky="w", pady=(4, 0))
        ttk.Radiobutton(
            company_box,
            text="Selecionar manualmente",
            variable=self.company_scope_var,
            value=self.SCOPE_SELECTED,
            command=self._on_company_scope_changed,
        ).grid(row=2, column=0, sticky="w", pady=(4, 0))
        self.select_companies_button = ttk.Button(
            company_box,
            text="Selecionar empresas...",
            command=self._select_companies,
            style="Secondary.TButton",
        )
        self.select_companies_button.grid(row=2, column=1, sticky="e", padx=(12, 0))
        ttk.Label(company_box, textvariable=self.company_summary_var, style="Muted.TLabel").grid(
            row=3,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(8, 0),
        )

        format_box = ttk.LabelFrame(container, text="Formato", padding=10)
        format_box.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        ttk.Radiobutton(format_box, text="PDF", variable=self.format_var, value=self.FORMAT_PDF).pack(side="left")
        ttk.Radiobutton(format_box, text="Excel", variable=self.format_var, value=self.FORMAT_EXCEL).pack(
            side="left",
            padx=(16, 0),
        )

        button_row = ttk.Frame(container)
        button_row.grid(row=3, column=0, sticky="e", pady=(14, 0))
        ttk.Button(button_row, text="Cancelar", command=self.destroy, style="Quiet.TButton").pack(side="right")
        export_button = ttk.Button(
            button_row,
            text="Exportar",
            command=self._export,
            style="Primary.TButton",
        )
        export_button.pack(side="right", padx=(0, 8))

        if not self.visible_company_ids:
            self.visible_radio.configure(state="disabled")
        self._on_company_scope_changed()

    def _set_default_period(self, default_year: str, default_month: str) -> None:
        default_value = self._period_label_from_parts(default_year, default_month)
        if self._period_id_from_label(default_value):
            self.start_period_var.set(default_value)
        else:
            period_values = self._period_values()
            self.start_period_var.set(period_values[-1] if period_values else "")
        self.end_period_var.set("")

    def _period_values(self) -> list[str]:
        values = []
        for year in sorted(self.periods_by_year):
            for period in self.periods_by_year[year]:
                values.append(self._period_label(period["ano"], period["mes"]))
        return values

    def _period_label(self, year: int, month: int) -> str:
        return f"{month:02d}/{year}"

    def _period_label_from_parts(self, year: str, month_label: str) -> str:
        year_value = str(year or "").strip()
        month_value = str(month_label or "").strip()
        if not year_value or not month_value:
            return ""
        try:
            month = int(month_value.split(" - ", 1)[0])
        except ValueError:
            return ""
        return self._period_label(int(year_value), month)

    def _period_id_from_label(self, value: str) -> int | None:
        raw_value = str(value or "").strip()
        if not raw_value:
            return None

        parsed = self._parse_period_value(raw_value)
        if not parsed:
            return None
        year, month = parsed
        return self.period_map_by_year_month.get((year, month))

    def _parse_period_value(self, value: str) -> tuple[int, int] | None:
        text = value.strip()
        if not text:
            return None

        digits = re.sub(r"\D", "", text)
        if len(digits) == 6:
            return int(digits[2:]), int(digits[:2])

        match = re.search(r"(?P<month>0?[1-9]|1[0-2])\s*/\s*(?P<year>\d{4})", text)
        if match:
            return int(match.group("year")), int(match.group("month"))

        match = re.search(r"(?P<year>\d{4})\s*[-/]\s*(?P<month>0?[1-9]|1[0-2])", text)
        if match:
            return int(match.group("year")), int(match.group("month"))

        match = re.search(r"(?P<year>\d{4})\s*-\s*(?P<month>0?[1-9]|1[0-2])", text)
        if match:
            return int(match.group("year")), int(match.group("month"))

        return None

    def _normalize_period_entry(self, variable: tk.StringVar) -> None:
        parsed = self._parse_period_value(variable.get())
        if not parsed:
            return

        year, month = parsed
        if (year, month) in self.period_map_by_year_month:
            variable.set(self._period_label(year, month))

    def _period_sort_key(self, period_id: int) -> int | None:
        for (year, month), mapped_period_id in self.period_map_by_year_month.items():
            if mapped_period_id == period_id:
                return (year * 100) + month
        return None

    def _on_company_scope_changed(self) -> None:
        manual = self.company_scope_var.get() == self.SCOPE_SELECTED
        self.select_companies_button.configure(state="normal" if manual else "disabled")
        self._refresh_company_summary()

    def _refresh_company_summary(self) -> None:
        scope = self.company_scope_var.get()
        if scope == self.SCOPE_ALL:
            self.company_summary_var.set("Todas as empresas ativas e inativas serao consideradas.")
            return
        if scope == self.SCOPE_VISIBLE:
            self.company_summary_var.set(f"{len(self.visible_company_ids)} empresa(s) visivel(is) no filtro atual.")
            return
        if not self.selected_company_ids:
            self.company_summary_var.set("Nenhuma empresa selecionada.")
            return

        companies = self.services.empresa_service.list_empresas(active_only=False)
        available_by_id = {company["id"]: company for company in companies}
        selected = [available_by_id[company_id] for company_id in self.selected_company_ids if company_id in available_by_id]
        selected.sort(key=lambda item: (item["codigo_empresa"], item["nome_empresa"].casefold()))
        if len(selected) == 1:
            company = selected[0]
            self.company_summary_var.set(f'Empresa selecionada: {company["codigo_empresa"]} - {company["nome_empresa"]}')
            return
        preview = ", ".join(company["nome_empresa"] for company in selected[:3])
        if len(selected) > 3:
            preview += f" e mais {len(selected) - 3}"
        self.company_summary_var.set(f"{len(selected)} empresas selecionadas: {preview}.")

    def _select_companies(self) -> None:
        companies = self.services.empresa_service.list_empresas(active_only=False)
        dialog = CompanyMultiSelectDialog(
            self,
            companies,
            selected_company_ids=self.selected_company_ids,
            title="Selecionar empresas para o relatorio",
        )
        self.wait_window(dialog)
        self.selected_company_ids = dialog.selected_company_ids
        self._refresh_company_summary()

    def _parse_period_ids(self) -> tuple[int, int] | None:
        start_period_id = self._period_id_from_label(self.start_period_var.get())
        if not start_period_id:
            messagebox.showwarning("Relatorio", "Informe o periodo inicial no formato MM/AAAA.", parent=self)
            self.start_period_entry.focus_set()
            return None

        end_text = self.end_period_var.get().strip()
        end_period_id = self._period_id_from_label(end_text) if end_text else start_period_id
        if not end_period_id:
            messagebox.showwarning("Relatorio", "Informe um periodo final cadastrado no formato MM/AAAA.", parent=self)
            self.end_period_entry.focus_set()
            return None

        start_key = self._period_sort_key(start_period_id)
        end_key = self._period_sort_key(end_period_id)
        if start_key is not None and end_key is not None and end_key < start_key:
            messagebox.showwarning("Relatorio", "O periodo final nao pode ser anterior ao inicial.", parent=self)
            self.end_period_entry.focus_set()
            return None

        self._normalize_period_entry(self.start_period_var)
        self._normalize_period_entry(self.end_period_var)
        return start_period_id, end_period_id

    def _resolve_company_ids(self) -> list[int] | None:
        scope = self.company_scope_var.get()
        if scope == self.SCOPE_ALL:
            return None
        if scope == self.SCOPE_VISIBLE:
            if not self.visible_company_ids:
                messagebox.showwarning("Relatorio", "Nao ha empresas visiveis no filtro atual.", parent=self)
                return []
            return self.visible_company_ids
        if not self.selected_company_ids:
            messagebox.showwarning("Relatorio", "Selecione pelo menos uma empresa.", parent=self)
            return []
        return self.selected_company_ids

    def _export(self) -> None:
        period_ids = self._parse_period_ids()
        if not period_ids:
            return
        company_ids = self._resolve_company_ids()
        if company_ids == []:
            return

        export_format = self.format_var.get()
        is_pdf = export_format == self.FORMAT_PDF
        file_path = filedialog.asksaveasfilename(
            parent=self,
            title="Salvar relatorio de pendencias em PDF" if is_pdf else "Salvar relatorio de pendencias",
            defaultextension=".pdf" if is_pdf else ".xlsx",
            filetypes=[("Arquivos PDF", "*.pdf"), ("Todos os arquivos", "*.*")]
            if is_pdf
            else [("Arquivos Excel", "*.xlsx"), ("Todos os arquivos", "*.*")],
            initialfile="relatorio_pendencias.pdf" if is_pdf else "relatorio_pendencias.xlsx",
        )
        if not file_path:
            return

        start_period_id, end_period_id = period_ids
        try:
            if is_pdf:
                result = self.services.pending_report_service.export_pending_report_pdf(
                    file_path,
                    company_ids,
                    start_period_id,
                    end_period_id,
                )
            else:
                result = self.services.pending_report_service.export_pending_report(
                    file_path,
                    company_ids,
                    start_period_id,
                    end_period_id,
                )
        except ValidationError as exc:
            messagebox.showwarning("Relatorio", str(exc), parent=self)
            return

        file_kind = "PDF" if is_pdf else "Excel"
        messagebox.showinfo(
            "Relatorio",
            (
                f"Relatorio {file_kind} exportado com sucesso.\n"
                f'Empresas consideradas: {result["company_count"]}\n'
                f'Empresas com pendencias: {result["pending_company_count"]}\n'
                f'Linhas exportadas: {result["rows"]}'
            ),
            parent=self,
        )
        self.destroy()

    def _center_on_parent(self) -> None:
        self.update_idletasks()
        parent = self.parent.winfo_toplevel()
        x = parent.winfo_rootx() + max((parent.winfo_width() - self.winfo_width()) // 2, 0)
        y = parent.winfo_rooty() + max((parent.winfo_height() - self.winfo_height()) // 2, 0)
        self.geometry(f"+{x}+{y}")
