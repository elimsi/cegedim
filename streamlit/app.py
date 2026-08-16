import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import os
from sqlalchemy import create_engine, text
from streamlit_autorefresh import st_autorefresh

# Must be the first Streamlit command
st.set_page_config(
    page_title="CETIP Fraud Investigator",
    page_icon="🕵️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS to enforce a darker/professional look
st.markdown("""
    <style>
    .stMetric {
        background-color: #1E1E1E;
        padding: 15px;
        border-radius: 5px;
        border-left: 5px solid #0055ff;
    }
    </style>
""", unsafe_allow_html=True)

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://cetip:cetip2026@postgres:5432/cetip_db")
FASTAPI_URL = os.getenv("FASTAPI_URL", "http://fastapi:8000")

@st.cache_resource
def get_db_connection():
    return create_engine(DATABASE_URL)

def get_data(query, params=None):
    engine = get_db_connection()
    try:
        return pd.read_sql(query, engine, params=params)
    except Exception as e:
        st.error(f"Erreur de base de données: {e}")
        return pd.DataFrame()

def fetch_ps_history(num_ps):
    try:
        response = requests.get(f"{FASTAPI_URL}/ps-history/{num_ps}", timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.warning(f"Impossible de contacter l'API ML: {e}")
    return None

def fetch_shap_values(transaction_id):
    try:
        response = requests.get(f"{FASTAPI_URL}/explain-shap/{transaction_id}", timeout=5)
        if response.status_code == 200:
            return response.json().get("shap_values", None)
    except Exception as e:
        pass
    return None

# ==============================================================================
# PAGE 1: Vue Temps Réel
# ==============================================================================
def page_vue_temps_reel():
    st.title("⏱️ Vue Temps Réel")
    
    # Check last processed file from silver
    df_last = get_data("""
        SELECT MAX(date_ingestion) as last_exec, fichier_source 
        FROM silver_traitements 
        GROUP BY fichier_source 
        ORDER BY last_exec DESC LIMIT 1
    """)
    
    if not df_last.empty:
        last_exec = df_last.iloc[0]['last_exec']
        fichier = df_last.iloc[0]['fichier_source']
        st.info(f"**Dernier bordereau traité :** {fichier} (le {last_exec})")
    else:
        st.info("Aucun bordereau traité pour le moment.")
        
    # KPIs from silver layer
    df_kpi = get_data("""
        SELECT 
            COUNT(id) as total_lignes,
            SUM(CASE WHEN flag_anomalie = 'ANOMALIE' THEN 1 ELSE 0 END) as anomalies,
            SUM(CASE WHEN incoherence_code_acte = TRUE THEN 1 ELSE 0 END) as incoherences_llm,
            SUM(montant) as montant_total
        FROM silver_traitements
    """)
    
    if not df_kpi.empty:
        kpi = df_kpi.iloc[0]
        total = kpi['total_lignes'] or 0
        anomalies = kpi['anomalies'] or 0
        incoherences = kpi['incoherences_llm'] or 0
        montant = kpi['montant_total'] or 0
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Lignes Traitées", f"{total:,}")
        col2.metric("Incohérences LLM", f"{incoherences}")
        col3.metric("Anomalies ML", f"{anomalies}")
        col4.metric("Montant Total", f"{montant:,.2f} €")
    
    st.markdown("---")
    st.subheader("État du Système")
    
    if df_last.empty:
        st.warning("⏳ En attente de données...")
    elif anomalies > 0 or incoherences > 0:
        st.error("❌ Alertes détectées (Anomalies présentes)")
    else:
        st.success("✅ Succès - Traitement normal")
        
    # Auto-refresh
    st_autorefresh(interval=30000, key="realtime_refresh")


# ==============================================================================
# PAGE 2: Fraud Investigator
# ==============================================================================
def highlight_score(val):
    try:
        score = float(val)
        if score > 0.8:
            return 'background-color: #8B0000; color: white'
        elif score >= 0.5:
            return 'background-color: #B8860B; color: white'
        else:
            return 'background-color: #556B2F; color: white'
    except:
        return ''

def page_fraud_investigator():
    st.title("🕵️ Fraud Investigator")
    
    # Query suspicious transactions directly from silver layer to get individual transactions
    df_anomalies = get_data("""
        SELECT 
            id, num_ps, numvir, montant, 
            score_anomalie, 0 as ecart_vs_historique, 
            date_virement as date_execution
        FROM silver_traitements 
        WHERE flag_anomalie = 'ANOMALIE' OR incoherence_code_acte = TRUE
        ORDER BY score_anomalie DESC
    """)
    
    if df_anomalies.empty:
        st.success("Aucune anomalie détectée.")
        return
        
    total_risk = df_anomalies['montant'].sum()
    st.warning(f"**Montant total à risque : {total_risk:,.2f} €**")
    
    st.markdown("### Liste des Transactions Suspectes")
    st.caption("Sélectionnez une ligne dans le tableau pour analyser.")
    
    # Style dataframe
    styled_df = df_anomalies.style.map(highlight_score, subset=['score_anomalie'])
    
    event = st.dataframe(
        styled_df, 
        use_container_width=True, 
        selection_mode="single-row",
        on_select="rerun",
        hide_index=True
    )
    
    if len(event.selection.rows) > 0:
        selected_idx = event.selection.rows[0]
        selected_row = df_anomalies.iloc[selected_idx]
        
        st.markdown("---")
        st.subheader(f"🔍 Analyse Détaillée : PS {selected_row['num_ps']}")
        
        col_a, col_b = st.columns([1, 2])
        
        with col_a:
            st.metric("Montant Suspect", f"{selected_row['montant']:,.2f} €")
            st.metric("Score Anomalie", f"{selected_row['score_anomalie']}")
            
            if st.button("Analyser avec l'IA", type="primary", use_container_width=True):
                with st.spinner("Mistral AI analyse la transaction..."):
                    try:
                        resp = requests.post(
                            f"{FASTAPI_URL}/llm-explain/{int(selected_row['id'])}",
                            timeout=30
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            st.session_state[f"llm_report_{int(selected_row['id'])}"] = data["rapport_llm"]
                        else:
                            st.error(f"Erreur API: {resp.status_code} - {resp.text}")
                    except Exception as e:
                        st.error(f"Erreur LLM: {e}")

            report_key = f"llm_report_{int(selected_row['id'])}"
            if report_key in st.session_state:
                st.markdown("""<div style="background: linear-gradient(135deg, #1a1a2e, #16213e); 
                    border-left: 4px solid #e94560; border-radius: 8px; 
                    padding: 16px; margin-top: 12px;">
                    <p style='color:#e94560; font-weight:bold; margin-bottom:8px;'>
                    Rapport d'investigation IA (Mistral)</p>""", unsafe_allow_html=True)
                st.markdown(st.session_state[report_key])
                st.markdown("</div>", unsafe_allow_html=True)
            
            # SHAP Explainability Chart
            shap_values = fetch_shap_values(int(selected_row['id']))
            if shap_values:
                st.markdown("### Explicabilité du Modèle (SHAP)")
                st.caption("Contribution de chaque variable au score d'anomalie")
                
                df_shap = pd.DataFrame(list(shap_values.items()), columns=['Feature', 'Contribution'])
                df_shap = df_shap.sort_values(by='Contribution', ascending=True)
                colors = ['#ff4b4b' if val > 0 else '#00cc96' for val in df_shap['Contribution']]
                
                fig_shap = go.Figure(go.Bar(
                    x=df_shap['Contribution'],
                    y=df_shap['Feature'],
                    orientation='h',
                    marker_color=colors
                ))
                fig_shap.update_layout(
                    margin=dict(l=0, r=0, t=10, b=0),
                    height=200,
                    template="plotly_dark",
                    xaxis_title="Impact sur le score",
                    yaxis_title=""
                )
                st.plotly_chart(fig_shap, use_container_width=True)
                
        with col_b:
            stats = fetch_ps_history(selected_row['num_ps'])
            if stats and stats['count'] > 0:
                mean_montant = stats['mean_montant']
                std_montant = stats['std_montant']
                
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=["Moyenne Historique", "Transaction Actuelle"],
                    y=[mean_montant, selected_row['montant']],
                    marker_color=['#1f77b4', '#d62728']
                ))
                fig.data[0].error_y = dict(
                    type='data', array=[std_montant, 0], visible=True
                )
                fig.update_layout(title="Comparaison Montant Actuel vs Historique PS", template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Historique insuffisant pour afficher le graphique de distribution.")

# ==============================================================================
# PAGE 3: Performance Opérationnelle (Gold Layer)
# ==============================================================================
def page_performance():
    st.title("📈 Performance Opérationnelle")
    
    # 1. Volume par semaine
    df_vol = get_data("""
        SELECT date_jour as jour, SUM(nb_transactions) as volume, SUM(montant_journalier) as montant
        FROM gold_fact_traitements
        GROUP BY date_jour
        ORDER BY date_jour
    """)
    if not df_vol.empty:
        fig1 = px.line(df_vol, x='jour', y='volume', title="Volume traité par jour", markers=True)
        st.plotly_chart(fig1, use_container_width=True)
        
    col1, col2 = st.columns(2)
    
    # 2. Montant par spécialité
    df_spec = get_data("""
        SELECT specialite, SUM(montant_journalier) as montant_total
        FROM gold_fact_traitements
        GROUP BY specialite
        ORDER BY montant_total DESC
    """)
    with col1:
        if not df_spec.empty:
            fig2 = px.bar(df_spec, x='specialite', y='montant_total', title="Montant traité par spécialité")
            st.plotly_chart(fig2, use_container_width=True)
            
    # 3. Clean claim rate par région (Approximate from anomalies)
    df_region = get_data("""
        SELECT region, 
               ROUND(((SUM(nb_transactions) - SUM(nb_anomalies)) * 100.0) / SUM(nb_transactions), 2) as clean_rate
        FROM gold_fact_traitements
        GROUP BY region
    """)
    with col2:
        if not df_region.empty:
            fig3 = px.bar(df_region, x='region', y='clean_rate', title="Clean Claim Rate par Région (%)")
            fig3.update_layout(yaxis_range=[0, 100])
            st.plotly_chart(fig3, use_container_width=True)

# ==============================================================================
# ROUTING
# ==============================================================================
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/ca/Cegedim_logo.svg/1200px-Cegedim_logo.svg.png", width=150)
st.sidebar.title("Navigation")
page = st.sidebar.radio("Aller à", [
    "1. Vue Temps Réel", 
    "2. Fraud Investigator", 
    "3. Performance Opérationnelle"
])

if page == "1. Vue Temps Réel":
    page_vue_temps_reel()
elif page == "2. Fraud Investigator":
    page_fraud_investigator()
elif page == "3. Performance Opérationnelle":
    page_performance()
