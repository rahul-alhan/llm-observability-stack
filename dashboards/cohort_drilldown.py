"""Streamlit dashboard for cohort drilldown + prompt-version A/B."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="LLM Observability", layout="wide")
st.title("LLM Observability — Cohort + A/B Explorer")

trace_path = Path("reports/traces.parquet")
if not trace_path.exists():
    st.warning("Run `python -m exporters.langfuse_export` first.")
    st.stop()

df = pd.read_parquet(trace_path)

st.sidebar.metric("Traces", f"{len(df):,}")
st.sidebar.metric("Unique users", df["user_id"].nunique())
versions = sorted(df["prompt_version"].dropna().unique())
selected = st.sidebar.multiselect("Prompt versions", versions, default=versions)
df = df[df["prompt_version"].isin(selected)]

st.subheader("Latency by prompt version")
fig = px.box(df, x="prompt_version", y="latency_ms", points="suspectedoutliers")
st.plotly_chart(fig, use_container_width=True)

st.subheader("Cost per request by prompt version")
cost = df.groupby("prompt_version").agg(
    n=("trace_id", "count"),
    avg_cost=("total_cost", "mean"),
    avg_tokens=("total_tokens", "mean"),
    p95_latency=("latency_ms", lambda s: s.quantile(0.95)),
).reset_index()
st.dataframe(cost, use_container_width=True)

st.subheader("User-cohort drilldown")
top_users = df.groupby("user_id").agg(
    n_traces=("trace_id", "count"),
    avg_cost=("total_cost", "mean"),
    p95_latency=("latency_ms", lambda s: s.quantile(0.95)),
).sort_values("n_traces", ascending=False).head(20)
st.dataframe(top_users, use_container_width=True)
