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

# Custom CSS to enforce a darker/professional look if standard dark mode is not forced by user config
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
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://cetip:cetip2026@localhost:5432/cetip_db")
FASTAPI_URL = os.getenv("FASTAPI_URL", "http://localhost:8000")

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
    
    # Check last processed file
    df_last = get_data("""
        SELECT MAX(date_execution) as last_exec, fichier_source 
        FROM fact_traitements 
        GROUP BY fichier_source 
        ORDER BY last_exec DESC LIMIT 1
    """)
    
    if not df_last.empty:
        last_exec = df_last.iloc[0]['last_exec']
        fichier = df_last.iloc[0]['fichier_source']
        st.info(f"**Dernier bordereau traité :** {fichier} (le {last_exec})")
    else:
        st.info("Aucun bordereau traité pour le moment.")
        
    # KPIs
    df_kpi = get_data("""
        SELECT 
            COUNT(id) as total_lignes,
            SUM(CASE WHEN statut = 'REJETE' THEN 1 ELSE 0 END) as lignes_rejetees,
            SUM(CASE WHEN flag_anomalie = 'ANOMALIE' THEN 1 ELSE 0 END) as anomalies,
            SUM(CASE WHEN statut = 'VALIDE' THEN montant ELSE 0 END) as montant_total
        FROM fact_traitements
    """)
    
    if not df_kpi.empty:
        kpi = df_kpi.iloc[0]
        total = kpi['total_lignes'] or 0
        rejets = kpi['lignes_rejetees'] or 0
        anomalies = kpi['anomalies'] or 0
        montant = kpi['montant_total'] or 0
        
        taux_rejet = (rejets / total * 100) if total > 0 else 0
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Lignes Traitées", f"{total:,}")
        col2.metric("Taux de Rejet", f"{taux_rejet:.1f}%")
        col3.metric("Anomalies Détectées", f"{anomalies}")
        col4.metric("Montant Validé", f"{montant:,.2f} €")
    
    st.markdown("---")
    st.subheader("État du Système")
    
    if df_last.empty:
        st.warning("⏳ En attente de données...")
    elif anomalies > 0:
        st.error("❌ Erreur / Alertes détectées (Anomalies présentes)")
    else:
        st.success("✅ Succès - Traitement normal")
        
    # Auto-refresh (Issue 12: proper non-blocking auto-refresh)
    st_autorefresh(interval=30000, key="realtime_refresh")

# ==============================================================================
# PAGE 2: Analyse des Rejets
# ==============================================================================
def page_analyse_rejets():
    st.title("🚫 Analyse des Rejets")
    
    # Global data for filters
    df_raw = get_data("SELECT * FROM fact_traitements WHERE statut = 'REJETE'")
    
    if df_raw.empty:
        st.success("Aucun rejet détecté dans la base de données.")
        return
        
    # Filters
    st.sidebar.subheader("Filtres")
    ps_list = df_raw['num_ps'].unique().tolist()
    selected_ps = st.sidebar.multiselect("Filtrer par PS", ps_list)
    
    raisons = df_raw['raison_rejet'].unique().tolist()
    selected_raison = st.sidebar.multiselect("Raison du Rejet", raisons)
    
    # Apply filters
    df_filtered = df_raw.copy()
    if selected_ps:
        df_filtered = df_filtered[df_filtered['num_ps'].isin(selected_ps)]
    if selected_raison:
        df_filtered = df_filtered[df_filtered['raison_rejet'].isin(selected_raison)]
        
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Répartition des causes")
        rejet_counts = df_filtered['raison_rejet'].value_counts().reset_index()
        rejet_counts.columns = ['raison_rejet', 'count']
        fig_pie = px.pie(rejet_counts, values='count', names='raison_rejet', hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)
        
    with col2:
        st.subheader("Top 10 PS par Rejets")
        top_ps = df_filtered['num_ps'].value_counts().head(10).reset_index()
        top_ps.columns = ['num_ps', 'count']
        fig_bar = px.bar(top_ps, x='num_ps', y='count')
        st.plotly_chart(fig_bar, use_container_width=True)
        
    st.subheader("Détail des lignes rejetées")
    st.dataframe(df_filtered[['num_ps', 'num_virement', 'montant', 'raison_rejet', 'date_execution']], use_container_width=True)

# ==============================================================================
# PAGE 3: Fraud Investigator
# ==============================================================================
def highlight_score(val):
    try:
        score = float(val)
        if score > 0.8:
            return 'background-color: #8B0000; color: white' # Dark Red
        elif score >= 0.5:
            return 'background-color: #B8860B; color: white' # Dark Goldenrod (Orange/Yellow)
        else:
            return 'background-color: #556B2F; color: white' # Dark Olive Green
    except:
        return ''

