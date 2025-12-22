# ============================
# 31.pyから変更、料理作成
# # ============================

import streamlit as st
import pandas as pd
import datetime
import matplotlib.pyplot as plt
import altair as alt
from supabase import create_client

supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)


# ============================
# ファイル定義
# ============================

UNITS = ["100g", "100mL", "枚", "本", "個", "大さじ", "小さじ"]

# ============================
# データ読み込み
# ============================
def load_log():
    res = supabase.table("nutrition_log").select("*").execute()
    df = pd.DataFrame(res.data)

    if df.empty:
        return pd.DataFrame(columns=[
            "date","meal","food","amount",
            "kcal","protein","fat","carbs"
        ])

    return df


def save_log(df, date_key):
    # 念のため NaN → None
    df = df.where(pd.notnull(df), None)

    # ① その日だけ削除
    supabase.table("nutrition_log") \
        .delete() \
        .eq("date", date_key) \
        .execute()

    # ② その日のデータだけ insert
    day_df = df[df["date"] == date_key]

    if not day_df.empty:
        supabase.table("nutrition_log") \
            .insert(day_df.to_dict("records")) \
            .execute()


def load_food_db():
    res = supabase.table("food_db").select("*").execute()
    df = pd.DataFrame(res.data)

    if df.empty:
        return pd.DataFrame(columns=[
            "food", "unit", "kcal", "protein", "fat", "carbs", "favorite"
        ])

    # unit補正
    df["unit"] = df["unit"].replace({
        "g": "100g",
        "ml": "100mL",
        "mL": "100mL"
    })

    # favorite補正
    if "favorite" not in df.columns:
        df["favorite"] = False
    else:
        df["favorite"] = df["favorite"].fillna(False)

    # 数値列をfloat化（NaN完全防御）
    NUM_COLS = ["kcal", "protein", "fat", "carbs", "unit_weight"]
    for col in NUM_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    return df



def amount_to_grams(food, amount, unit):
    if unit in ["g", "ml"]:
        return amount

    if unit in ["個", "枚"]:
        if pd.notna(food["unit_weight"]):
            return amount * food["unit_weight"]

    return None


def insert_food(records):
    for r in records:
        r.pop("id", None)  # ← ここ超重要
    supabase.table("food_db").insert(records).execute()


def update_food(row):
    food_id = row["id"]
    data = row.copy()
    data.pop("id")

    supabase.table("food_db") \
        .update(data) \
        .eq("id", food_id) \
        .execute()


def save_food_db(df):
    NUM_COLS = ["kcal", "protein", "fat", "carbs"]

    # 数値列を数値化
    for col in NUM_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # NaN → None（JSON対応）
    df = df.where(pd.notnull(df), None)

    # -----------------------------
    # 既存（idあり）
    # -----------------------------
    df_existing = df[df["id"].notna()]
    if not df_existing.empty:
        supabase.table("food_db").upsert(
            df_existing.to_dict("records"),
            on_conflict="id"
        ).execute()

    # -----------------------------
    # 新規（idなし）
    # -----------------------------
    df_new = df[df["id"].isna()].drop(columns=["id"])
    if not df_new.empty:
        supabase.table("food_db").insert(
            df_new.to_dict("records")
        ).execute()
        
        
def calc_total_nutrition(ingredients):
    total = {k: 0.0 for k in ["kcal", "protein", "fat", "carbs"]}

    for food, amount, unit in ingredients:
        grams = amount_to_grams(food, amount, unit)
        if grams is None:
            continue

        ratio = grams / 100.0

        for k in total:
            if pd.notna(food[k]):
                total[k] += float(food[k]) * ratio

    return total



def load_settings():
    res = supabase.table("settings").select("*").eq("id", 1).execute()

    if res.data:
        return res.data[0]["data"]
    else:
        # 初期設定を作成
        default = {}
        supabase.table("settings").insert({
            "id": 1,
            "data": default
        }).execute()
        return default


def save_settings(settings):
    supabase.table("settings").upsert({
        "id":1,
        "data":settings
    }).execute()

        
def ensure_day_state(date_key):
    if "foods_added" not in st.session_state:
        st.session_state.foods_added = {}

    if "meals" not in st.session_state:
        st.session_state.meals = {}

    if date_key not in st.session_state.foods_added:
        st.session_state.foods_added[date_key] = {
            "朝": [],
            "昼": [],
            "夜": []
        }

    if date_key not in st.session_state.meals:
        st.session_state.meals[date_key] = {
            "朝": {"kcal": 0, "protein": 0, "fat": 0, "carbs": 0},
            "昼": {"kcal": 0, "protein": 0, "fat": 0, "carbs": 0},
            "夜": {"kcal": 0, "protein": 0, "fat": 0, "carbs": 0},
        }


