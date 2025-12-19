import streamlit as st
import pandas as pd

# =============================
# データ読み込み（例）
# =============================
# food_df は「食品名が index」に入っている前提
# CSV例： index_col=0 に食品名

@st.cache_data

def load_food_data():
    return pd.read_csv("food.csv", index_col=0)

food_df = load_food_data()

# =============================
# セッション状態初期化
# =============================

if "food_count" not in st.session_state:
    # 食品名(index)をキー、回数を値にする
    st.session_state.food_count = pd.Series(dtype=int)

food_count = st.session_state.food_count

# =============================
# メイン画面
# =============================

st.title("食事管理アプリ")

# --- 食品選択 ---
food_names = food_df.index.astype(str).tolist()

target = st.selectbox("食品を選択", food_names)

# --- 追加ボタン ---
if st.button("追加"):
    if target in food_count.index:
        food_count[target] += 1
    else:
        food_count[target] = 1

    st.session_state.food_count = food_count

# =============================
# 摂取履歴表示
# =============================

st.subheader("摂取履歴")

if food_count.empty:
    st.write("まだ食品が追加されていません")
else:
    history_df = food_count.rename("count").to_frame()
    st.dataframe(history_df)

# =============================
# 未使用食品表示
# =============================

st.subheader("未使用の食品")

unused_foods = [
    f for f in food_names if f not in food_count.index
]

if unused_foods:
    st.write(unused_foods)
else:
    st.write("すべて使用済みです")

# =============================
# 栄養合計計算
# =============================

st.subheader("栄養合計")

if not food_count.empty:
    total = pd.Series(0, index=food_df.columns)

    for food, cnt in food_count.items():
        total += food_df.loc[food] * cnt

    st.dataframe(total.to_frame(name="total"))
else:
    st.write("栄養計算するデータがありません")
