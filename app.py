import streamlit as st
import math
import pandas as pd


# ------------------------------------------------------------------------------
# 1. Finanzmathematische Rechenlogik (Bankenpraxis inkl. Effektivwerten)
# ------------------------------------------------------------------------------
def berechne_annuitaetendarlehen(S_0, i_nom, modus, t_1=None, r=None, n_jahre=None):
    """
    S_0   : Kreditsumme
    i_nom : Nominaler Jahreszinssatz der Bank (i mit Dach ^)
    t_1   : Nominale Anfangstilgung der Bank (t mit Dach ^)
    """
    i_M = i_nom / 12.0
    q_M = 1.0 + i_M

    # Effektiver Jahreszinssatz nach PAngV (ohne Zusatzgebühren)
    i_eff = (q_M ** 12) - 1.0

    # Modus 1: Über anfänglichen Tilgungssatz (t_1)
    if modus == 1:
        if t_1 is None or t_1 <= 0:
            raise ValueError("Der Tilgungssatz muss größer als 0 sein.")
        r = (S_0 * (i_nom + t_1)) / 12.0
        N = math.log(1.0 + (i_nom / t_1)) / math.log(q_M)
        n_jahre = N / 12.0

    # Modus 2: Über monatliche Rate (r)
    elif modus == 2:
        mindestrate = S_0 * i_M
        if r is None or r <= mindestrate:
            raise ValueError(f"Die Monatsrate muss größer als die reinen Zinsen ({mindestrate:.2f} €) sein.")
        t_1 = (12.0 * r / S_0) - i_nom
        N = -math.log(1.0 - (i_M * S_0 / r)) / math.log(q_M)
        n_jahre = N / 12.0

    # Modus 3: Über Laufzeit in Jahren (n_jahre)
    elif modus == 3:
        if n_jahre is None or n_jahre <= 0:
            raise ValueError("Die Laufzeit muss positiv sein.")
        N = n_jahre * 12.0
        r = S_0 * ((q_M ** N) * i_M) / ((q_M ** N) - 1.0)
        t_1 = (12.0 * r / S_0) - i_nom

    # Berechnung der nominalen vs. tatsächlichen (effektiven) Jahresgrößen
    R_nom = 12.0 * r
    R_eff = r * (i_eff / i_M)
    t_eff = (R_eff / S_0) - i_eff

    # Monatliche Simulation
    restschuld = S_0
    aktuelle_laufzeit_monate = math.ceil(N)

    daten_jahre = []
    daten_monate = []

    gesamtzinsen_kum = 0.0
    gesamttilgung_kum = 0.0

    jahr_zinsen = 0.0
    jahr_tilgung = 0.0
    jahr_raten = 0.0

    volle_raten_anzahl = 0
    schlussrate = r

    for m in range(1, aktuelle_laufzeit_monate + 1):
        zins_m = restschuld * i_M

        if restschuld + zins_m <= r + 1e-9:
            rate_m = restschuld + zins_m
            tilgung_m = restschuld
            restschuld = 0.0
            schlussrate = rate_m
        else:
            rate_m = r
            tilgung_m = rate_m - zins_m
            restschuld -= tilgung_m
            volle_raten_anzahl += 1

        gesamtzinsen_kum += zins_m
        gesamttilgung_kum += tilgung_m

        jahr_zinsen += zins_m
        jahr_tilgung += tilgung_m
        jahr_raten += rate_m

        daten_monate.append({
            "Monat": m,
            "Zinsen_kum": gesamtzinsen_kum,
            "Tilgung_kum": gesamttilgung_kum,
            "Restschuld": restschuld
        })

        # Jahresabschluss (alle 12 Monate oder bei Volltilgung)
        if m % 12 == 0 or restschuld == 0.0:
            k = math.ceil(m / 12)
            fortschritt_prozent = (gesamttilgung_kum / S_0) * 100.0
            daten_jahre.append({
                "Jahr": k,
                "Jahresrate": jahr_raten,
                "Zinszahlung": jahr_zinsen,
                "Tilgung": jahr_tilgung,
                "Restschuld": restschuld,
                "Zinsen kumuliert": gesamtzinsen_kum,
                "Tilgung kumuliert": gesamttilgung_kum,
                "Tilgungsfortschritt": fortschritt_prozent
            })

            jahr_zinsen = 0.0
            jahr_tilgung = 0.0
            jahr_raten = 0.0

        if restschuld == 0.0:
            break

    return {
        "S_0": S_0,
        "i_nom": i_nom,
        "i_eff": i_eff,
        "i_M": i_M,
        "q_M": q_M,
        "t_1": t_1,
        "t_eff": t_eff,
        "r": r,
        "R_nom": R_nom,
        "R_eff": R_eff,
        "N_monate": N,
        "volle_raten": volle_raten_anzahl,
        "schlussrate": schlussrate,
        "laufzeit_jahre": n_jahre,
        "gesamtzinsen": gesamtzinsen_kum,
        "gesamtkosten": S_0 + gesamtzinsen_kum,
        "df_jahre": pd.DataFrame(daten_jahre),
        "monatsliste": daten_monate
    }