def load_day_from_csv(date_key, data):
    ensure_day_state(date_key)

    day_df = data[data["date"] == date_key]
    if day_df.empty:
        return

    # 初期化（上書き）
    st.session_state.foods_added[date_key] = {
        "朝": [], "昼": [], "夜": []
    }
    st.session_state.meals[date_key] = {
        m: {"kcal": 0, "protein": 0, "fat": 0, "carbs": 0}
        for m in ["朝", "昼", "夜"]
    }

    for _, row in day_df.iterrows():
        meal = row["meal"]

        food_entry = {
            "food": row["food"],
            "amount": row["amount"],
            "unit": "",
            "kcal": row["kcal"],
            "protein": row["protein"],
            "fat": row["fat"],
            "carbs": row["carbs"],
        }

        st.session_state.foods_added[date_key][meal].append(food_entry)

        for k in ["kcal", "protein", "fat", "carbs"]:
            st.session_state.meals[date_key][meal][k] += row[k]

# ============================
# 設定用 state 初期化
# ============================
if "log_dirty" not in st.session_state:
    st.session_state.log_dirty = False


if "initialized" not in st.session_state:
    saved = load_settings()

    st.session_state.theme = saved.get("theme", "dark")

    st.session_state.profile = saved.get(
        "profile",
        {"height": 170, "weight": 60.0, "goal": "維持"}
    )

    st.session_state.targets = saved.get(
        "targets",
        {"kcal": 2000, "protein": 100, "fat": 60, "carbs": 250}
    )

    st.session_state.initialized = True

# ============================
# 背景色設定
# ============================

def apply_theme(theme):
    if theme == "light":
        st.markdown("""
        <style>
        /* ===============================
           全体背景
        =============================== */
        body,
        [data-testid="stAppViewContainer"],
        .stApp {
            background-color: #ffffff !important;
            color: #000000 !important;
        }

        /* ===============================
           テキスト
        =============================== */
        .stMarkdown, .stText, label {
            color: #000000 !important;
        }

        /* ===============================
           number_input / text_input のみ
        =============================== */
        input[type="number"],
        input[type="text"],
        textarea {
            background-color: #ffffff !important;
            color: #000000 !important;
            border: 1px solid #cccccc !important;
        }

        /* ===============================
           selectbox / radio（触らない）
        =============================== */
        div[data-baseweb="select"] {
            background-color: transparent !important;
        }

        /* ===============================
           ボタン
        =============================== */
        .stButton button {
            background-color: #f0f2f6 !important;
            color: #000000 !important;
            border: 1px solid #cccccc !important;
        }

        /* ===============================
           DataFrame（ここが重要）
        =============================== */
        [data-testid="stDataFrame"] {
            border: 1px solid #cccccc !important;
        }

        [data-testid="stDataFrame"] table {
            border-collapse: collapse !important;
        }

        [data-testid="stDataFrame"] th,
        [data-testid="stDataFrame"] td {
            border: 1px solid #cccccc !important;
            color: #000000 !important;
        }
        
        /* ===============================
        HTML table（to_html 用）
        =============================== */
        table {
            border-collapse: collapse !important;
            width: 100%;
            background-color: #ffffff !important;
        }

        table th,
        table td {
            border: 1px solid #cccccc !important;
            padding: 6px 10px;
            color: #000000 !important;
            text-align: right;
        }

        table th {
            background-color: #f0f2f6 !important;
            font-weight: bold;
        }
        
        /* ===============================
        radio（ライトテーマ文字色完全上書き）
        =============================== */

        /* radio 全体 */
        div[data-baseweb="radio"] {
            color: #000000 !important;
        }

        /* radio の選択肢テキスト */
        div[data-baseweb="radio"] span {
            color: #000000 !important;
        }

        /* radio の label */
        div[data-baseweb="radio"] label {
            color: #000000 !important;
        }

        /* 念のため p 要素も */
        div[data-baseweb="radio"] p {
            color: #000000 !important;
        }

        </style>
        """, unsafe_allow_html=True)

    else:
        st.markdown("""
        <style>
        body,
        [data-testid="stAppViewContainer"],
        .stApp {
            background-color: #0e1117 !important;
            color: #fafafa !important;
        }

        .stMarkdown, .stText, label {
            color: #fafafa !important;
        }

        input[type="number"],
        input[type="text"],
        textarea {
            background-color: #262730 !important;
            color: #fafafa !important;
            border: 1px solid #444 !important;
        }

        .stButton button {
            background-color: #31333f !important;
            color: #fafafa !important;
            border: 1px solid #555 !important;
        }

        [data-testid="stDataFrame"] {
            border: 1px solid #555 !important;
        }

        [data-testid="stDataFrame"] th,
        [data-testid="stDataFrame"] td {
            border: 1px solid #555 !important;
            color: #fafafa !important;
        }
        
        div[role="radiogroup"] label {
            color: #fafafa !important;
        }

        div[role="radiogroup"] span {
            color: #fafafa !important;
        }

        </style>
        """, unsafe_allow_html=True)

