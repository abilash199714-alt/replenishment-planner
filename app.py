import streamlit as st
import pandas as pd
import math

st.set_page_config(page_title="Replenishment Planner", layout="centered")
st.title("📦 Replenishment Planner (Small Business)")

def ses_forecast(series, alpha=0.3):
    # Simple Exponential Smoothing
    if len(series) == 0:
        return 0.0
    f = float(series.iloc[0])
    for actual in series.iloc[1:]:
        f = alpha * float(actual) + (1 - alpha) * f
    return f

uploaded_file = st.file_uploader("Upload demand CSV", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)

    required_cols = {"sku","date","demand_qty","on_hand","incoming","lead_time_days","moq"}
    missing = required_cols - set(df.columns)
    if missing:
        st.error(f"Missing columns: {sorted(missing)}")
        st.stop()

    df["date"] = pd.to_datetime(df["date"])
    df["demand_qty"] = pd.to_numeric(df["demand_qty"], errors="coerce").fillna(0.0)
    df["on_hand"] = pd.to_numeric(df["on_hand"], errors="coerce").fillna(0.0)
    df["incoming"] = pd.to_numeric(df["incoming"], errors="coerce").fillna(0.0)
    df["lead_time_days"] = pd.to_numeric(df["lead_time_days"], errors="coerce").fillna(0.0)
    df["moq"] = pd.to_numeric(df["moq"], errors="coerce").fillna(0.0)

    # Weekly buckets
    df["week"] = df["date"].dt.to_period("W").dt.start_time

    weekly = (
        df.groupby(["sku", "week"], as_index=False)
          .agg(
              demand_qty=("demand_qty", "sum"),
              on_hand=("on_hand", "last"),
              incoming=("incoming", "last"),
              lead_time_days=("lead_time_days", "last"),
              moq=("moq", "last"),
          )
          .sort_values(["sku","week"])
    )

    results = []

    for sku, g in weekly.groupby("sku", sort=False):
        g = g.sort_values("week")

        hist = g["demand_qty"].tail(8)
        avg_weekly = ses_forecast(hist, alpha=0.3)   # <-- improved forecast (SES)
        std_weekly = float(hist.std(ddof=1)) if len(hist) > 1 else 0.0

        on_hand = float(g["on_hand"].iloc[-1])
        incoming = float(g["incoming"].iloc[-1])
        lead_time_weeks = float(g["lead_time_days"].iloc[-1]) / 7.0
        moq = float(g["moq"].iloc[-1])

        demand_lt = avg_weekly * lead_time_weeks
        safety_stock = 1.65 * std_weekly * math.sqrt(lead_time_weeks) if lead_time_weeks > 0 else 0.0

        net_stock = on_hand + incoming
        order_qty = max(0.0, demand_lt + safety_stock - net_stock)

        if moq > 0 and order_qty > 0:
            order_qty = math.ceil(order_qty / moq) * moq

        days_of_cover = (net_stock / avg_weekly * 7.0) if avg_weekly > 0 else 999.0

        if days_of_cover < lead_time_weeks * 7.0:
            risk = "Stockout Risk"
        elif days_of_cover > 90:
            risk = "Excess Risk"
        else:
            risk = "OK"

        results.append({
            "SKU": sku,
            "Forecast (avg weekly)": round(avg_weekly, 2),
            "On Hand": round(on_hand, 2),
            "Incoming": round(incoming, 2),
            "Days of Cover": round(days_of_cover, 1),
            "Safety Stock": round(safety_stock, 2),
            "Recommended Order Qty": round(order_qty, 2),
            "Risk": risk,
        })

    out = pd.DataFrame(results).sort_values("Recommended Order Qty", ascending=False)

    st.subheader("📊 Recommendations")
    st.dataframe(out, use_container_width=True)

    csv = out.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download Recommendations", csv, "recommendations.csv", mime="text/csv")
else:
    st.info("Upload a CSV with columns: sku, date, demand_qty, on_hand, incoming, lead_time_days, moq")