def berechne_zeitpunkt_fuer_zielwert(res, ziel_typ, ziel_betrag):
    S_0 = res["S_0"]
    i_M = res["i_M"]
    q_M = res["q_M"]
    r = res["r"]
    N = res["N_monate"]
    T_M1 = r - (S_0 * i_M)

    if ziel_betrag <= 0:
        return 0.0, 0, S_0

    if ziel_typ == "Tilgung":
        if ziel_betrag >= S_0:
            m_exakt = N
        else:
            m_exakt = math.log(1.0 + (ziel_betrag * i_M) / T_M1) / math.log(q_M)

        monat_bank = len(res["monatsliste"])
        restschuld_dann = 0.0
        for eintrag in res["monatsliste"]:
            if eintrag["Tilgung_kum"] >= ziel_betrag - 1e-6:
                monat_bank = eintrag["Monat"]
                restschuld_dann = eintrag["Restschuld"]
                break
    else:
        if ziel_betrag >= res["gesamtzinsen"]:
            m_exakt = N
        else:
            low, high = 0.0, N
            for _ in range(60):
                mid = (low + high) / 2.0
                t_kum_mid = (T_M1 / i_M) * ((q_M ** mid) - 1.0)
                z_kum_mid = (mid * r) - t_kum_mid
                if z_kum_mid < ziel_betrag:
                    low = mid
                else:
                    high = mid
            m_exakt = (low + high) / 2.0

        monat_bank = len(res["monatsliste"])
        restschuld_dann = 0.0
        for eintrag in res["monatsliste"]:
            if eintrag["Zinsen_kum"] >= ziel_betrag - 1e-6:
                monat_bank = eintrag["Monat"]
                restschuld_dann = eintrag["Restschuld"]
                break

    return m_exakt, monat_bank, restschuld_dann


# ------------------------------------------------------------------------------
# 2. Browser-Benutzeroberfläche
# ------------------------------------------------------------------------------
st.set_page_config(page_title="Annuitätendarlehensrechner", layout="wide")

# CSS: Verhindert das Abschneiden (...) der Zahlen in allen Ergebnis-Kacheln
st.markdown("""
<style>
div[data-testid="stMetricValue"] > div {
    white-space: nowrap !important;
    overflow: visible !important;
    text-overflow: unset !important;
    font-size: clamp(1.3rem, 2.0vw, 2.1rem) !important;
}
</style>
""", unsafe_allow_html=True)

st.title("🏦 Rechner für Annuitätendarlehen")
st.markdown("Berechnung nach deutscher **Bankenpraxis (monatliche Verrechnung)** inklusive Effektivzins-Analyse.")

# Seitenleiste: Eingaben
st.sidebar.header("Kreditparameter")
S_0 = st.sidebar.number_input("Darlehensbetrag S₀ (€)", min_value=1_000.0, max_value=5_000_000.0, value=100_000.0, step=5_000.0)

zins_typ = st.sidebar.selectbox(
    "Art der Zinseingabe:",
    ["Nominalzinssatz / Sollzins (î)", "Effektiver Jahreszins (i_eff)"]
)

zins_eingabe = st.sidebar.number_input("Zinssatz p.a. (%)", min_value=0.01, max_value=20.0, value=4.0, step=0.1)

if zins_typ.startswith("Nominal"):
    i_nom = zins_eingabe / 100.0
else:
    i_eff_input = zins_eingabe / 100.0
    i_nom = 12.0 * (((1.0 + i_eff_input) ** (1.0 / 12.0)) - 1.0)

modus_auswahl = st.sidebar.radio(
    "Berechnungsmethode:",
    [
        "1. Über anfänglichen Tilgungssatz (t̂)",
        "2. Über monatliche Rate (r)",
        "3. Über feste Laufzeit (n)"
    ]
)

t_1_val, r_val, n_val = None, None, None