apply_theme(st.session_state.get("theme", "light"))

# ============================
# UI
# ============================
st.title("PFC・カロリー自動計算アプリ")

if "page" not in st.session_state:
    st.session_state.page = "main"

col1, col2, col3, col4, col5, col6, col7 = st.columns(7)

if col1.button("メイン"):
    st.session_state.page = "main"
if col2.button("食品DB"):
    st.session_state.page = "food"
if col3.button("料理作成"):
    st.session_state.page = "recipe"
if col4.button("週間"):
    st.session_state.page = "weekly"
if col5.button("月間"):
    st.session_state.page = "monthly"
if col6.button("履歴"):
    st.session_state.page = "history"
if col7.button("設定"):
    st.session_state.page = "settings"

data = load_log()
food_db = load_food_db()

# ============================
# 目標設定
# ============================
def calc_target_calories(height, weight, goal):
    bmr = 10 * weight + 6.25 * height - 5 * 25 + 5
    tdee = bmr * 1.5

    if goal == "減量":
        return round(tdee - 500)
    elif goal == "ダイエット":
        return round(tdee - 300)
    elif goal == "筋肥大":
        return round(tdee + 400)
    else:
        return round(tdee)


def calc_pfc_targets(weight, kcal, goal):
    protein_g = weight * (2.0 if goal == "筋肥大" else 1.5)
    protein_kcal = protein_g * 4

    fat_kcal = kcal * 0.25
    fat_g = fat_kcal / 9

    carbs_kcal = kcal - protein_kcal - fat_kcal
    carbs_g = carbs_kcal / 4

    return {
    "kcal": int(round(kcal)),
    "protein": int(round(protein_g)),
    "fat": int(round(fat_g)),
    "carbs": int(round(carbs_g)),
    }



# ============================
# 設定ページ
# ============================
if st.session_state.page == "settings":
    st.header("設定")

    # =========================
    # 表示設定
    # =========================
    # 設定ページ
    st.subheader("表示設定")

    theme = st.radio(
        "テーマ",
        ["ライト（白）", "ダーク（黒）"],
        index=0 if st.session_state.get("theme", "light") == "light" else 1
    )

    st.session_state.theme = "light" if theme == "ライト（白）" else "dark"

    save_settings({
        "theme": st.session_state.theme,
        "profile": st.session_state.profile,
        "targets": st.session_state.targets
    })

    # =========================
    # 身体情報
    # =========================
    st.subheader("身体情報")

    p = st.session_state.profile

    p["height"] = st.number_input(
        "身長 (cm)",
        min_value=140.0,
        max_value=200.0,
        value=float(p["height"]),
        step=1.0
    )

    p["weight"] = st.number_input(
        "体重 (kg)",
        min_value=30.0,
        max_value=150.0,
        value=float(p["weight"]),
        step=0.1
    )

    p["goal"] = st.selectbox(
        "目的",
        ["減量", "ダイエット", "維持", "筋肥大"],
        index=["減量", "ダイエット", "維持", "筋肥大"].index(p["goal"])
    )

    st.divider()

    # =========================
    # 目標（自動計算）
    # =========================
    st.subheader("おすすめ目標（自動計算）")

    auto_kcal = calc_target_calories(
        p["height"], p["weight"], p["goal"]
    )
    auto_targets = calc_pfc_targets(
        p["weight"], auto_kcal, p["goal"]
    )

    auto_df = pd.DataFrame([{
    "kcal": auto_targets["kcal"],
    "たんぱく質(g)": auto_targets["protein"],
    "脂質(g)": auto_targets["fat"],
    "炭水化物(g)": auto_targets["carbs"],
    }])

    st.table(auto_df)


    if st.button("この目標を採用"):
        st.session_state.targets = auto_targets
        st.success("目標を更新しました")

    st.divider()

    # =========================
    # 手動目標設定（既存）
    # =========================
    st.subheader("目標を手動で調整")

    t = st.session_state.targets

    t["kcal"] = st.number_input(
    "目標カロリー",
    min_value=0,
    step=10,
    value=int(t["kcal"])
    )

    t["protein"] = st.number_input(
        "目標たんぱく質 (g)",
        min_value=0,
        step=5,
        value=int(t["protein"])
    )

    t["fat"] = st.number_input(
        "目標脂質 (g)",
        min_value=0,
        step=5,
        value=int(t["fat"])
    )

    t["carbs"] = st.number_input(
        "目標炭水化物 (g)",
        min_value=0,
        step=10,
        value=int(t["carbs"])
    )

    save_settings({"theme": st.session_state.theme, "profile": st.session_state.profile, "targets": st.session_state.targets})
    st.success("自動保存されます")
    st.stop()


