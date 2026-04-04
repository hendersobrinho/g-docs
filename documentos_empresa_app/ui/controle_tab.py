from __future__ import annotations

from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from documentos_empresa_app.utils.helpers import (
    CompanySelector,
    MONTH_NAMES,
    STATUS_COLORS,
    STATUS_OPTIONS,
    ScrollableFrame,
    ValidationError,
)


class ControleTab(ttk.Frame):
    def __init__(self, master, services, on_data_changed) -> None:
        super().__init__(master, padding=12)
        self.services = services
        self.on_data_changed = on_data_changed
        self.period_map_by_year_month: dict[tuple[int, int], int] = {}
        self.periods_by_year: dict[int, list[dict]] = {}
        self.current_filters: dict | None = None
        self.current_view: dict | None = None
        self.collapsed_groups: dict[str, bool] = {}
        self.group_widgets: dict[str, dict] = {}
        self.document_rows: dict[int, dict] = {}
        self.document_column_width = 320
        self.document_name_labels: list[tk.Label] = []
        self.document_header_frame: tk.Frame | None = None
        self._resize_start_x: int | None = None
        self._resize_start_width: int | None = None
        self.bulk_mode_enabled = False
        self.bulk_selection_vars: dict[int, tk.BooleanVar] = {}
        self.bulk_period_options: dict[str, int] = {}
        self.bulk_status_options = {
            "Recebido": "Recebido",
            "Pendente": "Pendente",
            "Encerrado": "Encerrado",
            "Nao cobrar": "Nao cobrar",
            "Limpar status": "",
        }
        self._bulk_selection_updates_suspended = False
        self.default_message_text = "Selecione a empresa e o intervalo para consultar."

        self.start_year_var = tk.StringVar()
        self.start_month_var = tk.StringVar()
        self.end_year_var = tk.StringVar()
        self.end_month_var = tk.StringVar()
        self.message_var = tk.StringVar(value=self.default_message_text)
        self.bulk_period_var = tk.StringVar()
        self.bulk_status_var = tk.StringVar()
        self.bulk_selection_summary_var = tk.StringVar(value="Nenhum documento selecionado.")

        self._build_layout()

    def _build_layout(self) -> None:
        top = ttk.Frame(self)
        top.pack(fill="x", pady=(0, 10))

        self.company_selector = CompanySelector(
            top,
            self.services.empresa_service,
            active_only=True,
            on_selected=self.on_company_selected,
            on_cleared=self._clear_company_directory_context,
        )
        self.company_selector.pack(fill="x", pady=(0, 10))

        period_frame = ttk.LabelFrame(top, text="Periodo da consulta", padding=12)
        period_frame.pack(fill="x")

        ttk.Label(period_frame, text="Ano inicial").grid(row=0, column=0, sticky="w")
        self.start_year_combo = ttk.Combobox(period_frame, textvariable=self.start_year_var, state="readonly", width=16)
        self.start_year_combo.grid(row=1, column=0, sticky="w", padx=(0, 10))
        self.start_year_combo.bind("<<ComboboxSelected>>", lambda _event: self._on_year_changed("start"))

        ttk.Label(period_frame, text="Mes inicial").grid(row=0, column=1, sticky="w")
        self.start_month_combo = ttk.Combobox(period_frame, textvariable=self.start_month_var, state="readonly", width=20)
        self.start_month_combo.grid(row=1, column=1, sticky="w", padx=(0, 10))

        ttk.Label(period_frame, text="Mes final (opcional)").grid(row=0, column=2, sticky="w")
        self.end_month_combo = ttk.Combobox(period_frame, textvariable=self.end_month_var, state="readonly", width=20)
        self.end_month_combo.grid(row=1, column=2, sticky="w", padx=(0, 10))

        ttk.Label(period_frame, text="Ano final (opcional)").grid(row=0, column=3, sticky="w")
        self.end_year_combo = ttk.Combobox(period_frame, textvariable=self.end_year_var, state="readonly", width=16)
        self.end_year_combo.grid(row=1, column=3, sticky="w", padx=(0, 10))
        self.end_year_combo.bind("<<ComboboxSelected>>", lambda _event: self._on_year_changed("end"))

        action_frame = ttk.Frame(period_frame)
        action_frame.grid(row=1, column=4, columnspan=3, sticky="w")
        ttk.Button(action_frame, text="Consultar", command=self.consult).pack(side="left")
        ttk.Button(action_frame, text="Limpar filtros", command=self.clear_filters).pack(side="left", padx=(6, 0))
        self.directory_button = ttk.Button(
            action_frame,
            text="Abrir pasta...",
            command=self.open_company_directory_browser,
        )
        self.directory_button.pack(side="left", padx=(6, 0))
        ttk.Label(period_frame, text="Limite maximo de 12 meses por consulta.").grid(
            row=2, column=0, columnspan=7, sticky="w", pady=(8, 0)
        )

        legend = ttk.Frame(self)
        legend.pack(fill="x", pady=(0, 10))
        legend_left = ttk.Frame(legend)
        legend_left.pack(side="left")
        ttk.Label(legend_left, text="Legenda:").pack(side="left")
        self._legend_chip(legend_left, "Recebido").pack(side="left", padx=(8, 4))
        self._legend_chip(legend_left, "Pendente").pack(side="left", padx=4)
        self._legend_chip(legend_left, "Encerrado").pack(side="left", padx=4)
        self._legend_chip(legend_left, "Nao cobrar").pack(side="left", padx=4)
        self.bulk_mode_button = ttk.Button(
            legend,
            text="Selecao em lote",
            command=self.toggle_bulk_selection_mode,
            state="disabled",
        )
        self.bulk_mode_button.pack(side="right")

        ttk.Label(self, textvariable=self.message_var).pack(fill="x", pady=(0, 8))

        result_frame = ttk.LabelFrame(self, text="Consulta e controle mensal", padding=10)
        result_frame.pack(fill="both", expand=True)
        self.bulk_panel = ttk.Frame(result_frame)
        ttk.Label(self.bulk_panel, textvariable=self.bulk_selection_summary_var).grid(
            row=0, column=0, sticky="w", padx=(0, 12), pady=(0, 6)
        )
        self.bulk_select_all_button = ttk.Button(
            self.bulk_panel,
            text="Marcar todos",
            command=self.select_all_documents_in_bulk,
        )
        self.bulk_select_all_button.grid(row=0, column=1, sticky="w", padx=(0, 6), pady=(0, 6))
        self.bulk_clear_button = ttk.Button(
            self.bulk_panel,
            text="Limpar selecao",
            command=self.clear_bulk_selection,
        )
        self.bulk_clear_button.grid(row=0, column=2, sticky="w", pady=(0, 6))
        ttk.Label(self.bulk_panel, text="Periodo").grid(row=1, column=0, sticky="w", padx=(0, 6))
        self.bulk_period_combo = ttk.Combobox(
            self.bulk_panel,
            textvariable=self.bulk_period_var,
            state="readonly",
            width=24,
        )
        self.bulk_period_combo.grid(row=1, column=1, sticky="w", padx=(0, 12))
        ttk.Label(self.bulk_panel, text="Status").grid(row=1, column=2, sticky="w", padx=(0, 6))
        self.bulk_status_combo = ttk.Combobox(
            self.bulk_panel,
            textvariable=self.bulk_status_var,
            state="readonly",
            width=18,
            values=list(self.bulk_status_options),
        )
        self.bulk_status_combo.grid(row=1, column=3, sticky="w", padx=(0, 12))
        self.bulk_apply_button = ttk.Button(
            self.bulk_panel,
            text="Aplicar nos selecionados",
            command=self.apply_bulk_status,
        )
        self.bulk_apply_button.grid(row=1, column=4, sticky="w")
        self.scrollable = ScrollableFrame(result_frame)
        self.scrollable.pack(fill="both", expand=True)
        self.bulk_panel.grid_columnconfigure(4, weight=1)
        self._set_directory_actions_enabled(False)
        self._update_bulk_controls_state()

    def _legend_chip(self, master, text: str):
        chip = tk.Label(master, text=f" {text} ", bg=STATUS_COLORS[text], relief="solid", bd=1)
        return chip

    def _show_bulk_panel(self) -> None:
        if self.bulk_panel.winfo_manager() != "pack":
            self.bulk_panel.pack(fill="x", pady=(0, 8), before=self.scrollable)

    def _hide_bulk_panel(self) -> None:
        if self.bulk_panel.winfo_manager():
            self.bulk_panel.pack_forget()

    def _clear_bulk_context(self) -> None:
        self.bulk_mode_enabled = False
        self.bulk_selection_vars = {}
        self.bulk_period_options = {}
        self.bulk_period_var.set("")
        self.bulk_status_var.set("")
        self.bulk_selection_summary_var.set("Nenhum documento selecionado.")
        self.bulk_mode_button.configure(text="Selecao em lote", state="disabled")
        self._hide_bulk_panel()
        self._update_bulk_controls_state()

    def refresh_data(self) -> None:
        self.company_selector.refresh_companies()
        self._set_directory_actions_enabled(bool(self.company_selector.get_selected_company_id()))
        self._load_period_options()
        if self.current_filters:
            company_id = self.current_filters.get("company_id")
            start_period_id = self.current_filters.get("start_period_id")
            end_period_id = self.current_filters.get("end_period_id")
            if company_id and start_period_id and end_period_id:
                try:
                    self.company_selector.set_company(company_id)
                    self._set_period_filter_values(start_period_id, end_period_id)
                except ValidationError:
                    self.current_filters = None
                    self.current_view = None
                    self._clear_bulk_context()
                    self._set_default_message("Selecione a empresa e o intervalo para consultar.")
                    self._clear_result_area()
        else:
            self._clear_invalid_selections()

    def on_company_selected(self, company: dict) -> None:
        _ = company
        self._set_directory_actions_enabled(True)

    def _clear_company_directory_context(self) -> None:
        self._set_directory_actions_enabled(False)

    def _set_directory_actions_enabled(self, enabled: bool) -> None:
        self.directory_button.configure(state="normal" if enabled else "disabled")

    def _get_selected_company(self) -> dict | None:
        company_id = self.company_selector.get_selected_company_id()
        if not company_id:
            return None
        return self.services.empresa_service.get_empresa(company_id)

    def open_company_directory_browser(self) -> None:
        company = self._get_selected_company()
        if not company:
            messagebox.showwarning("Controle", "Selecione uma empresa antes de vincular uma pasta.", parent=self)
            return

        current_directory = str(company.get("diretorio_documentos") or "").strip()
        initial_directory = (
            current_directory if current_directory and Path(current_directory).is_dir() else str(Path.home())
        )
        selected_directory = filedialog.askdirectory(
            parent=self,
            title=f'Escolha a pasta para "{company["nome_empresa"]}"',
            initialdir=initial_directory,
            mustexist=True,
        )
        if not selected_directory:
            return

        self.services.empresa_service.set_empresa_directory(company["id"], selected_directory)

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
        self.start_year_combo["values"] = year_values
        self.end_year_combo["values"] = year_values

        self._sync_month_values("start")
        self._sync_month_values("end")

    def _set_period_filter_values(self, start_period_id: int, end_period_id: int) -> None:
        start_period = self.services.periodo_service.get_periodo(start_period_id)
        end_period = self.services.periodo_service.get_periodo(end_period_id)

        self.start_year_var.set(str(start_period["ano"]))
        self.end_year_var.set(str(end_period["ano"]))
        self._sync_month_values("start")
        self._sync_month_values("end")
        self.start_month_var.set(self._month_label(start_period["mes"]))
        self.end_month_var.set(self._month_label(end_period["mes"]))

    def _clear_invalid_selections(self) -> None:
        valid_years = set(self.start_year_combo["values"])
        if self.start_year_var.get() not in valid_years:
            self.start_year_var.set("")
        if self.end_year_var.get() not in valid_years:
            self.end_year_var.set("")
        self._sync_month_values("start")
        self._sync_month_values("end")

    def _on_year_changed(self, side: str) -> None:
        if side == "start" and self.start_year_var.get() and not self.end_year_var.get():
            self.end_year_var.set(self.start_year_var.get())
        if side == "end" and self.end_year_var.get() and not self.start_year_var.get():
            self.start_year_var.set(self.end_year_var.get())

        self._sync_month_values("start")
        self._sync_month_values("end")

    def _sync_month_values(self, side: str) -> None:
        year_var = self.start_year_var if side == "start" else self.end_year_var
        month_var = self.start_month_var if side == "start" else self.end_month_var
        month_combo = self.start_month_combo if side == "start" else self.end_month_combo

        year_value = year_var.get().strip()
        if not year_value:
            month_combo["values"] = []
            month_var.set("")
            return

        try:
            year_int = int(year_value)
        except ValueError:
            month_combo["values"] = []
            month_var.set("")
            return

        months = [self._month_label(periodo["mes"]) for periodo in self.periods_by_year.get(year_int, [])]
        month_combo["values"] = months
        if month_var.get() not in months:
            month_var.set("")

    def _label_for_period(self, period_id: int) -> str:
        periodo = self.services.periodo_service.get_periodo(period_id)
        return periodo["label"]

    def _month_label(self, month: int) -> str:
        return f"{month:02d} - {MONTH_NAMES[month]}"

    def _parse_selected_period_ids(self) -> tuple[int, int] | None:
        start_year = self.start_year_var.get().strip()
        end_year = self.end_year_var.get().strip()
        start_month = self.start_month_var.get().strip()
        end_month = self.end_month_var.get().strip()

        if start_year and not end_year:
            end_year = start_year
            self.end_year_var.set(end_year)
            self._sync_month_values("end")
        elif end_year and not start_year:
            start_year = end_year
            self.start_year_var.set(start_year)
            self._sync_month_values("start")

        if not start_year or not end_year:
            messagebox.showwarning("Controle", "Selecione pelo menos um ano para a consulta.", parent=self)
            return None

        if start_month and not end_month:
            end_month = start_month
            self.end_month_var.set(end_month)
        elif end_month and not start_month:
            start_month = end_month
            self.start_month_var.set(start_month)

        if not start_month or not end_month:
            messagebox.showwarning(
                "Controle",
                "Selecione pelo menos um mes para a consulta. O mes final e opcional.",
                parent=self,
            )
            return None

        start_year_int = int(start_year)
        end_year_int = int(end_year)
        start_month_int = int(start_month.split(" - ", 1)[0])
        end_month_int = int(end_month.split(" - ", 1)[0])

        start_period_id = self.period_map_by_year_month.get((start_year_int, start_month_int))
        end_period_id = self.period_map_by_year_month.get((end_year_int, end_month_int))
        if not start_period_id or not end_period_id:
            messagebox.showwarning(
                "Controle",
                "Nao foi possivel localizar os periodos escolhidos. Verifique os anos e meses selecionados.",
                parent=self,
            )
            return None
        return start_period_id, end_period_id

    def clear_filters(self) -> None:
        self.current_filters = None
        self.current_view = None
        self._clear_bulk_context()
        self.company_selector.clear_selection()
        self.start_year_var.set("")
        self.start_month_var.set("")
        self.end_year_var.set("")
        self.end_month_var.set("")
        self._sync_month_values("start")
        self._sync_month_values("end")
        self._set_default_message("Selecione a empresa e o intervalo para consultar.")
        self._clear_result_area()

    def consult(
        self,
        *,
        preserve_scroll: bool = False,
        scroll_position: float | None = None,
    ) -> None:
        company_id = self.company_selector.get_selected_company_id()
        if not company_id:
            messagebox.showwarning("Controle", "Selecione uma empresa ativa para consultar.", parent=self)
            return

        period_ids = self._parse_selected_period_ids()
        if not period_ids:
            return
        start_period_id, end_period_id = period_ids

        if preserve_scroll and scroll_position is None:
            scroll_position = self._get_scroll_position()

        self.current_filters = {
            "company_id": company_id,
            "start_period_id": start_period_id,
            "end_period_id": end_period_id,
        }
        self._reload_current_view(scroll_position=scroll_position)

    def _reload_current_view(self, scroll_position: float | None = None) -> bool:
        if not self.current_filters:
            return False

        company_id = self.current_filters.get("company_id")
        start_period_id = self.current_filters.get("start_period_id")
        end_period_id = self.current_filters.get("end_period_id")
        if not company_id or not start_period_id or not end_period_id:
            return False

        try:
            view = self.services.status_service.build_control_view(company_id, start_period_id, end_period_id)
        except ValidationError as exc:
            messagebox.showerror("Controle", str(exc), parent=self)
            return False

        self.render_result(view, scroll_position=scroll_position)
        return True

    def render_result(self, view: dict, scroll_position: float | None = None) -> None:
        self.current_view = view
        self._clear_result_area()
        self.document_name_labels = []
        self.document_header_frame = None
        self.group_widgets = {}
        self.document_rows = {}

        periodos = view["periodos"]
        groups = view["groups"]
        if not groups:
            self._clear_bulk_context()
            self._set_default_message("Nenhum documento encontrado para a empresa e periodo informados.")
            ttk.Label(self.scrollable.inner, text="Nenhum documento encontrado para a consulta.").grid(
                row=0, column=0, sticky="w", padx=6, pady=6
            )
            self._restore_scroll_position(scroll_position)
            return

        self._sync_bulk_selection_with_view(view)
        self._refresh_bulk_period_options(view)
        self.bulk_mode_button.configure(
            state="normal",
            text="Fechar lote" if self.bulk_mode_enabled else "Selecao em lote",
        )
        if self.bulk_mode_enabled:
            self._show_bulk_panel()
        else:
            self._hide_bulk_panel()
        self._update_bulk_controls_state()

        self._set_default_message(
            f'Empresa consultada: {view["empresa"]["nome_empresa"]}. Clique nos grupos para expandir ou recolher.'
        )

        header_bg = "#1F4E79"
        header_frame = tk.Frame(
            self.scrollable.inner,
            bg=header_bg,
            relief="solid",
            bd=1,
            width=self.document_column_width,
            height=52,
        )
        header_frame.grid(row=0, column=0, sticky="nsew")
        header_frame.grid_propagate(False)
        doc_header = tk.Label(
            header_frame,
            text="Documento",
            bg=header_bg,
            fg="white",
            padx=8,
            pady=8,
            anchor="w",
            justify="left",
        )
        doc_header.pack(side="left", fill="both", expand=True)
        resize_handle = tk.Frame(header_frame, bg="#16324E", width=8, cursor="sb_h_double_arrow")
        resize_handle.pack(side="right", fill="y")
        resize_handle.bind("<ButtonPress-1>", self._start_document_column_resize)
        resize_handle.bind("<B1-Motion>", self._resize_document_column)
        resize_handle.bind("<ButtonRelease-1>", self._finish_document_column_resize)
        self.document_header_frame = header_frame
        self.document_name_labels.append(doc_header)

        for column_index, periodo in enumerate(periodos, start=1):
            header = tk.Label(
                self.scrollable.inner,
                text=f'{periodo["mes"]:02d}/{periodo["ano"]}\n{MONTH_NAMES[periodo["mes"]]}',
                bg=header_bg,
                fg="white",
                relief="solid",
                bd=1,
                padx=8,
                pady=8,
                justify="center",
            )
            header.grid(row=0, column=column_index, sticky="nsew", padx=1, pady=1)

        row_index = 1
        for group in groups:
            tipo_nome = group["tipo_nome"]
            is_collapsed = self.collapsed_groups.get(tipo_nome, False)

            header_frame = tk.Frame(self.scrollable.inner, bg="#DCE6F1", bd=1, relief="solid")
            header_frame.grid(row=row_index, column=0, columnspan=len(periodos) + 1, sticky="ew", pady=(6, 0))
            toggle = ttk.Button(
                header_frame,
                text="+" if is_collapsed else "-",
                width=3,
                command=lambda name=tipo_nome: self.toggle_group(name),
            )
            toggle.pack(side="left", padx=6, pady=6)
            tk.Label(
                header_frame,
                text=tipo_nome,
                bg="#DCE6F1",
                font=("TkDefaultFont", 10, "bold"),
            ).pack(side="left", padx=(0, 10))
            if group.get("tipo_ocorrencia") not in (None, "mensal"):
                tk.Label(
                    header_frame,
                    text=group["tipo_ocorrencia_label"],
                    bg="#EAF1D0",
                    fg="#355E1D",
                    relief="solid",
                    bd=1,
                    padx=8,
                    pady=2,
                ).pack(side="left", padx=(0, 10))
            tk.Label(
                header_frame,
                text=f'{len(group["documentos"])} documento(s)',
                bg="#DCE6F1",
                fg="#404040",
            ).pack(side="left")
            self.group_widgets[tipo_nome] = {
                "toggle": toggle,
                "document_ids": [],
            }
            row_index += 1

            for document in group["documentos"]:
                self._create_document_row(
                    document,
                    row_index,
                    periodos,
                    tipo_nome,
                    visible=not is_collapsed,
                )
                row_index += 1

        self._apply_document_column_width()
        for column_index in range(len(periodos) + 1):
            if column_index == 0:
                self.scrollable.inner.grid_columnconfigure(column_index, weight=0, minsize=self.document_column_width)
                continue
            self.scrollable.inner.grid_columnconfigure(column_index, weight=1)

        self._restore_scroll_position(scroll_position)

    def _create_document_row(
        self,
        document: dict,
        row_index: int,
        periodos: list[dict],
        group_name: str,
        *,
        visible: bool,
    ) -> None:
        row_widgets: list[tk.Widget] = []
        variables: list[tk.StringVar] = []

        name_widget, name_label, selection_control = self._create_document_name_cell(document, row_index)
        self.document_name_labels.append(name_label)
        row_widgets.append(name_widget)

        for column_index, cell in enumerate(document["cells"], start=1):
            period_label = f'{periodos[column_index - 1]["mes"]:02d}/{periodos[column_index - 1]["ano"]}'
            if cell["available"]:
                cell_widget, variable = self._create_status_cell(
                    row_index,
                    column_index,
                    document["id"],
                    cell["periodo_id"],
                    document["nome_documento"],
                    period_label,
                    cell["status"],
                    cell.get("updated_by_username"),
                    cell.get("updated_at"),
                )
                variables.append(variable)
            else:
                cell_widget = self._create_read_only_cell(
                    row_index,
                    column_index,
                    document["nome_documento"],
                    period_label,
                    cell.get("status") or "",
                    cell.get("read_only_hint"),
                    cell.get("updated_by_username"),
                    cell.get("updated_at"),
                )
            row_widgets.append(cell_widget)

        self.document_rows[document["id"]] = {
            "group_name": group_name,
            "row_index": row_index,
            "row_widgets": row_widgets,
            "name_container": name_widget,
            "name_label": name_label,
            "selection_control": selection_control,
            "variables": variables,
            "document": document,
        }
        self._apply_bulk_document_selection_style(document["id"])

        document_ids = self.group_widgets[group_name]["document_ids"]
        if document["id"] not in document_ids:
            document_ids.append(document["id"])

        if not visible:
            self._set_document_row_visible(document["id"], visible=False)

    def _create_document_name_cell(self, document: dict, row_index: int) -> tuple[tk.Widget, tk.Label, tk.Checkbutton | None]:
        background = self._bulk_document_background(document["id"])
        if not self.bulk_mode_enabled:
            name_label = tk.Label(
                self.scrollable.inner,
                text=document["nome_documento"],
                anchor="w",
                justify="left",
                relief="solid",
                bd=1,
                bg=background,
                padx=8,
                pady=6,
            )
            name_label.grid(row=row_index, column=0, sticky="nsew", padx=1, pady=1)
            return name_label, name_label, None

        selection_var = self.bulk_selection_vars.get(document["id"])
        name_frame = tk.Frame(
            self.scrollable.inner,
            relief="solid",
            bd=1,
            bg=background,
        )
        name_frame.grid(row=row_index, column=0, sticky="nsew", padx=1, pady=1)
        name_frame.grid_columnconfigure(1, weight=1)

        checkbox = tk.Checkbutton(
            name_frame,
            variable=selection_var,
            bg=background,
            activebackground=background,
            selectcolor=background,
            highlightthickness=0,
            bd=0,
            relief="flat",
        )
        checkbox.grid(row=0, column=0, sticky="w", padx=(6, 4), pady=6)

        name_label = tk.Label(
            name_frame,
            text=document["nome_documento"],
            anchor="w",
            justify="left",
            bg=background,
            padx=4,
            pady=6,
        )
        name_label.grid(row=0, column=1, sticky="nsew", padx=(0, 8))

        for widget in (name_frame, name_label):
            widget.bind(
                "<Button-1>",
                lambda _event, doc_id=document["id"]: self._toggle_bulk_document_selection(doc_id),
            )

        return name_frame, name_label, checkbox

    def _sync_bulk_selection_with_view(self, view: dict) -> None:
        valid_document_ids = [
            document["id"]
            for group in view.get("groups", [])
            for document in group.get("documentos", [])
        ]
        valid_document_id_set = set(valid_document_ids)

        for document_id in list(self.bulk_selection_vars):
            if document_id not in valid_document_id_set:
                self.bulk_selection_vars.pop(document_id)

        for document_id in valid_document_ids:
            if document_id in self.bulk_selection_vars:
                continue
            variable = tk.BooleanVar(value=False)
            variable.trace_add(
                "write",
                lambda *_args, current_id=document_id: self._on_bulk_selection_changed(current_id),
            )
            self.bulk_selection_vars[document_id] = variable

        self._update_bulk_selection_summary()

    def _refresh_bulk_period_options(self, view: dict) -> None:
        labels = []
        self.bulk_period_options = {}
        for periodo in view.get("periodos", []):
            label = f'{periodo["mes"]:02d}/{periodo["ano"]} - {MONTH_NAMES[periodo["mes"]]}'
            labels.append(label)
            self.bulk_period_options[label] = periodo["id"]
        self.bulk_period_combo.configure(values=labels)
        if self.bulk_period_var.get() not in labels:
            self.bulk_period_var.set(labels[0] if labels else "")

    def _bulk_document_background(self, document_id: int) -> str:
        selection_var = self.bulk_selection_vars.get(document_id)
        if selection_var and selection_var.get():
            return "#EAF3FF"
        return "#FFFFFF"

    def _toggle_bulk_document_selection(self, document_id: int) -> None:
        if not self.bulk_mode_enabled:
            return
        selection_var = self.bulk_selection_vars.get(document_id)
        if selection_var is None:
            return
        selection_var.set(not selection_var.get())

    def _on_bulk_selection_changed(self, document_id: int) -> None:
        if self._bulk_selection_updates_suspended:
            return
        self._apply_bulk_document_selection_style(document_id)
        self._update_bulk_selection_summary()

    def _apply_bulk_document_selection_style(self, document_id: int) -> None:
        row_info = self.document_rows.get(document_id)
        if not row_info:
            return

        background = self._bulk_document_background(document_id)
        name_container = row_info.get("name_container")
        name_label = row_info.get("name_label")
        selection_control = row_info.get("selection_control")

        if name_container and name_container.winfo_exists():
            name_container.configure(bg=background)
        if name_label and name_label.winfo_exists():
            name_label.configure(bg=background)
        if selection_control and selection_control.winfo_exists():
            selection_control.configure(
                bg=background,
                activebackground=background,
                selectcolor=background,
            )

    def _selected_bulk_document_ids(self) -> list[int]:
        return [
            document_id
            for document_id, variable in self.bulk_selection_vars.items()
            if variable.get()
        ]

    def _update_bulk_selection_summary(self) -> None:
        selected_count = len(self._selected_bulk_document_ids())
        if selected_count == 0:
            self.bulk_selection_summary_var.set("Nenhum documento selecionado.")
        elif selected_count == 1:
            self.bulk_selection_summary_var.set("1 documento selecionado.")
        else:
            self.bulk_selection_summary_var.set(f"{selected_count} documentos selecionados.")
        self._update_bulk_controls_state()

    def _set_bulk_selection_state(self, document_ids: list[int], selected: bool) -> None:
        self._bulk_selection_updates_suspended = True
        for document_id in document_ids:
            variable = self.bulk_selection_vars.get(document_id)
            if variable is not None:
                variable.set(selected)
        self._bulk_selection_updates_suspended = False

        for document_id in document_ids:
            self._apply_bulk_document_selection_style(document_id)
        self._update_bulk_selection_summary()

    def _update_bulk_controls_state(self) -> None:
        has_documents = bool(self.bulk_selection_vars)
        selected_count = len(self._selected_bulk_document_ids())
        active_state = "normal" if self.bulk_mode_enabled and has_documents else "disabled"

        self.bulk_select_all_button.configure(state=active_state)
        self.bulk_clear_button.configure(state="normal" if self.bulk_mode_enabled and selected_count else "disabled")
        self.bulk_period_combo.configure(
            state="readonly" if self.bulk_mode_enabled and self.bulk_period_options else "disabled"
        )
        self.bulk_status_combo.configure(state="readonly" if self.bulk_mode_enabled and has_documents else "disabled")
        self.bulk_apply_button.configure(state="normal" if self.bulk_mode_enabled and selected_count else "disabled")

    def toggle_bulk_selection_mode(self) -> None:
        if not self.current_view or not self.current_view.get("groups"):
            return

        scroll_position = self._get_scroll_position()
        self.bulk_mode_enabled = not self.bulk_mode_enabled
        if self.bulk_mode_enabled:
            self._show_bulk_panel()
        else:
            self._set_bulk_selection_state(list(self.bulk_selection_vars), False)
            self._hide_bulk_panel()

        self.bulk_mode_button.configure(text="Fechar lote" if self.bulk_mode_enabled else "Selecao em lote")
        self._update_bulk_controls_state()
        self.render_result(self.current_view, scroll_position=scroll_position)

    def select_all_documents_in_bulk(self) -> None:
        self._set_bulk_selection_state(list(self.bulk_selection_vars), True)

    def clear_bulk_selection(self) -> None:
        self._set_bulk_selection_state(list(self.bulk_selection_vars), False)

    def apply_bulk_status(self) -> None:
        selected_document_ids = self._selected_bulk_document_ids()
        if not selected_document_ids:
            messagebox.showwarning("Controle", "Selecione pelo menos um documento para alterar em lote.", parent=self)
            return

        period_label = self.bulk_period_var.get().strip()
        period_id = self.bulk_period_options.get(period_label)
        if not period_id:
            messagebox.showwarning("Controle", "Escolha um periodo da grade para aplicar o lote.", parent=self)
            return

        status_label = self.bulk_status_var.get().strip()
        if status_label not in self.bulk_status_options:
            messagebox.showwarning("Controle", "Escolha o status que sera aplicado aos documentos selecionados.", parent=self)
            return

        status_value = self.bulk_status_options[status_label]
        period_short_label = period_label.split(" - ", 1)[0]
        action_label = (
            "limpar o status"
            if status_label == "Limpar status"
            else f'aplicar o status "{status_label}"'
        )
        confirmed = messagebox.askyesno(
            "Controle",
            (
                f'Deseja {action_label} em {len(selected_document_ids)} documento(s) '
                f'para o periodo {period_short_label}?'
            ),
            parent=self,
        )
        if not confirmed:
            return

        scroll_position = self._get_scroll_position()
        try:
            result = self.services.status_service.update_status_batch(selected_document_ids, period_id, status_value)
        except ValidationError as exc:
            messagebox.showerror("Controle", str(exc), parent=self)
            return

        self.clear_bulk_selection()
        self._reload_current_view(scroll_position=scroll_position)

        if status_label == "Limpar status":
            status_message = "status limpo"
        else:
            status_message = f'status "{status_label}"'
        self._set_default_message(
            (
                f'Alteracao em lote concluida: {result["updated"]} de {result["selected"]} documento(s) '
                f'atualizado(s) em {period_short_label} com {status_message}.'
            )
        )

    def _create_status_cell(
        self,
        row_index: int,
        column_index: int,
        document_id: int,
        period_id: int,
        document_name: str,
        period_label: str,
        current_status: str,
        updated_by_username: str | None,
        updated_at: str | None,
    ) -> tuple[tk.Frame, tk.StringVar]:
        color = STATUS_COLORS.get(current_status, STATUS_COLORS[""])
        cell_frame = tk.Frame(self.scrollable.inner, bg=color, relief="solid", bd=1)
        cell_frame.grid(row=row_index, column=column_index, sticky="nsew", padx=1, pady=1)

        variable = tk.StringVar(value=current_status)
        option = tk.OptionMenu(
            cell_frame,
            variable,
            *STATUS_OPTIONS,
            command=lambda value, doc_id=document_id, per_id=period_id: self.update_status(doc_id, per_id, value),
        )
        option.configure(
            width=11,
            bg=color,
            highlightthickness=0,
            relief="flat",
            activebackground=color,
        )
        option["menu"].configure(tearoff=0)
        option.pack(fill="both", expand=True)

        self._bind_status_metadata(
            (cell_frame, option),
            document_name,
            period_label,
            current_status,
            updated_by_username,
            updated_at,
        )
        return cell_frame, variable

    def _create_read_only_cell(
        self,
        row_index: int,
        column_index: int,
        document_name: str,
        period_label: str,
        display_status: str,
        read_only_hint: str | None,
        updated_by_username: str | None,
        updated_at: str | None,
    ) -> tk.Label:
        color = STATUS_COLORS.get(display_status, "#F3F3F3")
        inactive = tk.Label(
            self.scrollable.inner,
            text=display_status,
            relief="solid",
            bd=1,
            bg=color,
            padx=8,
            pady=10,
        )
        inactive.grid(row=row_index, column=column_index, sticky="nsew", padx=1, pady=1)
        if read_only_hint:
            inactive.bind(
                "<Enter>",
                lambda _event, message=read_only_hint: self.message_var.set(message),
            )
            inactive.bind("<Leave>", self._restore_default_message)
        else:
            self._bind_status_metadata(
                (inactive,),
                document_name,
                period_label,
                display_status,
                updated_by_username,
                updated_at,
            )
        return inactive

    def _bind_status_metadata(
        self,
        widgets: tuple[tk.Widget, ...],
        document_name: str,
        period_label: str,
        current_status: str,
        updated_by_username: str | None,
        updated_at: str | None,
    ) -> None:
        for widget in widgets:
            widget.bind(
                "<Enter>",
                lambda _event, doc_name=document_name, per_label=period_label, cell_status=current_status,
                actor=updated_by_username, timestamp=updated_at: self._show_status_metadata(
                    doc_name,
                    per_label,
                    cell_status,
                    actor,
                    timestamp,
                ),
            )
            widget.bind("<Leave>", self._restore_default_message)

    def update_status(self, document_id: int, period_id: int, status: str) -> None:
        cached_document = self._get_cached_document(document_id)
        try:
            self.services.status_service.update_status(document_id, period_id, status)
        except ValidationError as exc:
            if cached_document is not None:
                self._replace_document_row(cached_document)
            messagebox.showerror("Controle", str(exc), parent=self)
            return
        self._refresh_document_row_from_service(document_id)

    def toggle_group(self, group_name: str) -> None:
        scroll_position = self._get_scroll_position()
        self.collapsed_groups[group_name] = not self.collapsed_groups.get(group_name, False)
        self._apply_group_visibility(group_name)
        self._restore_scroll_position(scroll_position)

    def _clear_result_area(self) -> None:
        self.group_widgets = {}
        self.document_rows = {}
        self.document_name_labels = []
        self.document_header_frame = None
        for child in self.scrollable.inner.winfo_children():
            child.destroy()

    def _get_cached_document(self, document_id: int) -> dict | None:
        if not self.current_view:
            return None

        for group in self.current_view.get("groups", []):
            for document in group.get("documentos", []):
                if document["id"] == document_id:
                    return document
        return None

    def _update_cached_document(self, document: dict) -> None:
        if not self.current_view:
            return

        for group in self.current_view.get("groups", []):
            for index, current_document in enumerate(group.get("documentos", [])):
                if current_document["id"] == document["id"]:
                    group["documentos"][index] = document
                    return

    def _refresh_document_row_from_service(self, document_id: int) -> None:
        if not self.current_filters or not self.current_view:
            return

        updated_document = self.services.status_service.build_control_document_view(
            document_id,
            self.current_filters["start_period_id"],
            self.current_filters["end_period_id"],
        )
        if updated_document is None:
            return

        scroll_position = self._get_scroll_position()
        self._update_cached_document(updated_document)
        self._replace_document_row(updated_document)
        self._restore_scroll_position(scroll_position)

    def _replace_document_row(self, document: dict) -> None:
        row_info = self.document_rows.get(document["id"])
        if not row_info or not self.current_view:
            return

        name_label = row_info.get("name_label")
        if name_label in self.document_name_labels:
            self.document_name_labels.remove(name_label)

        for widget in row_info["row_widgets"]:
            if widget.winfo_exists():
                widget.destroy()

        self._create_document_row(
            document,
            row_info["row_index"],
            self.current_view["periodos"],
            row_info["group_name"],
            visible=not self.collapsed_groups.get(row_info["group_name"], False),
        )
        self._apply_document_column_width()

    def _apply_group_visibility(self, group_name: str) -> None:
        group_info = self.group_widgets.get(group_name)
        if not group_info:
            return

        collapsed = self.collapsed_groups.get(group_name, False)
        toggle = group_info.get("toggle")
        if toggle and toggle.winfo_exists():
            toggle.configure(text="+" if collapsed else "-")

        for document_id in group_info["document_ids"]:
            self._set_document_row_visible(document_id, visible=not collapsed)

    def _set_document_row_visible(self, document_id: int, *, visible: bool) -> None:
        row_info = self.document_rows.get(document_id)
        if not row_info:
            return

        for widget in row_info["row_widgets"]:
            if not widget.winfo_exists():
                continue
            if visible:
                widget.grid()
            else:
                widget.grid_remove()

    def _get_scroll_position(self) -> float:
        yview = self.scrollable.canvas.yview()
        if not yview:
            return 0.0
        return yview[0]

    def _restore_scroll_position(self, scroll_position: float | None) -> None:
        if scroll_position is None:
            return

        clamped_position = min(max(scroll_position, 0.0), 1.0)

        def _apply() -> None:
            if self.winfo_exists():
                self.scrollable.canvas.yview_moveto(clamped_position)

        self.after_idle(_apply)

    def _show_status_metadata(
        self,
        document_name: str,
        period_label: str,
        status: str,
        updated_by_username: str | None,
        updated_at: str | None,
    ) -> None:
        if updated_at:
            actor = updated_by_username or "Sistema"
            self.message_var.set(
                (
                    f'Documento "{document_name}" em {period_label}: '
                    f'status "{status or "vazio"}", alterado por {actor} em {self._format_timestamp(updated_at)}.'
                )
            )
            return
        self.message_var.set(
            f'Documento "{document_name}" em {period_label}: nenhuma alteracao registrada ainda.'
        )

    def _restore_default_message(self, _event=None) -> None:
        self.message_var.set(self.default_message_text)

    def _set_default_message(self, text: str) -> None:
        self.default_message_text = text
        self.message_var.set(text)

    def _apply_document_column_width(self) -> None:
        if not self.scrollable.winfo_exists():
            return

        self.document_column_width = max(self.document_column_width, 180)
        self.scrollable.inner.grid_columnconfigure(0, weight=0, minsize=self.document_column_width)

        if self.document_header_frame and self.document_header_frame.winfo_exists():
            self.document_header_frame.configure(width=self.document_column_width)

        reserved_space = 72 if self.bulk_mode_enabled else 24
        wraplength = max(self.document_column_width - reserved_space, 120)
        for label in self.document_name_labels:
            if label.winfo_exists():
                label.configure(wraplength=wraplength)

    def _start_document_column_resize(self, event) -> None:
        self._resize_start_x = event.x_root
        self._resize_start_width = self.document_column_width

    def _resize_document_column(self, event) -> None:
        if self._resize_start_x is None or self._resize_start_width is None:
            return

        self.document_column_width = self._resize_start_width + (event.x_root - self._resize_start_x)
        self._apply_document_column_width()

    def _finish_document_column_resize(self, _event=None) -> None:
        self._resize_start_x = None
        self._resize_start_width = None

    def _format_timestamp(self, raw_value: str) -> str:
        try:
            return datetime.strptime(raw_value, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
        except ValueError:
            return raw_value
