# nutrition_tracker_app.py
# 改良版（単位対応・画面分離・編集削除対応・エラー修正版）

import streamlit as st
import pandas as pd
import os
from datetime import date

# =====================
# 初期設定
# =====================
FOOD_DB = "food_db.csv"
LOG_DB = "nutrition_log.csv"

UNITS = ["g", "mL", "個", "大さじ", "小さじ"]

# =====================
# CSV初期化
# =====================
def init_food_db():
    if not os.path.exists(FOOD_DB):
        df = pd.DataFrame(columns=[
            "name", "unit", "calories", "protein", "fat", "carbs"
        ])
        df.to_csv(FOOD_DB, index=False)


def init_log_db():
    if not os.path.exists(LOG_DB):
        df = pd.DataFrame(columns=[
            "date", "meal", "food", "amount", "unit",
            "calories", "protein", "fat", "carbs"
        ])
        df.to_csv(LOG_DB, index=False)


init_food_db()
init_log_db()

# =====================
# データ読み込み
# =====================
food_df = pd.read_csv(FOOD_DB)
log_df = pd.read_csv(LOG_DB)

# =====================
# セッション状態
# =====================
if "page" not in st.session_state:
    st.session_state.page = "main"

# =====================
# ナビゲーション
# =====================
st.title("🥗 栄養管理アプリ")
col1, col2 = st.columns(2)
with col1:
    if st.button("🏠 メイン画面"):
        st.session_state.page = "main"
with col2:
    if st.button("🗂 食品データベース管理"):
        st.session_state.page = "food"

# =====================
# 食品DB管理画面
# =====================
if st.session_state.page == "food":
    st.header("🗂 食品データベース管理")

    st.subheader("➕ 食品を追加")
    with st.form("add_food"):
        name = st.text_input("食品名")
        unit = st.selectbox("基準単位", UNITS)
        calories = st.number_input("カロリー", min_value=0.0)
        protein = st.number_input("たんぱく質", min_value=0.0)
        fat = st.number_input("脂質", min_value=0.0)
        carbs = st.number_input("炭水化物", min_value=0.0)
        submitted = st.form_submit_button("追加")

        if submitted and name:
            new = pd.DataFrame([[name, unit, calories, protein, fat, carbs]],
                               columns=food_df.columns)
            food_df = pd.concat([food_df, new], ignore_index=True)
            food_df.to_csv(FOOD_DB, index=False)
            st.success("食品を追加しました")

    st.subheader("✏️ 編集・削除")
    if not food_df.empty:
        target = st.selectbox("食品を選択", food_df["name"])
        row = food_df[food_df["name"] == target].iloc[0]

        new_unit = st.selectbox("単位", UNITS, index=UNITS.index(row.unit))
        new_cal = st.number_input("カロリー", value=float(row.calories))
        new_p = st.number_input("たんぱく質", value=float(row.protein))
        new_f = st.number_input("脂質", value=float(row.fat))
        new_c = st.number_input("炭水化物", value=float(row.carbs))

        colu, cold = st.columns(2)
        with colu:
            if st.button("更新"):
                food_df.loc[food_df.name == target, [
                    "unit", "calories", "protein", "fat", "carbs"
                ]] = [new_unit, new_cal, new_p, new_f, new_c]
                food_df.to_csv(FOOD_DB, index=False)
                st.success("更新しました")
        with cold:
            if st.button("削除"):
                food_df = food_df[food_df.name != target]
                food_df.to_csv(FOOD_DB, index=False)
                st.warning("削除しました")

    st.stop()

# =====================
# メイン画面
# =====================
st.header("🍽 食事入力")

meal = st.selectbox("食事区分", ["朝", "昼", "夜"])
food_name = st.selectbox("食品", food_df["name"] if not food_df.empty else [])

if food_name:
    food_row = food_df[food_df.name == food_name].iloc[0]
    st.write(f"単位: {food_row.unit}")
    amount = st.number_input("量", min_value=0.0)

    if st.button("追加"):
        factor = amount
        entry = {
            "date": str(date.today()),
            "meal": meal,
            "food": food_name,
            "amount": amount,
            "unit": food_row.unit,
            "calories": food_row.calories * factor,
            "protein": food_row.protein * factor,
            "fat": food_row.fat * factor,
            "carbs": food_row.carbs * factor
        }
        log_df = pd.concat([log_df, pd.DataFrame([entry])], ignore_index=True)
        log_df.to_csv(LOG_DB, index=False)
        st.success("追加しました")

# =====================
# 今日のまとめ
# =====================
st.header("📊 今日の合計")
today = str(date.today())
today_df = log_df[log_df.date == today]

if not today_df.empty:
    total = today_df[["calories", "protein", "fat", "carbs"]].sum()
    st.metric("カロリー", f"{total.calories:.1f} kcal")
    st.metric("P", f"{total.protein:.1f} g")
    st.metric("F", f"{total.fat:.1f} g")
    st.metric("C", f"{total.carbs:.1f} g")
else:
    st.info("まだ記録がありません")