if modus_auswahl.startswith("1"):
    modus = 1
    t1_eingabe = st.sidebar.number_input("Anfänglicher Tilgungssatz p.a. (%)", min_value=0.1, max_value=50.0, value=3.5, step=0.1)
    t_1_val = t1_eingabe / 100.0
elif modus_auswahl.startswith("2"):
    modus = 2
    r_val = st.sidebar.number_input("Monatliche Wunschrate (€)", min_value=10.0, max_value=50_000.0, value=650.0, step=25.0)
else:
    modus = 3
    n_val = st.sidebar.number_input("Gewünschte Laufzeit (Jahre)", min_value=1.0, max_value=60.0, value=15.0, step=1.0)

# Hauptberechnung ausführen
try:
    res = berechne_annuitaetendarlehen(S_0=S_0, i_nom=i_nom, modus=modus, t_1=t_1_val, r=r_val, n_jahre=n_val)

    # Dezente Toast-Benachrichtigung bei Parameteränderung
    aktuelle_signatur = f"{S_0}_{i_nom:.6f}_{modus}_{t_1_val}_{r_val}_{n_val}"
    if st.session_state.get("letzte_signatur") != aktuelle_signatur:
        st.session_state["letzte_signatur"] = aktuelle_signatur
        st.toast(f"Tilgungsplan aktualisiert! Monatsrate: {res['r']:,.2f} €", icon="✨")

    # 1. Haupt-Kennzahlen (volle Zahlenanzeige ohne Abschneiden)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Monatliche Rate (r)", f"{res['r']:,.2f} €")
    col2.metric("Gesamtlaufzeit", f"{res['laufzeit_jahre']:.2f} Jahre", f"{res['N_monate']:.2f} Monate")
    col3.metric("Gesamtzinsen", f"{res['gesamtzinsen']:,.2f} €")
    col4.metric("Gesamtaufwand", f"{res['gesamtkosten']:,.2f} €")

    # 2. Aufklappbare Detail-Übersicht (Überschriften zentriert, Linien & Boxen auf einer Höhe)
    with st.expander("📊 Details: Bank-Nominalwerte (mit ^) vs. Tatsächliche Effektivwerte & Schlussrate", expanded=True):
        # Reihe A: Zentrierte Überschriften
        h_col1, h_col2, h_col3 = st.columns(3)
        with h_col1:
            st.markdown("<h3 style='text-align: center; margin-bottom: 0;'>Zinssatz p.a.</h3>", unsafe_allow_html=True)
        with h_col2:
            st.markdown("<h3 style='text-align: center; margin-bottom: 0;'>Anfangstilgung & Jahresraten</h3>", unsafe_allow_html=True)
        with h_col3:
            st.markdown("<h3 style='text-align: center; margin-bottom: 0;'>Ratenstruktur & Schlussrate</h3>", unsafe_allow_html=True)

        # Reihe B: Trennlinien & Aufzählungspunkte (starten exakt auf derselben Höhe)
        c_col1, c_col2, c_col3 = st.columns(3)
        with c_col1:
            st.markdown("---")
            st.markdown(f"- **Nominalzins Bank ($\\hat{{i}}$):** {res['i_nom']*100:.3f} %")
            st.markdown(f"- **Effektivzins ($i_{{\\text{{eff}}}}$):** {res['i_eff']*100:.3f} %")

        with c_col2:
            st.markdown("---")
            st.markdown(f"- **Nominale Tilgung ($\\hat{{t}}$):** {res['t_1']*100:.3f} % ({res['S_0']*res['t_1']:,.2f} €)")
            st.markdown(f"- **Tatsächliche Tilgung Jahr 1 ($t$):** {res['t_eff']*100:.3f} % ({res['S_0']*res['t_eff']:,.2f} €)")

        with c_col3:
            st.markdown("---")
            st.markdown(f"- **Volle Monatsraten:** {res['volle_raten']} Raten à {res['r']:,.2f} €")
            if res['schlussrate'] < res['r'] - 0.01:
                st.markdown(f"- **Letzte Rate (im {res['volle_raten']+1}. Monat):** {res['schlussrate']:,.2f} €")
            else:
                st.markdown("- **Letzte Rate:** Exakt volle Rate")

        # Reihe C: Blaue Info-Boxen (ebenfalls exakt auf einer Höhe)
        i_col1, i_col2, i_col3 = st.columns(3)
        with i_col1:
            st.info(f"**Monatszins ($i_M$):** {res['i_M']*100:.4f} %")
        with i_col2:
            st.info(f"**Summe 12 Raten ($\\hat{{R}}$):** {res['R_nom']:,.2f} €  \n**Äquivalenzrate ($R$):** {res['R_eff']:,.2f} €")
        with i_col3:
            st.info(f"**Exakte Laufzeit:** {res['N_monate']:.2f} Monate")

    st.write("---")

    # 3. Tilgungstabelle nach Kalenderjahren inkl. Fortschrittsbalken
    st.subheader("Tilgungsplan nach Kalenderjahren")
    df_anzeige = res["df_jahre"].copy()
    format_dict = {
        "Jahresrate": "{:,.2f} €",
        "Zinszahlung": "{:,.2f} €",
        "Tilgung": "{:,.2f} €",
        "Restschuld": "{:,.2f} €",
        "Zinsen kumuliert": "{:,.2f} €",
        "Tilgung kumuliert": "{:,.2f} €"
    }
    st.dataframe(
        df_anzeige.style.format(format_dict),
        column_config={
            "Tilgungsfortschritt": st.column_config.ProgressColumn(
                "Tilgungsfortschritt",
                help="Anteil der bereits abbezahlten Kreditsumme",
                format="%.1f %%",
                min_value=0.0,
                max_value=100.0
            )
        },
        use_container_width=True,
        hide_index=True
    )

    # CSV-Download-Button
    csv_daten = res["df_jahre"].to_csv(index=False, sep=";").encode("utf-8-sig")
    st.download_button(
        label="📥 Tilgungsplan als CSV herunterladen",
        data=csv_daten,
        file_name="tilgungsplan.csv",
        mime="text/csv"
    )

    st.write("---")

    # 4. Zielwert-Abfrage (Kumulierte Zinsen oder Tilgung -> Laufzeit)
    st.subheader("🎯 Zielwert-Rechner: Wann ist eine bestimmte Summe erreicht?")
    z_col1, z_col2 = st.columns([1, 2])

    with z_col1:
        ziel_kategorie = st.radio(
            "Welche Summe möchtest du prüfen?",
            ["Kumulierte Tilgung", "Kumulierte Zinszahlungen"]
        )

    with z_col2:
        if ziel_kategorie == "Kumulierte Tilgung":
            max_wert = float(res["S_0"])
            standard_wert = round(max_wert / 2.0, 2)
            ziel_betrag = st.number_input(
                f"Gewünschte Tilgungssumme (max. {max_wert:,.2f} €):",
                min_value=0.0,
                max_value=max_wert,
                value=standard_wert,
                step=1_000.0
            )
            typ_kurz = "Tilgung"
        else:
            max_wert = float(res["gesamtzinsen"])
            standard_wert = round(max_wert / 2.0, 2)
            ziel_betrag = st.number_input(
                f"Gewünschte Zinssumme (max. {max_wert:,.2f} €):",
                min_value=0.0,
                max_value=max_wert,
                value=standard_wert,
                step=500.0
            )
            typ_kurz = "Zinsen"

    m_exakt, monat_bank, restschuld_dann = berechne_zeitpunkt_fuer_zielwert(res, typ_kurz, ziel_betrag)
    jahre_exakt = m_exakt / 12.0
    ganze_jahre = monat_bank // 12
    rest_monate = monat_bank % 12

    erg_col1, erg_col2, erg_col3, erg_col4 = st.columns(4)
    erg_col1.metric("Exakte Dauer (Monate)", f"{m_exakt:.2f} Monate")
    erg_col2.metric("Exakte Dauer (Jahre)", f"{jahre_exakt:.2f} Jahre")
    erg_col3.metric("Erreicht mit Monatsrate Nr.", f"{monat_bank}. Monat", f"{ganze_jahre} J. und {rest_monate} Mon.")
    erg_col4.metric("Restschuld nach dieser Rate", f"{restschuld_dann:,.2f} €")

    # Visueller Laufzeit-Fortschrittsbalken für den Zielwert
    zeit_anteil = min(max(m_exakt / res["N_monate"], 0.0), 1.0)
    st.progress(zeit_anteil, text=f"Zeitlicher Fortschritt bis zum Zielwert: {zeit_anteil*100:.1f} % der Gesamtlaufzeit")

    st.write("---")

    # 5. Grafischer Verlauf
    st.subheader("Verlauf von Restschuld, kumulierter Tilgung und Zinsen")
    chart_df = res["df_jahre"].set_index("Jahr")[["Restschuld", "Tilgung kumuliert", "Zinsen kumuliert"]]
    st.line_chart(chart_df)

except Exception as e:
    st.error(f"Fehler bei der Berechnung: {e}")