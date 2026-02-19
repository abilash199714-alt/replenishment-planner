import streamlit as st
import pandas as pd

st.set_page_config(page_title="Products", layout="wide")

st.title("📦 Products (Master Data)")
st.caption("Upload and manage your SKU master list. This powers planning, ordering, and alerts.")

REQUIRED_COLS = ["sku"]
OPTIONAL_COLS = ["name", "category", "vendor", "unit_cost", "moq", "lead_time_days"]

def normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]
    return df

# Keep products in session
if "products" not in st.session_state:
    st.session_state["products"] = pd.DataFrame(columns=REQUIRED_COLS + OPTIONAL_COLS)

uploaded = st.file_uploader("Upload products CSV", type=["csv"])

c1, c2, c3 = st.columns([1, 1, 2])
with c1:
    st.download_button(
        "⬇️ Download template CSV",
        data=pd.DataFrame(columns=REQUIRED_COLS + OPTIONAL_COLS).to_csv(index=False).encode("utf-8"),
        file_name="products_template.csv",
        mime="text/csv",
    )

with c2:
    if st.button("🗑️ Clear products"):
        st.session_state["products"] = pd.DataFrame(columns=REQUIRED_COLS + OPTIONAL_COLS)
        st.success("Cleared.")

if uploaded is not None:
    df = pd.read_csv(uploaded)
    df = normalize_cols(df)

    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        st.error(f"Missing required columns: {missing}. Required: {REQUIRED_COLS}")
    else:
        # Keep only known columns (but allow extra)
        # Ensure required col type
        df["sku"] = df["sku"].astype(str).str.strip()

        # Merge/replace by sku
        current = st.session_state["products"]
        current = normalize_cols(current)

        merged = pd.concat([current, df], ignore_index=True)
        merged = merged.drop_duplicates(subset=["sku"], keep="last")

        # Order columns nicely
        cols = [c for c in (REQUIRED_COLS + OPTIONAL_COLS) if c in merged.columns]
        extra = [c for c in merged.columns if c not in cols]
        merged = merged[cols + extra].sort_values("sku")

        st.session_state["products"] = merged
        st.success(f"Loaded {len(df)} rows. Total products: {len(merged)}")

st.subheader("Product list")
prod = st.session_state["products"].copy()

# Filters
f1, f2, f3 = st.columns(3)
with f1:
    q = st.text_input("Search SKU / Name", "")
with f2:
    vendor = st.selectbox("Vendor", ["All"] + sorted([v for v in prod.get("vendor", pd.Series()).dropna().unique()]) )
with f3:
    category = st.selectbox("Category", ["All"] + sorted([v for v in prod.get("category", pd.Series()).dropna().unique()]) )

if q:
    mask = prod["sku"].str.contains(q, case=False, na=False)
    if "name" in prod.columns:
        mask = mask | prod["name"].astype(str).str.contains(q, case=False, na=False)
    prod = prod[mask]

if "vendor" in prod.columns and vendor != "All":
    prod = prod[prod["vendor"].astype(str) == vendor]

if "category" in prod.columns and category != "All":
    prod = prod[prod["category"].astype(str) == category]

edited = st.data_editor(
    prod,
    use_container_width=True,
    num_rows="dynamic",
    hide_index=True,
    key="products_editor",
)

# Save edits back
if st.button("💾 Save edits"):
    edited = normalize_cols(edited)
    edited["sku"] = edited["sku"].astype(str).str.strip()

    base = normalize_cols(st.session_state["products"])
    # Update/merge by sku
    merged = pd.concat([base, edited], ignore_index=True).drop_duplicates(subset=["sku"], keep="last")
    st.session_state["products"] = merged.sort_values("sku")
    st.success("Saved!")

st.download_button(
    "⬇️ Download products CSV",
    data=st.session_state["products"].to_csv(index=False).encode("utf-8"),
    file_name="products.csv",
    mime="text/csv",
)
