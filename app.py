import streamlit as st
import pandas as pd
import numpy as np
import joblib
import matplotlib.pyplot as plt

st.set_page_config(page_title="CyberShield AI", page_icon="🛡️", layout="wide")

# Dark theme styling
st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background-color: #0e1117; }
.metric-card { background: #1c2333; border-radius: 10px; padding: 15px; text-align: center; border: 1px solid #2d3748; }
.attack-dos   { color: #ff4b4b; font-weight: bold; }
.attack-probe { color: #ffd700; font-weight: bold; }
.attack-r2l   { color: #ffa500; font-weight: bold; }
.attack-u2r   { color: #ff0000; font-weight: bold; }
.attack-normal{ color: #00cc44; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ CyberShield AI — Network Security Dashboard")
st.markdown("Real-time network intrusion detection powered by Machine Learning")

# Load models
@st.cache_resource
def load_all():
    return {
        "scaler":      joblib.load("models/scaler.pkl"),
        "pca":         joblib.load("models/pca.pkl"),
        "nb":          joblib.load("models/naive_bayes.pkl"),
        "lr":          joblib.load("models/logistic_regression.pkl"),
        "svm":         joblib.load("models/svm.pkl"),
        "rf":          joblib.load("models/random_forest.pkl"),
        "le_attack":   joblib.load("models/le_attack.pkl"),
        "le_protocol": joblib.load("models/le_protocol.pkl"),
        "le_service":  joblib.load("models/le_service.pkl"),
        "le_flag":     joblib.load("models/le_flag.pkl"),
    }

assets = load_all()

# Sidebar
st.sidebar.image("https://img.icons8.com/fluency/96/firewall.png", width=80)
st.sidebar.title("CyberShield AI")
st.sidebar.markdown("---")
model_choice = st.sidebar.radio("Select Detection Model", ["SVM", "Naive Bayes", "Logistic Regression"])
st.sidebar.markdown("---")
st.sidebar.markdown("**Attack Types:**")
st.sidebar.markdown("✅ Normal — Safe traffic")
st.sidebar.markdown("🔴 DoS — Denial of Service")
st.sidebar.markdown("🟡 Probe — Network Scanning")
st.sidebar.markdown("🟠 R2L — Remote to Local")
st.sidebar.markdown("🚨 U2R — Root Privilege Attack")

# Upload
st.subheader("📂 Upload Network Traffic Data")
uploaded_file = st.file_uploader("Upload CSV file (NSL-KDD format)", type="csv")

def get_emoji(attack):
    return {"Normal": "✅ Normal", "DoS": "🔴 DoS",
            "Probe": "🟡 Probe", "R2L": "🟠 R2L", "U2R": "🚨 U2R"}.get(attack, "⚪ Unknown")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    original_df = df.copy()

    # Encode categorical columns using saved encoders
    df["protocol_type"] = assets["le_protocol"].transform(df["protocol_type"])
    df["service"]       = assets["le_service"].transform(df["service"])
    df["flag"]          = assets["le_flag"].transform(df["flag"])

    if "labels" in df.columns:
        df = df.drop("labels", axis=1)

    # Binary prediction
    X_scaled = assets["scaler"].transform(df)
    X_pca    = assets["pca"].transform(X_scaled)

    if model_choice == "SVM":
        model = assets["svm"]
    elif model_choice == "Naive Bayes":
        model = assets["nb"]
    else:
        model = assets["lr"]

    binary_preds = model.predict(X_pca)
    probs        = model.predict_proba(X_pca)[:, 1]

    # Attack type prediction using Random Forest
    attack_encoded = assets["rf"].predict(X_scaled)
    attack_types   = assets["le_attack"].inverse_transform(attack_encoded)

    # Build results
    original_df["Binary"]      = ["🚨 ATTACK" if p == 1 else "✅ NORMAL" for p in binary_preds]
    original_df["Attack Type"] = [get_emoji(a) for a in attack_types]
    original_df["Confidence"]  = [f"{p:.1%}" for p in probs]

    # Metrics row
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📊 Total Records",    len(df))
    col2.metric("🚨 Attacks Detected", int(sum(binary_preds)))
    col3.metric("✅ Normal Traffic",   int(sum(binary_preds == 0)))
    col4.metric("🎯 Model Used",       model_choice)

    # Danger alerts
    u2r_count = list(attack_types).count("U2R")
    r2l_count = list(attack_types).count("R2L")
    if u2r_count > 0:
        st.error(f"🚨 CRITICAL: {u2r_count} U2R (Root Privilege) attacks detected! Immediate action required!")
    if r2l_count > 0:
        st.warning(f"🟠 WARNING: {r2l_count} R2L (Remote to Local) attacks detected!")

    # Charts
    st.markdown("---")
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.subheader("📊 Attack Type Breakdown")
        attack_counts = pd.Series(attack_types).value_counts()
        colors = {"Normal":"#00cc44","DoS":"#ff4b4b","Probe":"#ffd700","R2L":"#ffa500","U2R":"#ff0000"}
        fig, ax = plt.subplots(figsize=(5, 4), facecolor="#0e1117")
        ax.set_facecolor("#1c2333")
        bars = ax.bar(attack_counts.index,
                      attack_counts.values,
                      color=[colors.get(k, "#888") for k in attack_counts.index])
        ax.tick_params(colors="white")
        ax.title.set_color("white")
        ax.set_title("Attack Distribution")
        for spine in ax.spines.values():
            spine.set_edgecolor("#2d3748")
        st.pyplot(fig)

    with col_chart2:
        st.subheader("🥧 Traffic Composition")
        fig2, ax2 = plt.subplots(figsize=(5, 4), facecolor="#0e1117")
        ax2.set_facecolor("#1c2333")
        labels_pie = attack_counts.index
        colors_pie = [colors.get(k, "#888") for k in labels_pie]
        ax2.pie(attack_counts.values, labels=labels_pie, colors=colors_pie,
                autopct="%1.1f%%", textprops={"color": "white"})
        st.pyplot(fig2)

    # Results table
    st.markdown("---")
    st.subheader("📋 Detailed Prediction Results")
    st.dataframe(original_df[["Binary", "Attack Type", "Confidence"] +
                 list(original_df.columns[:6])], use_container_width=True)