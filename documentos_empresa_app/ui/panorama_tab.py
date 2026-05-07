from __future__ import annotations

from datetime import datetime
import tkinter as tk
from tkinter import messagebox, ttk

from documentos_empresa_app.services.panorama_service import PanoramaService
from documentos_empresa_app.utils.common import MONTH_NAMES
from documentos_empresa_app.utils.helpers import ValidationError


class PanoramaTab(ttk.Frame):
    ALL_SITUATIONS = "Todas"
    WORK_QUEUE = "Fila de trabalho"
    WORK_QUEUE_KEYS = {
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
        self.current_rows: list[dict] = []

        self.year_var = tk.StringVar()
        self.month_var = tk.StringVar()
        self.situation_var = tk.StringVar(value=self.ALL_SITUATIONS)
        self.search_var = tk.StringVar()
        self.active_only_var = tk.BooleanVar(value=True)
        self.summary_var = tk.StringVar(value="Selecione um periodo para carregar a conferencia mensal.")
        self.company_code_sort_desc: bool | None = None

        self.situation_key_by_label = {
            label: key for key, label in PanoramaService.SITUATION_LABELS.items()
        }

        self._build_layout()

    def _build_layout(self) -> None:
        filter_frame = ttk.LabelFrame(self, text="Conferencia mensal", padding=10)
        filter_frame.pack(fill="x", pady=(0, 8))
        filter_frame.columnconfigure(4, weight=1)

        ttk.Label(filter_frame, text="Ano").grid(row=0, column=0, sticky="w")
        self.year_combo = ttk.Combobox(filter_frame, textvariable=self.year_var, state="readonly", width=14)
        self.year_combo.grid(row=1, column=0, sticky="w", padx=(0, 10))
        self.year_combo.bind("<<ComboboxSelected>>", lambda _event: self._on_year_changed())

        ttk.Label(filter_frame, text="Mes").grid(row=0, column=1, sticky="w")
        self.month_combo = ttk.Combobox(filter_frame, textvariable=self.month_var, state="readonly", width=20)
        self.month_combo.grid(row=1, column=1, sticky="w", padx=(0, 10))

        ttk.Label(filter_frame, text="Situacao").grid(row=0, column=2, sticky="w")
        self.situation_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.situation_var,
            state="readonly",
            width=20,
            values=[self.ALL_SITUATIONS, self.WORK_QUEUE, *PanoramaService.SITUATION_LABELS.values()],
        )
        self.situation_combo.grid(row=1, column=2, sticky="w", padx=(0, 10))
        self.situation_combo.bind("<<ComboboxSelected>>", lambda _event: self._populate_tree())

        ttk.Label(filter_frame, text="Buscar empresa").grid(row=0, column=3, sticky="w")
        search_entry = ttk.Entry(filter_frame, textvariable=self.search_var, width=28)
        search_entry.grid(row=1, column=3, sticky="ew", padx=(0, 10))
        search_entry.bind("<KeyRelease>", lambda _event: self._populate_tree())

        action_frame = ttk.Frame(filter_frame)
        action_frame.grid(row=1, column=4, sticky="w")
        ttk.Checkbutton(
            action_frame,
            text="Somente ativas",
            variable=self.active_only_var,
            command=self.load_panorama,
        ).pack(side="left", padx=(0, 8))
        ttk.Button(action_frame, text="Atualizar", command=self.load_panorama).pack(side="left", padx=(0, 8))
        ttk.Button(action_frame, text="Limpar busca", command=self.clear_search).pack(side="left", padx=(0, 8))
        ttk.Button(action_frame, text="Abrir no Controle", command=self.open_selected_company).pack(side="left")

        ttk.Label(self, textvariable=self.summary_var).pack(fill="x", pady=(0, 8))

        list_frame = ttk.LabelFrame(self, text="Empresas", padding=10)
        list_frame.pack(fill="both", expand=True)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            list_frame,
            columns=(
                "codigo",
                "empresa",
                "situacao",
                "progresso",
                "mes_anterior",
                "recebidos",
                "pendentes",
                "faltando",
                "ultima_marcacao",
            ),
            show="headings",
            selectmode="browse",
        )
        self.tree.heading("codigo", text="Codigo")
        self.tree.heading("empresa", text="Empresa")
        self.tree.heading("situacao", text="Situacao")
        self.tree.heading("progresso", text="Progresso")
        self.tree.heading("mes_anterior", text="Mes anterior")
        self.tree.heading("recebidos", text="Recebidos")
        self.tree.heading("pendentes", text="Pendentes")
        self.tree.heading("faltando", text="Faltando")
        self.tree.heading("ultima_marcacao", text="Ultima marcacao")
        self.tree.column("codigo", width=100, anchor="center")
        self.tree.column("empresa", width=340)
        self.tree.column("situacao", width=150, anchor="center")
        self.tree.column("progresso", width=100, anchor="center")
        self.tree.column("mes_anterior", width=110, anchor="center")
        self.tree.column("recebidos", width=100, anchor="center")
        self.tree.column("pendentes", width=100, anchor="center")
        self.tree.column("faltando", width=100, anchor="center")
        self.tree.column("ultima_marcacao", width=210, anchor="center")
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<Double-1>", self._on_tree_double_click)
        self.tree.bind("<Return>", lambda _event: self.open_selected_company())

        scrollbar_y = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x = ttk.Scrollbar(list_frame, orient="horizontal", command=self.tree.xview)
        scrollbar_x.grid(row=1, column=0, sticky="ew")
        self.tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        self._configure_tree_tags()

    def _configure_tree_tags(self) -> None:
        self.tree.tag_configure(PanoramaService.SITUATION_SEM_DOCUMENTOS, background="#EDEDED")
        self.tree.tag_configure(PanoramaService.SITUATION_SEM_COBRANCA, background="#F6EFC7")
        self.tree.tag_configure(PanoramaService.SITUATION_NAO_INICIADA, background="#FCE4D6")
        self.tree.tag_configure(PanoramaService.SITUATION_EM_ANDAMENTO, background="#D9EAF7")
        self.tree.tag_configure(PanoramaService.SITUATION_COM_PENDENCIA, background="#FAD4D4")
        self.tree.tag_configure(PanoramaService.SITUATION_CONCLUIDA, background="#D9F2D9")

    def refresh_data(self) -> None:
        selected_period_id = self._selected_period_id()
        self._load_period_options()

        if selected_period_id and self._set_period_by_id(selected_period_id):
            self.load_panorama()
            return

        if self._select_default_period():
            self.load_panorama()
            return

        self.current_rows = []
        self.tree.delete(*self.tree.get_children())
        self.summary_var.set("Nenhum periodo cadastrado para carregar a conferencia mensal.")

    def _load_period_options(self) -> None:
        periodos = self.services.periodo_service.list_periodos()
        self.periods_by_year = {}
        self.period_map_by_year_month = {}

        for periodo in periodos:
            self.periods_by_year.setdefault(periodo["ano"], []).append(periodo)
            self.period_map_by_year_month[(periodo["ano"], periodo["mes"])] = periodo["id"]

        for items in self.periods_by_year.values():
            items.sort(key=lambda item: item["mes"])

        year_values = [str(year) for year in sorted(self.periods_by_year)]
        self.year_combo["values"] = year_values
        if self.year_var.get() not in year_values:
            self.year_var.set("")
        self._sync_month_values()

    def _select_default_period(self) -> bool:
        if not self.period_map_by_year_month:
            self.year_var.set("")
            self.month_var.set("")
            return False

        today = datetime.now()
        default_key = (today.year, today.month)
        if default_key not in self.period_map_by_year_month:
            default_key = max(self.period_map_by_year_month)

        year, month = default_key
        self.year_var.set(str(year))
        self._sync_month_values()
        self.month_var.set(self._month_label(month))
        return True

    def _set_period_by_id(self, periodo_id: int) -> bool:
        for year, periodos in self.periods_by_year.items():
            for periodo in periodos:
                if periodo["id"] != periodo_id:
                    continue
                self.year_var.set(str(year))
                self._sync_month_values()
                self.month_var.set(self._month_label(periodo["mes"]))
                return True
        return False

    def _on_year_changed(self) -> None:
        previous_month = self.month_var.get()
        self._sync_month_values()
        if (not self.month_var.get() or self.month_var.get() != previous_month) and self.month_combo["values"]:
            self.month_var.set(self.month_combo["values"][0])

    def _sync_month_values(self) -> None:
        year_value = self.year_var.get().strip()
        if not year_value:
            self.month_combo["values"] = []
            self.month_var.set("")
            return

        try:
            year_int = int(year_value)
        except ValueError:
            self.month_combo["values"] = []
            self.month_var.set("")
            return

        months = [self._month_label(periodo["mes"]) for periodo in self.periods_by_year.get(year_int, [])]
        self.month_combo["values"] = months
        if self.month_var.get() not in months:
            self.month_var.set("")

    def _month_label(self, month: int) -> str:
        return f"{month:02d} - {MONTH_NAMES[month]}"

    def _selected_period_id(self) -> int | None:
        year_value = self.year_var.get().strip()
        month_value = self.month_var.get().strip()
        if not year_value or not month_value:
            return None
        try:
            year = int(year_value)
            month = int(month_value.split(" - ", 1)[0])
        except ValueError:
            return None
        return self.period_map_by_year_month.get((year, month))

    def load_panorama(self) -> None:
        period_id = self._selected_period_id()
        if not period_id:
            messagebox.showwarning("Panorama", "Selecione ano e mes para carregar a conferencia.", parent=self)
            return

        try:
            view = self.services.panorama_service.build_monthly_view(
                period_id,
                active_only=self.active_only_var.get(),
            )
        except ValidationError as exc:
            messagebox.showerror("Panorama", str(exc), parent=self)
            return

        self.current_rows = view["rows"]
        self._populate_tree()

    def _populate_tree(self) -> None:
        if not hasattr(self, "tree"):
            return

        self.tree.delete(*self.tree.get_children())
        filtered_rows = self._filtered_rows()
        filtered_rows = self._sorted_rows(filtered_rows)

        for row in filtered_rows:
            progress = f'{row["marcados"]}/{row["total_cobravel"]}'
            company_name = row["nome_empresa"] if row["ativa"] else f'{row["nome_empresa"]} [Inativa]'
            self.tree.insert(
                "",
                "end",
                iid=str(row["empresa_id"]),
                values=(
                    row["codigo_empresa"],
                    company_name,
                    row["situacao"],
                    progress,
                    self._format_previous_progress(row),
                    row["recebidos"],
                    row["pendentes"],
                    row["faltando"],
                    self._format_last_marker(row),
                ),
                tags=(row["situacao_key"],),
            )

        self._update_summary(filtered_rows)

    def _filtered_rows(self) -> list[dict]:
        search = self.search_var.get().strip().casefold()
        situation_key = self.situation_key_by_label.get(self.situation_var.get())
        work_queue_only = self.situation_var.get() == self.WORK_QUEUE

        rows = []
        for row in self.current_rows:
            if work_queue_only and row["situacao_key"] not in self.WORK_QUEUE_KEYS:
                continue
            if situation_key and row["situacao_key"] != situation_key:
                continue

            company_text = f'{row["codigo_empresa"]} {row["nome_empresa"]}'.casefold()
            if search and search not in company_text:
                continue

            rows.append(row)
        return rows

    def _sorted_rows(self, rows: list[dict]) -> list[dict]:
        if self.company_code_sort_desc is None:
            return rows
        return sorted(
            rows,
            key=lambda row: (row["codigo_empresa"], row["nome_empresa"].casefold()),
            reverse=self.company_code_sort_desc,
        )

    def toggle_company_code_sort(self) -> None:
        self.company_code_sort_desc = False if self.company_code_sort_desc is None else not self.company_code_sort_desc
        direction = "v" if self.company_code_sort_desc else "^"
        self.tree.heading("codigo", text=f"Codigo {direction}")
        self._populate_tree()

    def _format_previous_progress(self, row: dict) -> str:
        previous_marcados = row.get("previous_marcados")
        previous_total = row.get("previous_total_cobravel")
        if previous_marcados is None or previous_total is None:
            return "-"
        return f"{previous_marcados}/{previous_total}"

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

        period_label = self.month_var.get().split(" - ", 1)[0]
        if self.year_var.get():
            period_label = f"{period_label}/{self.year_var.get()}"

        counts = {key: 0 for key in PanoramaService.SITUATION_LABELS}
        for row in filtered_rows:
            counts[row["situacao_key"]] += 1

        parts = [
            f'{PanoramaService.SITUATION_LABELS[key]}: {counts[key]}'
            for key in (
                PanoramaService.SITUATION_COM_PENDENCIA,
                PanoramaService.SITUATION_EM_ANDAMENTO,
                PanoramaService.SITUATION_NAO_INICIADA,
                PanoramaService.SITUATION_SEM_DOCUMENTOS,
                PanoramaService.SITUATION_CONCLUIDA,
                PanoramaService.SITUATION_SEM_COBRANCA,
            )
        ]
        self.summary_var.set(
            f"{len(filtered_rows)} de {len(self.current_rows)} empresa(s) em {period_label}. "
            + " | ".join(parts)
        )

    def clear_search(self) -> None:
        self.search_var.set("")
        self.situation_var.set(self.ALL_SITUATIONS)
        self._populate_tree()

    def _on_tree_double_click(self, event: tk.Event) -> str | None:
        if self.tree.identify_region(event.x, event.y) == "heading":
            if self.tree.identify_column(event.x) == "#1":
                self.toggle_company_code_sort()
            return "break"
        return self.open_selected_company()

    def open_selected_company(self) -> str | None:
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Panorama", "Selecione uma empresa para abrir no Controle.", parent=self)
            return "break"

        period_id = self._selected_period_id()
        if not period_id:
            messagebox.showwarning("Panorama", "Selecione ano e mes antes de abrir no Controle.", parent=self)
            return "break"

        if not self.on_open_control:
            return "break"

        self.on_open_control(int(selection[0]), period_id)
        return "break"