def page_fraud_investigator():
    st.title("🕵️ Fraud Investigator")
    
    df_anomalies = get_data("""
        SELECT 
            id, num_ps, num_virement, montant, 
            score_anomalie, ecart_vs_historique, 
            montant_moyen_historique_ps as historique_moyen, 
            date_execution
        FROM fact_traitements 
        WHERE flag_anomalie = 'ANOMALIE'
        ORDER BY score_anomalie DESC
    """)
    
    if df_anomalies.empty:
        st.success("Aucune anomalie détectée.")
        return
        
    total_risk = df_anomalies['montant'].sum()
    st.warning(f"**Montant total à risque : {total_risk:,.2f} €**")
    
    st.markdown("### Liste des Transactions Suspectes")
    st.caption("Sélectionnez une ligne dans le tableau pour analyser l'historique du PS.")
    
    # Style dataframe
    styled_df = df_anomalies.style.map(highlight_score, subset=['score_anomalie'])
    
    # Streamlit 1.35.0 feature: on_select
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
            st.metric("Ecart vs Historique", f"{selected_row['ecart_vs_historique']}%")
            
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
                
                # Convert dict to dataframe for plotting
                df_shap = pd.DataFrame(list(shap_values.items()), columns=['Feature', 'Contribution'])
                df_shap = df_shap.sort_values(by='Contribution', ascending=True)
                
                # Determine colors based on sign
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
            
            st.markdown("---")
            if st.button("Marquer comme verifie (Faux Positif)", use_container_width=True):
                try:
                    resp = requests.post(
                        f"{FASTAPI_URL}/review/{selected_row['id']}",
                        json={"reviewer": "analyst"},
                        timeout=5
                    )
                    if resp.status_code == 200:
                        st.success("Transaction marquee comme verifiee en base de donnees.")
                        st.rerun()
                    else:
                        engine = get_db_connection()
                        with engine.connect() as conn:
                            conn.execute(
                                text("UPDATE fact_traitements SET reviewed = TRUE, reviewed_at = NOW(), reviewed_by = 'analyst' WHERE id = :tid"),
                                {"tid": int(selected_row['id'])}
                            )
                            conn.commit()
                        st.success("Transaction marquee comme verifiee (acces direct BDD).")
                        st.rerun()
                except Exception as e:
                    st.error(f"Erreur: {e}")
                
        with col_b:
            stats = fetch_ps_history(selected_row['num_ps'])
            if stats and stats['count'] > 0:
                # Mock a scatter plot showing the mean vs the current
                mean_montant = stats['mean_montant']
                std_montant = stats['std_montant']
                
                fig = go.Figure()
                
                # Historic Mean line
                fig.add_trace(go.Bar(
                    x=["Moyenne Historique", "Transaction Actuelle"],
                    y=[mean_montant, selected_row['montant']],
                    marker_color=['#1f77b4', '#d62728']
                ))
                
                # Add standard deviation error bar to history
                fig.data[0].error_y = dict(
                    type='data',
                    array=[std_montant, 0],
                    visible=True
                )
                
                fig.update_layout(title="Comparaison Montant Actuel vs Historique PS", template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Historique insuffisant pour afficher le graphique de distribution.")

# ==============================================================================
# PAGE 4: Performance Opérationnelle
# ==============================================================================
def page_performance():
    st.title("📈 Performance Opérationnelle")
    
    # 1. Volume par semaine
    df_vol = get_data("""
        SELECT d.semaine, COUNT(f.id) as volume, SUM(f.montant) as montant
        FROM fact_traitements f
        JOIN dim_date d ON f.date_execution::DATE = to_date(d.date_id::TEXT, 'YYYYMMDD')
        GROUP BY d.semaine
        ORDER BY d.semaine
    """)
    if not df_vol.empty:
        fig1 = px.line(df_vol, x='semaine', y='volume', title="Volume traité par semaine", markers=True)
        st.plotly_chart(fig1, use_container_width=True)
        
    col1, col2 = st.columns(2)
    
    # 2. Montant par spécialité
    df_spec = get_data("""
        SELECT p.specialite, SUM(f.montant) as montant_total
        FROM fact_traitements f
        JOIN dim_ps p ON f.num_ps = p.num_ps
        WHERE f.statut = 'VALIDE'
        GROUP BY p.specialite
        ORDER BY montant_total DESC
    """)
    with col1:
        if not df_spec.empty:
            fig2 = px.bar(df_spec, x='specialite', y='montant_total', title="Montant validé par spécialité")
            st.plotly_chart(fig2, use_container_width=True)
            
    # 3. Clean claim rate par région
    df_region = get_data("""
        SELECT p.region, 
               ROUND((SUM(CASE WHEN f.statut = 'VALIDE' THEN 1 ELSE 0 END) * 100.0) / COUNT(f.id), 2) as clean_rate
        FROM fact_traitements f
        JOIN dim_ps p ON f.num_ps = p.num_ps
        GROUP BY p.region
    """)
    with col2:
        if not df_region.empty:
            fig3 = px.bar(df_region, x='region', y='clean_rate', title="Clean Claim Rate par Région (%)")
            fig3.update_layout(yaxis_range=[0, 100])
            st.plotly_chart(fig3, use_container_width=True)
            
    # 4. Distribution des scores d'anomalie
    df_scores = get_data("SELECT score_anomalie FROM fact_traitements WHERE score_anomalie IS NOT NULL")
    if not df_scores.empty:
        fig4 = px.histogram(df_scores, x='score_anomalie', nbins=20, title="Distribution des scores d'anomalie")
        st.plotly_chart(fig4, use_container_width=True)

# ==============================================================================
# ROUTING
# ==============================================================================
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/ca/Cegedim_logo.svg/1200px-Cegedim_logo.svg.png", width=150)
st.sidebar.title("Navigation")
page = st.sidebar.radio("Aller à", [
    "1. Vue Temps Réel", 
    "2. Analyse des Rejets", 
    "3. Fraud Investigator", 
    "4. Performance Opérationnelle"
])

if page == "1. Vue Temps Réel":
    page_vue_temps_reel()
elif page == "2. Analyse des Rejets":
    page_analyse_rejets()
elif page == "3. Fraud Investigator":
    page_fraud_investigator()
elif page == "4. Performance Opérationnelle":
    page_performance()