# ============================
# 週間レポート
# ============================
NUTRIENTS = {
    "kcal": "カロリー",
    "protein": "たんぱく質",
    "fat": "脂質",
    "carbs": "炭水化物",
}

if st.session_state.page == "weekly":
    st.header("週間レポート")

    if data.empty:
        st.info("データがありません")
        st.stop()

    data["date"] = pd.to_datetime(data["date"])
    today = datetime.date.today()
    week_ago = today - datetime.timedelta(days=6)

    week_data = data[data["date"] >= pd.to_datetime(week_ago)]
    daily = week_data.groupby("date").sum(numeric_only=True)

    st.subheader("合計")
    st.write(daily.sum())

    st.subheader("平均")
    st.write(daily.mean())

    st.subheader("推移グラフ")

    # =========================
    # 表示項目チェックボックス
    # =========================
    cols = st.columns(4)
    selected = []

    for col, k in zip(cols, NUTRIENTS):
        if col.checkbox(
            NUTRIENTS[k],
            value=True,
            key=f"weekly_chk_{k}"
        ):
            selected.append(k)

    # =========================
    # 目標線 ON/OFF
    # =========================
    show_target = st.checkbox(
        "目標線を表示",
        value=True,
        key="weekly_target"
    )

    if not selected:
        st.info("表示する項目を1つ以上選択してください")
    else:
        chart_df = daily[selected].copy()

        if show_target:
            for k in selected:
                chart_df[f"{k}_target"] = st.session_state.targets[k]

        st.line_chart(chart_df)

        
    st.stop()

# ============================
# 月間レポート
# ============================
if st.session_state.page == "monthly":
    st.header("月間レポート")

    if data.empty:
        st.info("データがありません")
        st.stop()

    data["date"] = pd.to_datetime(data["date"])
    start = datetime.date.today().replace(day=1)
    month_data = data[data["date"] >= pd.to_datetime(start)]
    daily = month_data.groupby("date").sum(numeric_only=True)

    st.subheader("合計")
    st.write(daily.sum())

    st.subheader("平均")
    st.write(daily.mean())

    st.subheader("推移グラフ")

    cols = st.columns(4)
    selected = []

    for col, k in zip(cols, NUTRIENTS):
        if col.checkbox(
            NUTRIENTS[k],
            value=True,
            key=f"monthly_chk_{k}"
        ):
            selected.append(k)

    show_target = st.checkbox(
        "目標線を表示",
        value=True,
        key="monthly_target"
    )

    if not selected:
        st.info("表示する項目を1つ以上選択してください")
    else:
        chart_df = daily[selected].copy()

        if show_target:
            for k in selected:
                chart_df[f"{k}_target"] = st.session_state.targets[k]

        st.line_chart(chart_df)

    st.stop()

