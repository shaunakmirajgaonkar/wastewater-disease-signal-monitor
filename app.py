
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="WasteWatch Local", page_icon="🧪", layout="wide")

REQUIRED = [
    "record_id","catchment_zone","sample_date","population_coverage",
    "wastewater_flow_m3_day","pathogen_marker_signal","marker_change_pct",
    "sampling_quality_score","rainfall_7d_mm","industrial_influence_score",
    "seasonality_score","local_health_trend_score","health_trend_change_pct",
    "reporting_completeness_pct","signal_persistence_days","sampling_frequency_score",
    "review_status"
]

def score_row(r):
    marker = np.clip(float(r["pathogen_marker_signal"]), 0, 100)
    change = np.clip(float(r["marker_change_pct"]) + 50, 0, 100)
    health = np.clip(float(r["local_health_trend_score"]), 0, 100)
    health_change = np.clip(float(r["health_trend_change_pct"]) + 50, 0, 100)
    persistence = np.clip(float(r["signal_persistence_days"]) / 14 * 100, 0, 100)
    quality = np.clip(float(r["sampling_quality_score"]), 0, 100)
    completeness = np.clip(float(r["reporting_completeness_pct"]), 0, 100)
    # Context/quality dampening prevents weak data from looking highly certain.
    raw = .30*marker + .18*change + .22*health + .10*health_change + .08*persistence + .07*quality + .05*completeness
    confidence = .65 + .35*(quality/100)*(completeness/100)
    return round(float(np.clip(raw*confidence, 0, 100)), 1)

def classify(s):
    if s >= 80: return "Critical Review"
    if s >= 65: return "High Review"
    if s >= 45: return "Review"
    return "Monitor"

def explanation(r):
    parts=[]
    if r.pathogen_marker_signal >= 70: parts.append("Elevated wastewater marker signal.")
    if r.marker_change_pct >= 20: parts.append("Recent marker increase is notable.")
    if r.local_health_trend_score >= 70: parts.append("Local aggregate health-trend signal is elevated.")
    if r.health_trend_change_pct >= 20: parts.append("Local trend has increased recently.")
    if r.signal_persistence_days >= 7: parts.append("Signal persistence supports continued review.")
    if r.sampling_quality_score < 70: parts.append("Sampling quality limits confidence.")
    if r.reporting_completeness_pct < 80: parts.append("Health-trend reporting completeness limits interpretation.")
    if not parts: parts.append("No major local screening signal exceeded the configured review thresholds.")
    return " ".join(parts)

st.markdown("""
<style>
.stApp{background:#f5f8fb;color:#172033}
section[data-testid="stSidebar"]{background:#fff;border-right:1px solid #dfe6ee}
.block-container{max-width:1450px;padding-top:1.8rem}
.hero{background:linear-gradient(135deg,#fff,#eef8f5);border:1px solid #dbe8e4;border-radius:22px;padding:30px 34px;margin-bottom:20px}
.hero h1{margin:0;color:#172033;font-size:2.35rem}
.hero p{color:#59697c;margin:.45rem 0 0}
.badge{display:inline-block;padding:6px 11px;border-radius:999px;background:#e8f5f1;color:#246b5d;font-weight:700;font-size:.78rem;margin-right:6px}
.section{background:#fff;border:1px solid #e1e7ee;border-radius:17px;padding:18px;box-shadow:0 4px 18px rgba(31,48,72,.045)}
.small{color:#65758a;font-size:.9rem}
div[data-testid="stMetric"]{background:#fff;border:1px solid #e1e7ee;padding:15px;border-radius:14px}
</style>
""", unsafe_allow_html=True)

if "df" not in st.session_state:
    st.session_state.df = pd.read_csv("data/synthetic_wastewater_signal_registry.csv")

with st.sidebar:
    st.markdown("## 🧪 WasteWatch Local")
    st.caption("Wastewater disease-signal screening")
    st.divider()
    st.markdown("**LOCAL-FIRST**  \n**AGGREGATE DATA**  \n**EXPLAINABLE**  \n**HUMAN REVIEW**")
    st.divider()
    uploaded = st.file_uploader("Upload authorized aggregate CSV", type=["csv"])
    if uploaded:
        try:
            candidate = pd.read_csv(uploaded)
            missing = [c for c in REQUIRED if c not in candidate.columns]
            if missing:
                st.error("Missing columns: " + ", ".join(missing))
            else:
                st.session_state.df = candidate
                st.success("Validated locally.")
                st.rerun()
        except Exception as e:
            st.error(f"CSV error: {e}")
    st.caption("Synthetic or authorized aggregate records only. No external APIs.")

