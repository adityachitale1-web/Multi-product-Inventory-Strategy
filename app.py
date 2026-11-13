"""Streamlit dashboard: Advanced Service-Level Trade-Off Simulation (multi-product inventory strategy).
Run:  streamlit run app.py"""
import matplotlib
matplotlib.use("Agg")
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from scipy.stats import norm

import service_level_tradeoff as T

st.set_page_config(page_title="Multi-Product Inventory Strategy", page_icon="📦", layout="wide")
st.title("📦 Multi-Product Inventory Strategy: Service-Level Trade-offs")
st.caption("How service level drives safety stock and holding cost for three products with different demand, "
           "variability, lead time and cost. Safety stock = Z·σ·√L · Holding cost = Safety stock × holding cost per unit.")

# ---------------- sidebar: inputs ----------------
with st.sidebar:
    st.header("Product inputs")
    base = pd.DataFrame(T.PRODUCTS).T.reset_index().rename(columns={"index": "Product"})
    base = base[["Product", "D", "sigma", "L", "h", "p"]]
    edited = st.data_editor(base, hide_index=True, disabled=["Product"], key="prod",
                            column_config={"D": st.column_config.NumberColumn("Avg demand/day", min_value=1),
                                           "sigma": st.column_config.NumberColumn("σ demand/day", min_value=0.1),
                                           "L": st.column_config.NumberColumn("Lead time (days)", min_value=0.5),
                                           "h": st.column_config.NumberColumn("Holding cost/unit", min_value=0.01, format="%.2f"),
                                           "p": st.column_config.NumberColumn("Lost-sale cost/unit", min_value=0.01, format="%.2f")})
    lo, hi = st.slider("Service-level range", 0.80, 0.99, (0.80, 0.99), 0.01, format="%.2f")
    pick = st.slider("Compare at service level", 0.80, 0.99, 0.95, 0.01, format="%.2f")
    st.caption("Edit any cell; every chart and table updates instantly.")

products = {r.Product: {"D": float(r.D), "sigma": float(r.sigma), "L": float(r.L), "h": float(r.h), "p": float(r.p)} for r in edited.itertuples()}
levels = np.round(np.arange(lo, hi + 0.0001, 0.01), 2)
df = T.tradeoff_table(products, levels)
full = T.tradeoff_table(products)                      # always 80-99% for the summary metrics
opt = T.optimal_service_level(products)

tab1, tab2, tab3, tab4 = st.tabs(["📈 Trade-off curves", "📊 Quantified impact", "🎯 Policy recommendation", "🔬 Variability & lead time"])

# ---------------- 1. the required chart ----------------
with tab1:
    st.pyplot(T.plot_tradeoffs(df, products))
    st.markdown("""
- **Non-linear climb:** Z rises faster as the service level approaches 100%, so each extra point of service needs more buffer than the last.
- **Holding cost scales with safety stock** by each product's cost per unit; Product C's high holding cost makes its green line climb fastest relative to its buffer.
- **Products differ** because σ·√L sets the scale: Product B (σ=100, L=3) needs the largest buffer at every service level.
""")
    with st.expander("Interactive version (hover for exact values)"):
        fig = go.Figure()
        for i, (name, d) in enumerate(df.groupby("Product")):
            fig.add_trace(go.Scatter(x=d["Service level"], y=d["Holding cost"], name=f"{name} holding cost", mode="lines+markers"))
            fig.add_trace(go.Scatter(x=d["Service level"], y=d["Safety stock"], name=f"{name} safety stock", mode="lines", line=dict(dash="dot")))
        fig.update_layout(height=430, xaxis_title="Service level", yaxis_title="Units / Cost", xaxis_tickformat=".0%", hovermode="x unified")
        st.plotly_chart(fig)

