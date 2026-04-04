from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from documentos_empresa_app.utils.common import DOCUMENT_DELIVERY_OPTIONS, ValidationError, parse_delivery_methods


class DeliveryMethodsManagerDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, delivery_method_service, dialog_title: str) -> None:
        super().__init__(parent.winfo_toplevel())
        self.parent = parent
        self.delivery_method_service = delivery_method_service
        self.dialog_title = dialog_title
        self.selected_method_id: int | None = None
        self.nome_var = tk.StringVar()

        self.title(f"{dialog_title} - Meios do sistema")
        self.transient(parent.winfo_toplevel())
        self.resizable(True, True)
        self.minsize(420, 320)

        self._build_layout()
        self.refresh_methods()
        self.grab_set()
        self.after(10, self._center_on_parent)

    def _build_layout(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        ttk.Label(
            self,
            text=(
                "Gerencie os meios disponiveis no sistema. Renomear atualiza tambem os documentos que usam o meio. "
                "Excluir remove apenas da lista do sistema."
            ),
            justify="left",
            wraplength=440,
        ).grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 8))

        list_frame = ttk.LabelFrame(self, text="Meios cadastrados", padding=10)
        list_frame.grid(row=1, column=0, sticky="nsew", padx=12)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(list_frame, columns=("nome",), show="headings", selectmode="browse", height=10)
        self.tree.heading("nome", text="Nome")
        self.tree.column("nome", width=260)
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self.load_selected_method)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        editor = ttk.LabelFrame(self, text="Editar lista", padding=10)
        editor.grid(row=2, column=0, sticky="ew", padx=12, pady=(12, 12))
        editor.columnconfigure(0, weight=1)
        editor.columnconfigure(1, weight=1)

        ttk.Label(editor, text="Nome do meio").grid(row=0, column=0, columnspan=2, sticky="w")
        entry = ttk.Entry(editor, textvariable=self.nome_var)
        entry.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        entry.bind("<Return>", self.save_method)

        self.save_button = ttk.Button(editor, text="Adicionar", command=self.save_method)
        self.save_button.grid(row=2, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(editor, text="Limpar", command=self.clear_selection).grid(row=2, column=1, sticky="ew")
        ttk.Button(editor, text="Excluir do sistema", command=self.delete_selected_method).grid(
            row=3, column=0, columnspan=2, sticky="ew", pady=(8, 0)
        )

    def _center_on_parent(self) -> None:
        self.update_idletasks()
        parent = self.parent.winfo_toplevel()
        x = parent.winfo_rootx() + max((parent.winfo_width() - self.winfo_width()) // 2, 0)
        y = parent.winfo_rooty() + max((parent.winfo_height() - self.winfo_height()) // 2, 0)
        self.geometry(f"+{x}+{y}")

    def refresh_methods(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for method in self.delivery_method_service.list_methods():
            self.tree.insert("", "end", iid=str(method["id"]), values=(method["nome_meio"],))

        if self.selected_method_id and self.tree.exists(str(self.selected_method_id)):
            self.tree.selection_set(str(self.selected_method_id))
            self.tree.focus(str(self.selected_method_id))
            self.tree.see(str(self.selected_method_id))
            return

        self.clear_selection()

    def load_selected_method(self, _event=None) -> None:
        selection = self.tree.selection()
        if not selection:
            return

        method = self.delivery_method_service.get_method(int(selection[0]))
        self.selected_method_id = method["id"]
        self.nome_var.set(method["nome_meio"])
        self.save_button.configure(text="Renomear")

    def clear_selection(self) -> None:
        self.selected_method_id = None
        self.nome_var.set("")
        self.save_button.configure(text="Adicionar")
        selection = self.tree.selection()
        if selection:
            self.tree.selection_remove(*selection)

    def save_method(self, _event=None) -> None:
        try:
            if self.selected_method_id:
                affected_documents = self.delivery_method_service.update_method(self.selected_method_id, self.nome_var.get())
                message = "Meio atualizado com sucesso."
                if affected_documents:
                    message += f" Documentos ajustados: {affected_documents}."
                messagebox.showinfo(self.dialog_title, message, parent=self)
            else:
                self.delivery_method_service.create_method(self.nome_var.get())
                messagebox.showinfo(self.dialog_title, "Meio cadastrado com sucesso.", parent=self)
        except ValidationError as exc:
            messagebox.showerror(self.dialog_title, str(exc), parent=self)
            return

        self.refresh_methods()

    def delete_selected_method(self) -> None:
        if not self.selected_method_id:
            messagebox.showwarning(self.dialog_title, "Selecione um meio na lista.", parent=self)
            return

        method = self.delivery_method_service.get_method(self.selected_method_id)
        affected_documents = self.delivery_method_service.count_documents_using(method["nome_meio"])
        prompt = f'Deseja excluir "{method["nome_meio"]}" da lista do sistema?'
        if affected_documents:
            prompt += (
                f"\n\nEsse meio ainda aparece em {affected_documents} documento(s). "
                "A exclusao remove apenas da lista do sistema."
            )

        if not messagebox.askyesno(self.dialog_title, prompt, parent=self):
            return

        self.delivery_method_service.delete_method(self.selected_method_id)
        self.refresh_methods()
        messagebox.showinfo(self.dialog_title, "Meio removido da lista do sistema.", parent=self)


class DeliveryMethodsField(ttk.LabelFrame):
    def __init__(
        self,
        master,
        title: str = "Meios de recebimento",
        dialog_title: str = "Empresas",
        delivery_method_service=None,
    ) -> None:
        super().__init__(master, text=title, padding=8)
        self.dialog_title = dialog_title
        self.delivery_method_service = delivery_method_service
        self.option_var = tk.StringVar()
        self.selected_values: list[str] = []
        self.available_values: list[str] = list(DOCUMENT_DELIVERY_OPTIONS)
        self.editable = True

        self.combo = ttk.Combobox(
            self,
            textvariable=self.option_var,
            values=self.available_values,
            state="normal",
            width=18,
        )
        self.combo.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.combo.bind("<<ComboboxSelected>>", self.toggle_selected)
        self.combo.bind("<Return>", self.toggle_selected)
        self.manage_button = ttk.Button(self, text="...", width=3, command=self.open_manager_dialog)
        self.manage_button.grid(row=0, column=1, sticky="ew")

        list_frame = ttk.Frame(self)
        list_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        list_frame.columnconfigure(0, weight=1)

        self.selected_listbox = tk.Listbox(
            list_frame,
            height=2,
            exportselection=False,
            activestyle="dotbox",
        )
        self.selected_listbox.grid(row=0, column=0, sticky="ew")
        self.selected_listbox.bind("<<ListboxSelect>>", self._on_list_selection_changed)
        self.selected_listbox.bind("<Double-1>", self.remove_selected_item)
        self.selected_listbox.bind("<Delete>", self.remove_selected_item)

        self.remove_button = ttk.Button(list_frame, text="Remover", command=self.remove_selected_item)
        self.remove_button.grid(row=0, column=1, sticky="ns", padx=(6, 0))

        self.columnconfigure(0, weight=1)
        self.refresh_available_values()
        self._sync_selected_listbox()
        self.set_editable(True)

    def get_values(self) -> list[str]:
        self._commit_pending_selection()
        return list(self.selected_values)

    def set_values(self, raw_value: str | list[str] | tuple[str, ...] | None) -> None:
        self.option_var.set("")
        self.selected_values = parse_delivery_methods(raw_value, known_options=self.available_values)
        self._update_combo_values()
        self._sync_selected_listbox()

    def clear(self) -> None:
        self.set_values(None)

    def refresh_available_values(self) -> None:
        if self.delivery_method_service:
            self.available_values = [item["nome_meio"] for item in self.delivery_method_service.list_methods()]
        self._update_combo_values()
        self._sync_selected_listbox()

    def toggle_selected(self, _event=None) -> None:
        if not self.editable:
            return

        selected = self._normalize_single_value(self.option_var.get())
        if not selected:
            return

        existing_index = next(
            (index for index, item in enumerate(self.selected_values) if item.casefold() == selected.casefold()),
            None,
        )
        if existing_index is None:
            self.selected_values.append(selected)
        else:
            self.selected_values.pop(existing_index)

        self.option_var.set("")
        self._update_combo_values()
        self._sync_selected_listbox()

    def open_manager_dialog(self) -> None:
        if not self.editable:
            return
        if not self.delivery_method_service:
            messagebox.showwarning(
                self.dialog_title,
                "O gerenciamento global de meios nao esta disponivel nesta tela.",
                parent=self,
            )
            return

        dialog = DeliveryMethodsManagerDialog(self, self.delivery_method_service, self.dialog_title)
        self.wait_window(dialog)
        self.refresh_available_values()

    def _normalize_single_value(self, raw_value: str | None) -> str:
        values = parse_delivery_methods([raw_value or ""], known_options=self.available_values)
        return values[0] if values else ""

    def _commit_pending_selection(self) -> None:
        if not self.editable:
            return
        selected = self._normalize_single_value(self.option_var.get())
        if not selected:
            return
        if any(item.casefold() == selected.casefold() for item in self.selected_values):
            self.option_var.set("")
            return
        self.selected_values.append(selected)
        self.option_var.set("")
        self._sync_selected_listbox()

    def _update_combo_values(self) -> None:
        self.combo["values"] = sorted(self.available_values, key=str.casefold)

    def remove_selected_item(self, _event=None) -> str | None:
        if not self.editable:
            return "break"

        selection = self.selected_listbox.curselection()
        if not selection:
            return "break"

        index = selection[0]
        if 0 <= index < len(self.selected_values):
            self.selected_values.pop(index)
            self._sync_selected_listbox()
        return "break"

    def set_editable(self, enabled: bool) -> None:
        self.editable = enabled
        self.combo.configure(state="normal" if enabled else "disabled")
        self.manage_button.configure(state="normal" if enabled else "disabled")
        self.selected_listbox.configure(state="normal" if enabled else "disabled")
        self._set_remove_button_state()

    def _sync_selected_listbox(self) -> None:
        list_state = str(self.selected_listbox.cget("state"))
        if list_state == "disabled":
            self.selected_listbox.configure(state="normal")

        self.selected_listbox.delete(0, "end")
        for value in self.selected_values:
            self.selected_listbox.insert("end", value)

        list_height = min(max(len(self.selected_values), 2), 4)
        self.selected_listbox.configure(height=list_height)
        self._set_remove_button_state()

        if list_state == "disabled":
            self.selected_listbox.configure(state="disabled")

    def _set_remove_button_state(self) -> None:
        has_selection = bool(self.selected_listbox.curselection())
        self.remove_button.configure(state="normal" if self.editable and has_selection else "disabled")

    def _on_list_selection_changed(self, _event=None) -> None:
        self._set_remove_button_state()