# ============================
# 食品DB管理
# ============================
if st.session_state.page == "food":
    st.header("食品データベース管理")
    
    required_cols = ["food","unit","kcal","protein","fat","carbs","favorite"]
    for c in required_cols:
        if c not in food_db.columns:
            food_db[c] = False if c == "favorite" else 0


    # --- 新規登録 ---
    st.subheader("食品登録")
    new_food = st.text_input("食品名")
    new_unit = st.selectbox("単位", UNITS, key="new_unit_select")
    per_label = f"{new_unit}あたり" if new_unit in ["100g", "100mL"] else f"1{new_unit}あたり"


    f_k = st.number_input(f"{per_label}のカロリー", min_value=0.0)
    f_p = st.number_input(f"{per_label}のたんぱく質", min_value=0.0)
    f_f = st.number_input(f"{per_label}の脂質", min_value=0.0)
    f_c = st.number_input(f"{per_label}の炭水化物", min_value=0.0)


    if st.button("食品を追加") and new_food:
        row = pd.DataFrame([{
            "food": new_food,
            "unit": new_unit,
            "kcal": f_k,
            "protein": f_p,
            "fat": f_f,
            "carbs": f_c,
            "favorite": False
        }])

        food_db = pd.concat([food_db, row], ignore_index=True)
        save_food_db(food_db)
        st.success("追加しました")
        st.rerun()


    st.divider()

    # --- 編集・削除（検索付き） ---
    # --- 食品DB一覧 ---

    st.subheader("食品DB")

    # favorite列が無ければ追加
    if "favorite" not in food_db.columns:
        food_db["favorite"] = False
        save_food_db(food_db)

    with st.expander("食品DB一覧（検索・編集・削除）", expanded=False):

        if food_db.empty:
            st.info("食品が登録されていません")
        else:

            # =========================
            # 検索
            # =========================
            keyword = st.text_input("食品名で検索", key="food_search")

            view_df = food_db.copy()

            if keyword:
                view_df = view_df[view_df["food"].str.contains(keyword, case=False)]

            # =========================
            # お気に入りを上に
            # =========================
            view_df = view_df.sort_values("favorite", ascending=False)

            if view_df.empty:
                st.info("該当する食品がありません")
            else:
                # =========================
                # 一覧表示
                # =========================
                for idx, row in view_df.iterrows():

                    with st.container():
                        cols = st.columns([3, 2, 2, 2, 2, 2, 1, 1, 1])

                        # --- 表示用基準量 ---
                        base_label = (
                            f"{row['unit']}あたり"
                            if row["unit"] in ["100g", "100mL"]
                            else f"1{row['unit']}あたり"
                        )

                        cols[0].markdown(f"**{row['food']}**")
                        cols[1].write(base_label)
                        cols[2].write(f"{row['kcal']} kcal")
                        cols[3].write(f"P {row['protein']} g")
                        cols[4].write(f"F {row['fat']} g")
                        cols[5].write(f"C {row['carbs']} g")

                        # お気に入り
                        fav_label = "★" if row["favorite"] else "☆"
                        if cols[6].button(fav_label, key=f"fav_{idx}"):
                            food_db.loc[idx, "favorite"] = not row["favorite"]
                            save_food_db(food_db)
                            st.rerun()

                        # ✏ 編集
                        edit = cols[7].button("✏", key=f"edit_{idx}")

                        # 🗑 削除
                        delete = cols[8].button("🗑", key=f"del_{idx}")

                        # =========================
                        # 削除
                        # =========================
                        if delete:
                            food_db = food_db.drop(idx).reset_index(drop=True)
                            save_food_db(food_db)

                            st.rerun()

                        # =========================
                        # 編集
                        # =========================
                        if edit:
                            st.session_state.edit_index = idx

                # =========================
                # 編集フォーム
                # =========================
                if "edit_index" in st.session_state:
                    i = st.session_state.edit_index
                    row = food_db.loc[i]

                    st.divider()
                    st.markdown("### 食品を編集")

                    e_food = st.text_input("食品名", row["food"], key="e_food")

                    unit_index = UNITS.index(row["unit"]) if row["unit"] in UNITS else 0
                    e_unit = st.selectbox("単位", UNITS, index=unit_index, key="e_unit")

                    # ★ 編集用の per_label をここで作る（重要）
                    edit_per_label = (
                        f"{e_unit}あたり"
                        if e_unit in ["100g", "100mL"]
                        else f"1{e_unit}あたり"
                    )

                    e_kcal = st.number_input(
                        f"{edit_per_label}のカロリー",
                        value=float(row["kcal"]),
                        key="e_kcal"
                    )
                    e_p = st.number_input(
                        f"{edit_per_label}のたんぱく質",
                        value=float(row["protein"]),
                        key="e_p"
                    )
                    e_f = st.number_input(
                        f"{edit_per_label}の脂質",
                        value=float(row["fat"]),
                        key="e_f"
                    )
                    e_c = st.number_input(
                        f"{edit_per_label}の炭水化物",
                        value=float(row["carbs"]),
                        key="e_c"
                    )

                    col1, col2 = st.columns([1, 1], gap="small")

                    if col1.button("保存"):
                        food_db.loc[i] = {
                            "id": row["id"],  # ★★★ これが超重要
                            "food": e_food,
                            "unit": e_unit,
                            "kcal": e_kcal,
                            "protein": e_p,
                            "fat": e_f,
                            "carbs": e_c,
                            "favorite": row["favorite"]
                        }

                        save_food_db(food_db)
                        del st.session_state.edit_index
                        st.rerun()

                    if col2.button("キャンセル"):
                        del st.session_state.edit_index
                        st.rerun()
    st.stop()
    
    