df = st.session_state.df.copy()
df["sample_date"] = pd.to_datetime(df["sample_date"], errors="coerce")
df["signal_score"] = df.apply(score_row, axis=1)
df["classification"] = df["signal_score"].apply(classify)
df["explanation"] = df.apply(explanation, axis=1)

st.markdown("""
<div class="hero">
<h1>🧪 WasteWatch Local</h1>
<p><b>Wastewater Disease Signal Monitor</b> — screen aggregate wastewater and local health-trend records for potential early-warning signals that may merit qualified public-health review.</p>
<div style="margin-top:16px">
<span class="badge">100% LOCAL</span><span class="badge">NO EXTERNAL APIs</span><span class="badge">AGGREGATE ONLY</span><span class="badge">EXPLAINABLE</span>
</div>
</div>
""", unsafe_allow_html=True)

st.warning("Screening signals are not diagnoses, case counts, outbreak confirmations, transmission estimates, or individual health-risk assessments. Use qualified public-health interpretation and applicable surveillance procedures.")

a,b,c,d = st.columns(4)
a.metric("Catchment records", len(df))
b.metric("Avg signal score", f"{df.signal_score.mean():.1f}/100")
c.metric("High/Critical review", int(df.classification.isin(["High Review","Critical Review"]).sum()))
d.metric("Zones monitored", df.catchment_zone.nunique())

tab1,tab2,tab3,tab4 = st.tabs(["Signal Overview","Trend Intelligence","Zone Review","Registry & Export"])

with tab1:
    left,right=st.columns([1.5,1])
    with left:
        q=df.sort_values("sample_date")
        fig=px.line(q,x="sample_date",y="signal_score",color="catchment_zone",markers=True,title="Screening signal trend by catchment")
        fig.update_layout(template="plotly_white",height=410,margin=dict(l=20,r=20,t=60,b=20))
        st.plotly_chart(fig,use_container_width=True)
    with right:
        counts=df.classification.value_counts().reindex(["Monitor","Review","High Review","Critical Review"]).fillna(0).reset_index()
        counts.columns=["Classification","Records"]
        fig=px.bar(counts,x="Classification",y="Records",title="Review-level distribution")
        fig.update_layout(template="plotly_white",height=410)
        st.plotly_chart(fig,use_container_width=True)
    st.subheader("Explainable screening factors")
    st.dataframe(df[["record_id","catchment_zone","sample_date","pathogen_marker_signal","marker_change_pct","local_health_trend_score","health_trend_change_pct","sampling_quality_score","signal_score","classification","explanation"]],use_container_width=True,hide_index=True)

with tab2:
    metric=st.selectbox("Trend metric",["pathogen_marker_signal","marker_change_pct","local_health_trend_score","health_trend_change_pct","signal_persistence_days"])
    fig=px.line(df.sort_values("sample_date"),x="sample_date",y=metric,color="catchment_zone",markers=True,title=metric.replace("_"," ").title())
    fig.update_layout(template="plotly_white",height=430)
    st.plotly_chart(fig,use_container_width=True)
    st.subheader("Marker vs aggregate health-trend context")
    fig=px.scatter(df,x="pathogen_marker_signal",y="local_health_trend_score",size="signal_persistence_days",color="classification",hover_name="catchment_zone",title="Wastewater marker and aggregate health-trend signals")
    fig.update_layout(template="plotly_white",height=430)
    st.plotly_chart(fig,use_container_width=True)
    st.caption("Association in this chart does not establish causation or disease transmission.")

with tab3:
    zone=st.selectbox("Catchment zone",sorted(df.catchment_zone.unique()))
    z=df[df.catchment_zone==zone]
    x,y,zcol=st.columns(3)
    x.metric("Records",len(z)); y.metric("Avg score",f"{z.signal_score.mean():.1f}"); zcol.metric("Latest score",f"{z.sort_values('sample_date').iloc[-1].signal_score:.1f}")
    st.dataframe(z.sort_values("sample_date",ascending=False)[["record_id","sample_date","pathogen_marker_signal","marker_change_pct","local_health_trend_score","sampling_quality_score","signal_score","classification","review_status"]],use_container_width=True,hide_index=True)

with tab4:
    st.subheader("Current local registry")
    st.dataframe(df,use_container_width=True,hide_index=True)
    st.download_button("Download scored registry CSV",df.to_csv(index=False).encode("utf-8"),"wastewater_disease_signal_scored_registry.csv","text/csv")
    st.download_button("Download current registry CSV",st.session_state.df.to_csv(index=False).encode("utf-8"),"wastewater_disease_signal_registry.csv","text/csv")

st.divider()
st.caption("WasteWatch Local • 100% local processing • No external APIs • Aggregate wastewater disease-signal decision support")
