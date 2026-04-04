from __future__ import annotations

from documentos_empresa_app.database.repositories import (
    DocumentoRepository,
    EmpresaRepository,
    PeriodoRepository,
    StatusRepository,
)
from documentos_empresa_app.services.audit_service import AuditService
from documentos_empresa_app.services.session_service import SessionService
from documentos_empresa_app.utils.common import (
    AUTO_STATUS_NAO_COBRAR,
    ValidationError,
    build_chargeable_closure_key_map,
    count_months_between,
    get_type_occurrence_label,
    is_chargeable_period,
    month_key,
    normalize_type_occurrence_rule,
)


class StatusService:
    def __init__(
        self,
        empresa_repository: EmpresaRepository,
        documento_repository: DocumentoRepository,
        periodo_repository: PeriodoRepository,
        status_repository: StatusRepository,
        audit_service: AuditService | None = None,
        session_service: SessionService | None = None,
    ) -> None:
        self.empresa_repository = empresa_repository
        self.documento_repository = documento_repository
        self.periodo_repository = periodo_repository
        self.status_repository = status_repository
        self.audit_service = audit_service
        self.session_service = session_service
        self.valid_statuses = {"Recebido", "Pendente", "Encerrado", "", None}

    def update_status(self, documento_id: int, periodo_id: int, status: str | None) -> None:
        normalized = self._normalize_status(status)
        with self.status_repository.db_manager.connect():
            documento = self.documento_repository.get_by_id(documento_id)
            if not documento:
                raise ValidationError("Documento nao encontrado.")

            periodo = self.periodo_repository.get_by_id(periodo_id)
            if not periodo:
                raise ValidationError("Periodo nao encontrado.")

            existing = self.status_repository.get_by_document_and_period(documento_id, periodo_id)
            previous_status = existing["status"] if existing else None
            if previous_status == normalized:
                return

            occurrence_rule = normalize_type_occurrence_rule(documento.get("regra_ocorrencia"))
            if not is_chargeable_period(occurrence_rule, periodo["mes"]) and normalized not in ("", None):
                raise ValidationError(
                    (
                        f'O tipo "{documento["nome_tipo"]}" esta configurado como '
                        f'{get_type_occurrence_label(occurrence_rule).lower()} e o periodo '
                        f'{periodo["mes"]:02d}/{periodo["ano"]} fica automaticamente como "{AUTO_STATUS_NAO_COBRAR}".'
                    )
                )

            closure_key = self._get_closure_key_map([documento]).get(documento_id)
            target_key = month_key(periodo["ano"], periodo["mes"])
            if closure_key is not None:
                if target_key > closure_key and normalized not in ("", None):
                    raise ValidationError(
                        "Esse documento ja foi encerrado em um mes anterior e nao pode receber status depois disso."
                    )

            future_statuses = []
            if normalized == "Encerrado":
                future_statuses = self.status_repository.list_future_statuses(
                    documento_id,
                    periodo["ano"],
                    periodo["mes"],
                )

            self.status_repository.upsert(
                documento_id,
                periodo_id,
                normalized,
                self.session_service.get_user_id() if self.session_service else None,
            )
            if normalized == "Encerrado":
                self.status_repository.delete_future_statuses(documento_id, periodo["ano"], periodo["mes"])

            empresa = self.empresa_repository.get_by_id(documento["empresa_id"])
            if not empresa:
                return

            self._log_status_change(empresa, documento, periodo, previous_status, normalized)
            for removed_status in future_statuses:
                if removed_status["status"] in ("", None):
                    continue
                self._log_status_change(
                    empresa,
                    documento,
                    {"ano": removed_status["ano"], "mes": removed_status["mes"]},
                    removed_status["status"],
                    None,
                )

    def build_control_view(self, empresa_id: int, start_period_id: int, end_period_id: int) -> dict:
        empresa = self.empresa_repository.get_by_id(empresa_id)
        if not empresa:
            raise ValidationError("Empresa nao encontrada.")

        start_period = self.periodo_repository.get_by_id(start_period_id)
        end_period = self.periodo_repository.get_by_id(end_period_id)
        if not start_period or not end_period:
            raise ValidationError("Selecione um periodo inicial e um periodo final validos.")

        start_key = month_key(start_period["ano"], start_period["mes"])
        end_key = month_key(end_period["ano"], end_period["mes"])
        if start_key > end_key:
            raise ValidationError("O periodo inicial nao pode ser maior que o periodo final.")
        if count_months_between(
            start_period["ano"],
            start_period["mes"],
            end_period["ano"],
            end_period["mes"],
        ) > 12:
            raise ValidationError("A consulta permite no maximo 12 meses por vez.")

        periodos = self.periodo_repository.list_between(
            start_period["ano"], start_period["mes"], end_period["ano"], end_period["mes"]
        )
        if not periodos:
            raise ValidationError("Nao existem periodos gerados para o intervalo informado.")

        documentos = self.documento_repository.list_by_company(empresa_id)
        if not documentos:
            return {"empresa": empresa, "periodos": periodos, "groups": []}

        period_ids = [periodo["id"] for periodo in periodos]
        document_ids = [documento["id"] for documento in documentos]

        status_rows = self.status_repository.list_for_documents_and_periods(document_ids, period_ids)
        statuses = {
            (row["documento_empresa_id"], row["periodo_id"]): row
            for row in status_rows
        }
        closures = self._get_closure_key_map(documentos)

        grouped: dict[int, dict] = {}
        for documento in documentos:
            closure_key = closures.get(documento["id"])
            occurrence_rule = normalize_type_occurrence_rule(documento.get("regra_ocorrencia"))
            cells = []
            appears_in_any_period = False
            for periodo in periodos:
                current_key = month_key(periodo["ano"], periodo["mes"])
                chargeable = is_chargeable_period(occurrence_rule, periodo["mes"])
                available = chargeable and (closure_key is None or current_key <= closure_key)
                status_row = statuses.get((documento["id"], periodo["id"]))
                display_status = (
                    AUTO_STATUS_NAO_COBRAR
                    if not chargeable
                    else (status_row["status"] or "") if available and status_row else ""
                )
                if available or display_status == AUTO_STATUS_NAO_COBRAR:
                    appears_in_any_period = True
                cells.append(
                    {
                        "periodo_id": periodo["id"],
                        "available": available,
                        "status": display_status,
                        "updated_by_username": status_row["updated_by_username"] if available and status_row else "",
                        "updated_at": status_row["updated_at"] if available and status_row else None,
                        "read_only_hint": self._build_read_only_hint(
                            documento,
                            periodo,
                            available,
                            chargeable,
                            closure_key,
                        ),
                    }
                )

            if not appears_in_any_period:
                continue

            group = grouped.setdefault(
                documento["tipo_documento_id"],
                {
                    "tipo_id": documento["tipo_documento_id"],
                    "tipo_nome": documento["nome_tipo"],
                    "tipo_ocorrencia": occurrence_rule,
                    "tipo_ocorrencia_label": get_type_occurrence_label(occurrence_rule),
                    "documentos": [],
                }
            )
            group["documentos"].append(
                {
                    "id": documento["id"],
                    "nome_documento": documento["nome_documento"],
                    "tipo_id": documento["tipo_documento_id"],
                    "tipo_nome": documento["nome_tipo"],
                    "tipo_ocorrencia": occurrence_rule,
                    "cells": cells,
                }
            )

        groups = [
            {
                "tipo_id": group["tipo_id"],
                "tipo_nome": tipo_nome,
                "tipo_ocorrencia": group["tipo_ocorrencia"],
                "tipo_ocorrencia_label": group["tipo_ocorrencia_label"],
                "documentos": sorted(group["documentos"], key=lambda item: item["nome_documento"].lower()),
            }
            for _tipo_id, group in sorted(grouped.items(), key=lambda item: item[1]["tipo_nome"].lower())
            for tipo_nome in [group["tipo_nome"]]
        ]

        return {"empresa": empresa, "periodos": periodos, "groups": groups}

    def _normalize_status(self, status: str | None) -> str | None:
        normalized = None if status is None else str(status).strip()
        if normalized == "":
            normalized = None
        if normalized not in self.valid_statuses:
            raise ValidationError("Status invalido informado.")
        return normalized

    def _get_closure_key_map(self, documentos: list[dict]) -> dict[int, int]:
        document_ids = [documento["id"] for documento in documentos]
        occurrence_by_document = {
            documento["id"]: normalize_type_occurrence_rule(documento.get("regra_ocorrencia"))
            for documento in documentos
        }
        closure_rows = self.status_repository.list_closures_for_documents(document_ids)
        return build_chargeable_closure_key_map(closure_rows, occurrence_by_document)

    def _build_read_only_hint(
        self,
        documento: dict,
        periodo: dict,
        available: bool,
        chargeable: bool,
        closure_key: int | None,
    ) -> str:
        if not chargeable:
            return (
                f'O tipo "{documento["nome_tipo"]}" usa ocorrencia '
                f'{get_type_occurrence_label(documento.get("regra_ocorrencia")).lower()}. '
                f'Por isso {periodo["mes"]:02d}/{periodo["ano"]} fica como "{AUTO_STATUS_NAO_COBRAR}".'
            )
        if not available and closure_key is not None:
            closure_year = closure_key // 100
            closure_month = closure_key % 100
            return (
                f'O documento foi encerrado em {closure_month:02d}/{closure_year} '
                "e nao pode receber status depois disso."
            )
        return ""

    def _log_status_change(
        self,
        empresa: dict,
        documento: dict,
        periodo: dict,
        previous_status: str | None,
        new_status: str | None,
    ) -> None:
        if not self.audit_service:
            return
        previous_label = previous_status or "vazio"
        new_label = new_status or "vazio"
        self.audit_service.log(
            "ALTERACAO_STATUS",
            "documento_status",
            documento["id"],
            (
                f'Usuario {self._actor_name()} alterou o status do documento "{documento["nome_documento"]}" '
                f'da empresa "{empresa["nome_empresa"]}", periodo {periodo["mes"]:02d}/{periodo["ano"]}, '
                f'de "{previous_label}" para "{new_label}".'
            ),
            empresa_id=empresa["id"],
            empresa_nome=empresa["nome_empresa"],
            periodo_ano=periodo["ano"],
            periodo_mes=periodo["mes"],
        )

    def _actor_name(self) -> str:
        if not self.session_service:
            return "Sistema"
        return self.session_service.get_username()