# ---------------- 2. quantify ----------------
with tab2:
    at = df[np.isclose(df["Service level"], pick)] if (df["Service level"] - pick).abs().min() < 1e-9 else T.tradeoff_table(products, [pick])
    c = st.columns(len(products))
    for col, (_, r) in zip(c, at.iterrows()):
        col.metric(f"{r['Product']} @ {pick:.0%}", f"{r['Safety stock']:,.0f} units", f"holding cost {r['Holding cost']:,.0f}", delta_color="off")
    st.subheader("Key trade-offs (80% – 99%)")
    sm = T.summary(full)
    st.dataframe(sm.style.format({c: "{:,.1f}" for c in sm.columns if c != "Product"}
                                 | {"95%→99% cost increase": "{:+.1f}%", "Cost of 95→99% as share of 80→95%": "{:.0%}"}), hide_index=True)
    st.caption("Going from 95% to 99% raises safety stock and holding cost by about 41% for every product. Those last 4 points "
               "cost roughly 80% as much as the previous 15 points (80% → 95%).")
    st.subheader("Marginal holding cost of each +1 point of service")
    mc = T.marginal_costs(full).pivot(index="Service level", columns="Product", values="Marginal holding cost (+1 pt)").dropna()
    mc.index = [f"{x:.0%}" for x in mc.index]
    st.bar_chart(mc)
    st.subheader("Full table")
    show = df.copy()
    show["Service level"] = show["Service level"].map("{:.0%}".format)
    st.dataframe(show.style.format({"Z": "{:.3f}", "Safety stock": "{:,.1f}", "Holding cost": "{:,.1f}"}), hide_index=True, height=320)
    st.download_button("⬇️ Download table (CSV)", df.round(3).to_csv(index=False), "service_level_tradeoffs.csv", "text/csv")

# ---------------- 3. recommendation ----------------
with tab3:
    st.markdown("Balancing **customer satisfaction** (lost sales) against **financial impact** (holding cost): the "
                "cost-minimising service level is the **critical ratio** p / (p + h), where p is the cost of a lost sale "
                "and h the holding cost per unit.")
    show = opt.copy()
    st.dataframe(show.style.format({"Critical ratio p/(p+h)": "{:.1%}", "Recommended service level": "{:.0%}", "Safety stock": "{:,.0f}",
                                     "Holding cost": "{:,.0f}", "Buffer in days of demand": "{:.2f}"}), hide_index=True)
    uniform = full[np.isclose(full["Service level"], 0.95)]["Holding cost"].sum()
    st.markdown(f"""
**Policy insight:** one blanket 95% target costs **{uniform:,.0f}** in holding cost; differentiated targets cost
**{opt['Holding cost'].sum():,.0f}** and put service where a stockout hurts most:
""" + "\n".join(f"- **{r['Product']}**: {r['Recommended service level']:.0%} (lost sale {products[r['Product']]['p']:.0f} vs holding {products[r['Product']]['h']:.2f} per unit)" for _, r in opt.iterrows()))
    st.caption("Recommendations are clipped to the simulated 80–99% range. Edit the lost-sale costs in the sidebar to test other margins.")

# ---------------- 4. variability & lead time ----------------
with tab4:
    who = st.selectbox("Product", list(products))
    p = products[who]
    z = norm.ppf(pick)
    sig = np.array([0.5, 0.75, 1.0, 1.25, 1.5]) * p["sigma"]
    Ls = np.array([1, 2, 3, 4, 5, 6, 8])
    grid = pd.DataFrame([[z * s * np.sqrt(L) for L in Ls] for s in sig], index=[f"σ = {s:,.0f}" for s in sig], columns=[f"L = {L} d" for L in Ls])
    st.markdown(f"**Safety stock for {who} at {pick:.0%} service** as demand variability (σ) and lead time (L) change")
    st.dataframe(grid.style.format("{:,.0f}").background_gradient(cmap="Greens"))
    st.markdown(f"""
- **Variability scales the buffer one-for-one:** +50% σ → +50% safety stock.
- **Lead time scales it by √L:** doubling lead time raises safety stock by only √2 ≈ +41%. Cutting {who}'s lead time from {p['L']:g} to
  {max(p['L'] - 1, 0.5):g} days saves {(1 - np.sqrt(max(p['L'] - 1, 0.5) / p['L'])) * 100:.0f}% of its buffer.
- Reducing σ (better forecasting) or L (faster suppliers) shifts the whole trade-off curve down, the alternative to accepting lower service.
""")
