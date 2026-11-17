"""
================================================================================
STRATÉGIE : ACHAT SUR CAPITULATION EXTRÊME DU VIX (STRATÉGIE A - SORTIE J+30)
================================================================================

1. RÈGLE DE DÉCLENCHEMENT (SIGNAL) :
   - Le VIX (^VIX) enregistre une hausse journalière > +50 % par rapport à sa
     clôture de la veille.
   - Cooldown : Ignorer tout nouveau signal si un achat a déjà été effectué dans
     les 5 derniers jours de bourse (évite les doublons lors d'un même krach).

2. EXÉCUTION DE L'ENTRÉE :
   - Timing : À l'approche de la clôture le jour du signal (vers 17h20 sur PEA /
     Euronext Paris, ou 21h50 sur CTO / horaire US).
   - Supports : ETF S&P 500 classique (x1 : ESE, PE500, SPY) ou ETF Levier x2
     journalier (CL2 sur PEA / SSO sur CTO).
   - Gestion du risque : Allouer max 15 % à 25 % du portefeuille sur la poche x2.

3. GESTION DE LA POSITION & SORTIE :
   - AUCUN STOP-LOSS : Historiquement, le marché subit une réplique baissière de
     -3 % à -9 % dans les 2 à 5 jours suivant le pic avant de rebondir.
   - Sortie temporelle fixe : Revente de 100 % de la position exactement 30 jours
     de bourse (environ 6 semaines calendaires) après l'entrée.

4. STATISTIQUES HISTORIQUES (1990 - 2026 | 9 TRADES CLÔTURÉS) :
   - Taux de réussite à J+30 : 88,9 % (8 gagnants / 1 perdant en juillet 1990).
   - Sans levier (x1) : Gain moyen +4,45 % | Drawdown moyen -3,75 % (pire -13,83 %).
   - Levier x2 (CL2)  : Gain moyen +8,65 % | Drawdown moyen -7,46 % (pire -26,35 %).
================================================================================
"""

import yfinance as yf
import pandas as pd
import requests
from datetime import datetime

# --- CONFIGURATION ---
DISCORD_WEBHOOK_URL = "COLLE_TON_URL_WEBHOOK_DISCORD_ICI"
VIX_THRESHOLD = 0.50          # Seuil de déclenchement (+50 %)
HOLDING_TRADING_DAYS = 30     # Durée de détention en jours de bourse
TEST_MODE = True            # Passer à True pour tester l'envoi Discord immédiatement


def get_market_data():
    """Récupère les 5 dernières séances du VIX et du S&P 500."""
    vix = yf.Ticker("^VIX").history(period="5d")
    sp500 = yf.Ticker("^GSPC").history(period="5d")

    if len(vix) < 2 or len(sp500) < 2:
        raise ValueError("Données insuffisantes récupérées depuis Yahoo Finance.")

    prev_vix = vix['Close'].iloc[-2]
    curr_vix = vix['Close'].iloc[-1]
    vix_change = (curr_vix / prev_vix) - 1

    curr_sp500 = sp500['Close'].iloc[-1]
    sp500_change = (curr_sp500 / sp500['Close'].iloc[-2]) - 1
    last_date = vix.index[-1]

    return {
        "date": last_date,
        "prev_vix": prev_vix,
        "curr_vix": curr_vix,
        "vix_change": vix_change,
        "curr_sp500": curr_sp500,
        "sp500_change": sp500_change
    }


def estimate_exit_date(start_date, trading_days=30):
    """Estime la date de sortie à J+30 jours ouvrés (hors week-ends)."""
    exit_dt = pd.Timestamp(start_date) + pd.offsets.BDay(trading_days)
    return exit_dt.strftime("%d/%m/%Y")


def send_discord_alert(data, is_test=False):
    """Envoie une notification formatée sur Discord via Webhook."""
    exit_date_str = estimate_exit_date(data["date"], HOLDING_TRADING_DAYS)
    title_prefix = "🧪 [TEST] " if is_test else "🚨 "

    payload = {
        "username": "VIX Capitulation Bot",
        "embeds": [
            {
                "title": f"{title_prefix}SIGNAL D'ACHAT VIX DÉTECTÉ ({data['vix_change']*100:+.2f} %)",
                "description": (
                    "Le VIX a franchi le seuil critique de **+50 %** sur la séance.\n"
                    "Application du protocole **Stratégie A (Sortie J+30)**."
                ),
                "color": 15158332,  # Rouge alerte
                "fields": [
                    {
                        "name": "📈 VIX Actuel / Veille",
                        "value": f"**{data['curr_vix']:.2f}** (vs {data['prev_vix']:.2f})",
                        "inline": True
                    },
                    {
                        "name": "📉 S&P 500",
                        "value": f"**{data['curr_sp500']:.2f}** ({data['sp500_change']*100:+.2f} %)",
                        "inline": True
                    },
                    {
                        "name": "📅 Sortie prévue (J+30 ouvrés)",
                        "value": f"**{exit_date_str}** (vérifier jours fériés US)",
                        "inline": False
                    },
                    {
                        "name": "📋 Rappel d'exécution",
                        "value": (
                            "• **Achat** : 100 % de la poche allouée avant clôture (CL2 / ESE / SPY)\n"
                            "• **Stop-loss** : Aucun (tolérer -5 % à -9 % les premiers jours)\n"
                            "• **Cooldown** : Ignorer tout nouveau signal pendant 5 séances"
                        ),
                        "inline": False
                    }
                ],
                "footer": {
                    "text": f"Analyse exécutée le {datetime.now().strftime('%d/%m/%Y à %H:%M')}"
                }
            }
        ]
    }

    response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
    response.raise_for_status()
    print("Alerte Discord envoyée avec succès.")


def main():
    data = get_market_data()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] VIX: {data['curr_vix']:.2f} ({data['vix_change']*100:+.2f} %)")

    if TEST_MODE or data["vix_change"] > VIX_THRESHOLD:
        send_discord_alert(data, is_test=TEST_MODE)
    else:
        print("Aucun signal déclenché (variation <= +50 %).")


if __name__ == "__main__":
    main()
