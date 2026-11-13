"""Advanced Service-Level Trade-Off Simulation: multi-product inventory strategy.

For products A, B and C (each with its own demand variability, lead time and holding cost),
simulate service levels from 80% to 99% and compute:
    Safety stock = Z x sigma x sqrt(Lead time)
    Holding cost = Safety stock x Holding cost per unit
then plot side-by-side subplots (blue = safety stock, green = holding cost) and quantify the
trade-offs. Runs as-is in Google Colab or with `python service_level_tradeoff.py`.
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import norm

# -----------------------------
# Product parameters (adjust as needed)
# sigma = std of daily demand (units), L = lead time (days), h = holding cost per unit,
# D = average daily demand (units, used for context), p = cost of a lost sale per unit
# -----------------------------
PRODUCTS = {
    "Product A": {"D": 400, "sigma": 65,  "L": 2, "h": 1.1, "p": 20.0},
    "Product B": {"D": 650, "sigma": 100, "L": 3, "h": 1.3, "p": 12.0},
    "Product C": {"D": 300, "sigma": 55,  "L": 4, "h": 1.8, "p": 45.0},
}
SERVICE_LEVELS = np.round(np.arange(0.80, 0.991, 0.01), 2)      # 80% ... 99%


def tradeoff_table(products=PRODUCTS, service_levels=SERVICE_LEVELS):
    """One row per product x service level: Z, safety stock, holding cost."""
    rows = []
    for name, p in products.items():
        for sl in service_levels:
            z = norm.ppf(sl)                                       # Z-score matched to the service level
            ss = z * p["sigma"] * np.sqrt(p["L"])                  # Safety stock = Z * sigma * sqrt(L)
            rows.append({"Product": name, "Service level": sl, "Z": z,
                         "Safety stock": ss, "Holding cost": ss * p["h"]})   # Holding cost = SS * h
    return pd.DataFrame(rows)


def marginal_costs(df):
    """Extra holding cost of each +1 point of service level: shows the non-linear climb."""
    out = df.copy()
    out["Marginal holding cost (+1 pt)"] = out.groupby("Product")["Holding cost"].diff()
    return out


def optimal_service_level(products=PRODUCTS):
    """Cost-balancing service level (critical ratio): CSL* = p / (p + h).
    Above it, the extra holding cost of more buffer outweighs the lost-sale cost it avoids."""
    rows = []
    for name, p in products.items():
        csl = p["p"] / (p["p"] + p["h"])
        csl_c = float(np.clip(csl, 0.80, 0.99))                    # keep within the simulated range
        z = norm.ppf(csl_c)
        ss = z * p["sigma"] * np.sqrt(p["L"])
        rows.append({"Product": name, "Critical ratio p/(p+h)": csl, "Recommended service level": csl_c,
                     "Safety stock": ss, "Holding cost": ss * p["h"],
                     "Buffer in days of demand": ss / p["D"]})
    return pd.DataFrame(rows)


def plot_tradeoffs(df, products=PRODUCTS, path=None):
    """Side-by-side subplots: X = service level, Y = units / cost; blue = safety stock, green = holding cost."""
    plt.rcParams.update({"figure.dpi": 120, "axes.grid": True, "grid.alpha": 0.3})
    fig, axes = plt.subplots(1, len(products), figsize=(15, 4.6), sharey=True)
    axes = np.atleast_1d(axes)
    fig.suptitle("Service Level Trade-offs in Inventory Optimization", fontsize=13, fontweight="bold")
    for ax, name in zip(axes, products):
        d = df[df["Product"] == name]
        p = products[name]
        ax.plot(d["Service level"], d["Safety stock"], color="blue", lw=2, marker="o", ms=3, label="Safety Stock")
        ax.plot(d["Service level"], d["Holding cost"], color="green", lw=2, marker="s", ms=3, label="Holding Cost")
        ax.set_title(f"{name}\nσ={p['sigma']}, L={p['L']} days, h={p['h']}", fontsize=10.5, fontweight="bold")
        ax.set_xlabel("Service Level")
        ax.set_xticks([0.80, 0.85, 0.90, 0.95, 0.99])
        ax.set_xticklabels(["80%", "85%", "90%", "95%", "99%"])
        ax.grid(True, linestyle="--", alpha=0.4)
        ax.legend(loc="upper left", fontsize=9, frameon=False)
    axes[0].set_ylabel("Units / Cost", fontweight="bold")
    plt.tight_layout(rect=[0, 0, 1, 0.92])
    if path:
        fig.savefig(path, bbox_inches="tight")
    return fig


def summary(df):
    """Key numbers per product: cost at 90/95/99%, cost of going from 95% to 99%."""
    piv = df.pivot_table(index="Product", columns="Service level", values=["Safety stock", "Holding cost"])
    rows = []
    for name in df["Product"].unique():
        ss90, ss95, ss99 = (piv.loc[name, ("Safety stock", s)] for s in (0.90, 0.95, 0.99))
        hc80, hc90, hc95, hc99 = (piv.loc[name, ("Holding cost", s)] for s in (0.80, 0.90, 0.95, 0.99))
        rows.append({"Product": name, "SS @90%": ss90, "SS @95%": ss95, "SS @99%": ss99,
                     "Holding cost @90%": hc90, "Holding cost @95%": hc95, "Holding cost @99%": hc99,
                     "95%→99% cost increase": (hc99 / hc95 - 1) * 100,
                     "Cost of 95→99% as share of 80→95%": (hc99 - hc95) / max(hc95 - hc80, 1e-9)})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = tradeoff_table()
    pd.set_option("display.width", 200)
    print("SAFETY STOCK AND HOLDING COST BY SERVICE LEVEL (selected levels)")
    print(df[df["Service level"].isin([0.80, 0.85, 0.90, 0.95, 0.99])].round(2).to_string(index=False))
    print("\nKEY TRADE-OFFS")
    print(summary(df).round(1).to_string(index=False))
    print("\nCOST-BALANCING SERVICE LEVEL (critical ratio)")
    print(optimal_service_level().round(3).to_string(index=False))
    plot_tradeoffs(df, path="service_level_tradeoffs.png")
    plt.show()