# ============================
# 料理作成
# ============================
if st.session_state.page == "recipe":

    st.subheader("料理を作成")

    dish_name = st.text_input("料理名")

    st.caption("使う材料と量を選んでください")
    ingredient_rows = []

    for i, row in food_db.iterrows():
        with st.container():
            cols = st.columns([3, 2, 2])
            use = cols[0].checkbox(row["food"], key=f"use_{row['id']}")
            amount = cols[1].number_input(
                "量",
                min_value=0.0,
                step=1.0,
                key=f"amt_{row['id']}"
            )
            unit = cols[2].selectbox(
                "単位",
                ["g", "ml", "個", "枚"],
                key=f"unit_{row['id']}"
            )

    if use and amount > 0:
        ingredient_rows.append((row, amount, unit))

        if ingredient_rows and dish_name:
            totals = calc_total_nutrition(ingredient_rows)

            st.markdown("###栄養合計")
            st.write(f"カロリー: {totals['kcal']:.1f} kcal")
            st.write(f"たんぱく質: {totals['protein']:.1f} g")
            st.write(f"脂質: {totals['fat']:.1f} g")
            st.write(f"炭水化物: {totals['carbs']:.1f} g")
            
        if st.button("この料理を食品DBに登録"):
            # ① 料理を保存
            result = supabase.table("food_db").insert({
                "name": dish_name,
                "unit": "1人前",
                **totals,
                "favorite": False
            }).execute()

            dish_id = result.data[0]["id"]

            # ② 材料内訳を保存
            recipe_records = []
            for food, amount, unit in ingredient_rows:
                recipe_records.append({
                    "dish_id": dish_id,
                    "ingredient_id": food["id"],
                    "amount": amount,
                    "unit": unit,
                })

            supabase.table("recipe_items").insert(recipe_records).execute()

            st.success("料理＋材料内訳を保存しました")
            st.rerun()


    st.stop()
    

# ============================
# 履歴閲覧
# ============================
if st.session_state.page == "history":
    st.header("履歴閲覧")
    if data.empty:
        st.info("記録なし")
        st.stop()

    data["date"] = pd.to_datetime(data["date"])
    d = st.date_input("日付", data["date"].max().date())
    day = data[data["date"] == pd.to_datetime(d)]

    if day.empty:
        st.info("この日の記録なし")
    else:
        st.dataframe(day)
        st.write(day[["kcal", "protein", "fat", "carbs"]].sum())
    st.stop()

# ============================
# メイン画面
# ============================
st.header("食事入力")
selected_date = st.date_input("記録日", datetime.date.today())
date_key = selected_date.isoformat()

ensure_day_state(date_key)

if st.session_state.get("loaded_date") != date_key:
    load_day_from_csv(date_key, data)
    st.session_state.loaded_date = date_key


filtered = food_db.copy()

if not filtered.empty:
    food = st.selectbox("食品", filtered["food"])
    row = filtered[filtered["food"] == food].iloc[0]

    disp_unit = "g" if row["unit"] == "100g" else "mL" if row["unit"] == "100mL" else row["unit"]
    amount = st.number_input(f"量（{disp_unit}）", min_value=0.0)
    meal = st.selectbox("食事区分", ["朝", "昼", "夜"])

    factor = amount / 100 if row["unit"] in ["100g", "100mL"] else amount
    calc = {
        k: float(row[k]) * factor
        for k in ["kcal", "protein", "fat", "carbs"]
    }

    if st.button("追加"):
        st.session_state.foods_added[date_key][meal].append(
            {"food": food, "amount": amount, "unit": disp_unit, **calc}
        )
        for k in calc:
            st.session_state.meals[date_key][meal][k] += calc[k]

        st.session_state.log_dirty = True

# ============================
# 当日の記録表示・削除
# ============================

st.subheader("当日の記録")

if "foods_added" not in st.session_state:
    st.session_state.foods_added = {}

if date_key not in st.session_state.foods_added:
    st.session_state.foods_added[date_key] = {
        "朝": [],
        "昼": [],
        "夜": []
    }

for meal in ["朝", "昼", "夜"]:
    if meal not in st.session_state.foods_added[date_key]:
        st.session_state.foods_added[date_key][meal] = []

