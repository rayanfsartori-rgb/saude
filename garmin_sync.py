#!/usr/bin/env python3
"""
RFS — Garmin Sync
Puxa sono e calorias do Garmin Connect e atualiza registro.csv.
Roda automaticamente via GitHub Actions todo dia às 23:30 (horário de Brasília).
"""

import os
import csv
from datetime import date
from pathlib import Path

from garminconnect import Garmin


# ── Config ────────────────────────────────────────────────────────────────────

GARMIN_EMAIL    = os.environ["GARMIN_EMAIL"]
GARMIN_PASSWORD = os.environ["GARMIN_PASSWORD"]

REGISTRO = Path("registro.csv")
CAMPOS   = ["data", "proteina", "carbo", "gordura", "kcal_ing",
            "kcal_gasto", "sono", "atividade1", "atividade2", "obs"]


# ── Garmin ────────────────────────────────────────────────────────────────────

def buscar_garmin(data_iso: str) -> dict:
    print("🔌 Conectando ao Garmin Connect...")
    garmin = Garmin(GARMIN_EMAIL, GARMIN_PASSWORD)
    garmin.login()
    print("✅ Login OK")

    # Calorias totais (BMR + ativas)
    stats      = garmin.get_stats(data_iso)
    kcal_total = int(stats.get("totalKilocalories", 0) or 0)
    print(f"🔥 Calorias: {kcal_total} kcal")

    # Sono (noite anterior — convenção RFS)
    sono_horas = 0.0
    try:
        sleep_data = garmin.get_sleep_data(data_iso)
        dto        = sleep_data.get("dailySleepDTO") or sleep_data
        sono_seg   = dto.get("sleepTimeSeconds", 0) or 0
        sono_horas = round(sono_seg / 3600, 2)
    except Exception as e:
        print(f"⚠️  Sono não disponível: {e}")

    print(f"😴 Sono: {sono_horas}h")
    return {"kcal_gasto": kcal_total, "sono": sono_horas}


# ── CSV ───────────────────────────────────────────────────────────────────────

def ler_csv() -> list[dict]:
    if not REGISTRO.exists():
        return []
    with open(REGISTRO, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def salvar_csv(rows: list[dict]):
    with open(REGISTRO, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CAMPOS)
        writer.writeheader()
        writer.writerows(rows)


def ordenar(rows: list[dict]) -> list[dict]:
    def key(r):
        try:
            d, m, y = r["data"].split("/")
            return (int(y), int(m), int(d))
        except Exception:
            return (0, 0, 0)
    return sorted(rows, key=key)


def atualizar_csv(dados_garmin: dict, data_br: str):
    rows = ler_csv()

    row = next((r for r in rows if r.get("data", "").strip() == data_br), None)

    if row is None:
        row = {c: "" for c in CAMPOS}
        row["data"] = data_br
        rows.append(row)
        print(f"➕ Nova linha: {data_br}")
    else:
        print(f"✏️  Atualizando linha: {data_br}")

    row["kcal_gasto"] = dados_garmin["kcal_gasto"]
    row["sono"]       = dados_garmin["sono"]

    salvar_csv(ordenar(rows))
    print(f"✅ {data_br} | Gasto: {dados_garmin['kcal_gasto']} kcal | Sono: {dados_garmin['sono']}h")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    hoje     = date.today()
    hoje_br  = hoje.strftime("%d/%m/%Y")
    hoje_iso = hoje.isoformat()

    print(f"\n{'='*50}")
    print(f"RFS Garmin Sync — {hoje_br}")
    print(f"{'='*50}\n")

    dados = buscar_garmin(hoje_iso)
    atualizar_csv(dados, hoje_br)

    print("\n🎉 Sync concluído!")


if __name__ == "__main__":
    main()