tabs = st.tabs(["全体","朝", "昼", "夜"])

with tabs[0]:
    st.subheader("全て")

    for meal in ["朝", "昼", "夜"]:
        st.markdown(f"### {meal}")

        for i, f in enumerate(st.session_state.foods_added[date_key][meal]):
            c1, c2 = st.columns([4, 1])
            c1.write(f"{f['food']} {f['amount']}{f['unit']} ({f['kcal']:.1f}kcal)")
            if c2.button("削除", key=f"all_{meal}_{i}"):
                for k in ["kcal", "protein", "fat", "carbs"]:
                    st.session_state.meals[date_key][meal][k] -= f[k]
                st.session_state.foods_added[date_key][meal].pop(i)
                st.session_state.log_dirty = True
                st.rerun()

        # --- 小計 ---
        m = st.session_state.meals[date_key][meal]
        meal_df = pd.DataFrame(
            [[
                round(m["kcal"], 1),
                round(m["protein"], 1),
                round(m["fat"], 1),
                round(m["carbs"], 1),
            ]],
            columns=["kcal", "たんぱく質(g)", "脂質(g)", "炭水化物(g)"]
        )

        st.markdown(meal_df.to_html(index=False), unsafe_allow_html=True)


for tab, meal in zip(tabs[1:], ["朝", "昼", "夜"]):
    with tab:
        st.subheader(meal)

        for i, f in enumerate(st.session_state.foods_added[date_key][meal]):
            c1, c2 = st.columns([4, 1])
            c1.write(f"{f['food']} {f['amount']}{f['unit']} ({f['kcal']:.1f}kcal)")
            if c2.button("削除", key=f"{meal}_{i}"):
                for k in ["kcal", "protein", "fat", "carbs"]:
                    st.session_state.meals[date_key][meal][k] -= f[k]
                st.session_state.foods_added[date_key][meal].pop(i)
                st.session_state.log_dirty = True
                st.rerun()

        m = st.session_state.meals[date_key][meal]
        meal_df = pd.DataFrame(
            [[
                round(m["kcal"], 1),
                round(m["protein"], 1),
                round(m["fat"], 1),
                round(m["carbs"], 1),
            ]],
            columns=["kcal", "たんぱく質(g)", "脂質(g)", "炭水化物(g)"]
        )

        st.markdown(meal_df.to_html(index=False), unsafe_allow_html=True)


# =========================
# ★ ここから合計（forの外）
# =========================

total = {"kcal": 0, "protein": 0, "fat": 0, "carbs": 0}

for meal in ["朝", "昼", "夜"]:
    for k in total:
        total[k] += st.session_state.meals[date_key][meal][k]

col1, col2 = st.columns([2, 1])

total_df = pd.DataFrame(
    [[
        round(total["kcal"], 1),
        round(total["protein"], 1),
        round(total["fat"], 1),
        round(total["carbs"], 1),
    ]],
    columns=["kcal", "たんぱく質(g)", "脂質(g)", "炭水化物(g)"]
)
with col1:
    st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)

    st.subheader("当日の合計")

    st.markdown(
        total_df.to_html(index=False),
        unsafe_allow_html=True
    )



# 円グラフ

with col2:
    st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)

    st.markdown("### PFCバランス（kcal換算）")
    
    p_kcal = total["protein"] * 4
    f_kcal = total["fat"] * 9
    c_kcal = total["carbs"] * 4

    # NaN & 0対策
    if pd.isna(p_kcal): p_kcal = 0.0
    if pd.isna(f_kcal): f_kcal = 0.0
    if pd.isna(c_kcal): c_kcal = 0.0

    if p_kcal + f_kcal + c_kcal == 0:
        st.info("データなし")
    else:
        labels = [
            f"P {p_kcal:.0f}kcal",
            f"F {f_kcal:.0f}kcal",
            f"C {c_kcal:.0f}kcal"
            ]
        fig, ax = plt.subplots()
        ax.pie(
            [p_kcal, f_kcal, c_kcal],
            labels=["Protein", "Fat", "Carbs"],
            autopct="%.1f%%",
            startangle=90
        )
        ax.axis("equal")
        st.pyplot(fig)



# =========================
# 目標棒グラフ
# =========================
st.subheader("摂取量と目標")

t = st.session_state.targets

# =========================
# 元データ
# =========================
df = pd.DataFrame({
    "項目": ["kcal", "Protein", "Fat", "Carbs"],
    "摂取量": [
        total["kcal"],
        total["protein"],
        total["fat"],
        total["carbs"],
    ],
    "目標": [
        t["kcal"],
        t["protein"],
        t["fat"],
        t["carbs"],
    ],
    "軸": ["kcal", "PFC", "PFC", "PFC"]
})

# =========================
# 目標内 / 超過に分解
# =========================
df["within"] = df[["摂取量", "目標"]].min(axis=1)
df["excess"] = (df["摂取量"] - df["目標"]).clip(lower=0)

stack_df = df.melt(
    id_vars=["項目", "目標", "軸"],
    value_vars=["within", "excess"],
    var_name="区分",
    value_name="量"
)

# ★ stack順序を完全に固定（これが最重要）
stack_df["order"] = stack_df["区分"].map({
    "within": 0,  # 下
    "excess": 1   # 上
})

color_scale = alt.Scale(
    domain=["within", "excess"],
    range=["#3498db", "#e74c3c"]
)

# =========================
# kcal（左）
# =========================
kcal_bar = (
    alt.Chart(stack_df[stack_df["軸"] == "kcal"])
    .mark_bar()
    .encode(
        x=alt.X("項目:N", sort=["kcal"], title=None),
        y=alt.Y(
            "量:Q",
            title="kcal",
            stack="zero",
            scale=alt.Scale(zero=True)
        ),
        color=alt.Color("区分:N", scale=color_scale, legend=None),
        order=alt.Order("order:Q")
    )
)

kcal_target = (
    alt.Chart(df[df["軸"] == "kcal"])
    .mark_rule(strokeDash=[4, 4], color="gray")
    .encode(
        x="項目:N",
        y="目標:Q"
    )
)

kcal_text = (
    alt.Chart(df[df["軸"] == "kcal"])
    .mark_text(dy=-6)
    .encode(
        x="項目:N",
        y="摂取量:Q",
        text=alt.Text("摂取量:Q", format=".0f")
    )
)

kcal_chart = (
    (kcal_bar + kcal_target + kcal_text)
    .properties(width=120)
)

# =========================
# PFC（右）
# =========================
pfc_bar = (
    alt.Chart(stack_df[stack_df["軸"] == "PFC"])
    .mark_bar()
    .encode(
        x=alt.X(
            "項目:N",
            sort=["Protein", "Fat", "Carbs"],
            title=None
        ),
        y=alt.Y(
            "量:Q",
            title="PFC (g)",
            stack="zero",
            scale=alt.Scale(zero=True)
        ),
        color=alt.Color("区分:N", scale=color_scale, legend=None),
        order=alt.Order("order:Q")
    )
)

pfc_target = (
    alt.Chart(df[df["軸"] == "PFC"])
    .mark_rule(strokeDash=[4, 4], color="gray")
    .encode(
        x="項目:N",
        y="目標:Q"
    )
)

pfc_text = (
    alt.Chart(df[df["軸"] == "PFC"])
    .mark_text(dy=-6)
    .encode(
        x="項目:N",
        y="摂取量:Q",
        text=alt.Text("摂取量:Q", format=".1f")
    )
)

pfc_chart = (
    (pfc_bar + pfc_target + pfc_text)
    .properties(width=300)
)

# =========================
# 横連結（kcal 左 / PFC 右）
# =========================
chart = alt.hconcat(kcal_chart, pfc_chart)

st.altair_chart(chart, use_container_width=True)

# ============================
# 自動保存
# ============================
if st.session_state.get("log_dirty"):
    rows = []
    for meal, foods in st.session_state.foods_added[date_key].items():
        for f in foods:
            rows.append({
                "date": date_key,
                "meal": meal,
                "food": f["food"],
                "amount": f["amount"],
                "kcal": f["kcal"],
                "protein": f["protein"],
                "fat": f["fat"],
                "carbs": f["carbs"],
            })

    if rows:
        save_log(pd.DataFrame(rows), date_key)

    st.session_state.log_dirty = False
    
if st.button("保存"):
    rows = []
    for meal, foods in st.session_state.foods_added[date_key].items():
        for f in foods:
            rows.append({
                "date": date_key,
                "meal": meal,
                "food": f["food"],
                "amount": f["amount"],
                "kcal": float(f["kcal"]),
                "protein": float(f["protein"]),
                "fat": float(f["fat"]),
                "carbs": float(f["carbs"]),
            })

    if rows:
        save_log(pd.DataFrame(rows), date_key)
        st.success("保存しました")
        st.rerun()
    else:
        st.info("保存するデータがありません")
