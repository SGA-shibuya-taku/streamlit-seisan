import datetime
import random
import time
import requests
import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 認証設定
AUTH_CONFIG = st.secrets["AUTH"]
PIN_CODE = AUTH_CONFIG["PIN_CODE"]
SESSION_TIMEOUT_MINUTES = AUTH_CONFIG.get("SESSION_TIMEOUT_MINUTES", 30)


# 認証関数
def check_authentication():
    """認証チェック関数"""
    # セッション状態の初期化
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.auth_time = None

    # セッションタイムアウトチェック
    if st.session_state.authenticated and st.session_state.auth_time:
        elapsed_minutes = (time.time() - st.session_state.auth_time) / 60
        if elapsed_minutes > SESSION_TIMEOUT_MINUTES:
            st.session_state.authenticated = False
            st.session_state.auth_time = None
            st.warning(
                f"セッションがタイムアウトしました（{SESSION_TIMEOUT_MINUTES}分）"
            )

    return st.session_state.authenticated


def show_login_form():
    """ログイン画面表示"""
    st.title("資産管理アプリ")
    st.markdown("---")

    # PINコード認証のみ
    st.subheader("PINを入力")
    pin_input = st.text_input("暗証番号", type="password", placeholder="PINを入力")

    if st.button("ログイン", type="primary"):
        if pin_input == PIN_CODE:
            st.session_state.authenticated = True
            st.session_state.auth_time = time.time()
            st.success("認証成功！")
            st.rerun()
        else:
            st.error("暗証番号が間違っています")

def get_pokemon(id):
    url = f"https://pokeapi.co/api/v2/pokemon/{id}"
    response = requests.get(url)
    data = response.json()
    pokemon = {}
    response_sp = requests.get(data["species"]["url"])
    pokemon["name"] = response_sp.json()["names"][0]["name"]
    pokemon["image"] = data["sprites"]["other"]["showdown"]["front_default"]

    return pokemon


# Google Sheets API認証
def authenticate_google_sheets():
    google_credentials = st.secrets["GOOGLE_CREDENTIALS"]
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(
        google_credentials, scope
    )
    client = gspread.authorize(credentials)
    return client


# スプレッドシートへの接続
def get_google_sheet(sheet_name):
    client = authenticate_google_sheets()
    sheet = client.open(sheet_name).sheet1  # 最初のシートを取得
    return sheet


def get_google_sheet2(sheet_name):
    client = authenticate_google_sheets()
    # 2番目のシートを取得（インデックスは0から始まる）
    sheet = client.open(sheet_name).get_worksheet(1)
    return sheet


# スプレッドシートからデータ読み込み
def load_data(sheet):
    records = sheet.get_all_records()  # シート全体を取得
    return pd.DataFrame(records)


# 精算内容保存
def save_settlement_history(sheet, data):
    # データを追加（2次元リスト形式）
    values = data.values.tolist()
    if values:
        sheet.append_rows(values)


# データフレームをスプレッドシートに保存
def save_data(sheet, data):
    sheet.clear()  # シート内容をクリア
    sheet.update(
        [data.columns.values.tolist()] + data.values.tolist()
    )  # ヘッダーとデータを書き込み

# メインアプリ
if not check_authentication():
    show_login_form()
    st.stop()

# アプリのタイトル
st.title("家計管理アプリ")

# スプレッドシート名
SHEET_NAME = "kakei_seisan"

# スプレッドシートへの接続
sheet = get_google_sheet(SHEET_NAME)
history_sheet = get_google_sheet2(SHEET_NAME)

# データ読み込み
try:
    data = load_data(sheet)
except Exception:
    data = pd.DataFrame(columns=["Person", "Date", "Amount", "Content", "Place"])

name1 = st.secrets.NAME1
name2 = st.secrets.NAME2

tabs = st.tabs(["記録", "精算履歴"])

with tabs[0]:

    # 入力フォーム
    st.header("支出の記録")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader(name1)
        person_1_date = st.date_input(f"日付（{name1}）")
        person_1_amount = st.number_input(f"金額（{name1}）", min_value=0, step=100)
        sub_col1, sub_col2 = col1.columns(2)
        person_1_content = sub_col1.radio(f"分類({name1})", ["食費", "その他"])
        person_1_place = sub_col2.text_input(f"場所({name1})")
        if st.button(f"追加（{name1}）"):
            new_row = {
                "Person": name1,
                "Date": str(person_1_date),
                "Amount": person_1_amount,
                "Content": person_1_content,
                "Place": person_1_place
            }
            data = pd.concat([data, pd.DataFrame([new_row])], ignore_index=True)
            save_data(sheet, data)
            st.success(f"{name1} の支出が追加されました！")

    with col2:
        st.subheader(name2)
        person_2_date = st.date_input(f"日付（{name2}）")
        person_2_amount = st.number_input(f"金額（{name2}）", min_value=0, step=100)
        sub_col1, sub_col2 = col2.columns(2)
        person_2_content = sub_col1.radio(f"分類({name2})", ["食費", "その他"])
        person_2_place = sub_col2.text_input(f"場所({name2})")
        if st.button(f"追加（{name2}）"):
            new_row = {
                "Person": name2,
                "Date": str(person_2_date),
                "Amount": person_2_amount,
                "Content": person_2_content,
                "Place": person_2_place,
            }
            data = pd.concat([data, pd.DataFrame([new_row])], ignore_index=True)
            save_data(sheet, data)
            st.success(f"{name2} の支出が追加されました！")

    # 表の表示
    st.header("支出一覧")
    st.dataframe(data)

    # 精算機能
    st.header("精算")
    if st.button("精算する"):
        # Personごとの合計金額を計算
        total_person_1 = data[data["Person"] == name1]["Amount"].sum()
        total_person_2 = data[data["Person"] == name2]["Amount"].sum()

        # 精算計算
        total_spent = total_person_1 + total_person_2
        equal_share = total_spent / 2
        difference = total_person_1 - total_person_2

        if difference > 0:
            payer = name2
            payee = name1
            amount_to_pay = abs(difference) / 2
        elif difference < 0:
            payer = name1
            payee = name2
            amount_to_pay = abs(difference) / 2
        else:
            payer, payee, amount_to_pay = None, None, None

        # 結果表示
        if payer and payee:
            st.write(f"{payer} が {payee} に ¥{amount_to_pay:.0f} 支払う必要があります。")
        else:
            st.write("精算する必要はありません。")

        # 精算履歴の記録
        history_data = pd.DataFrame(
            [
                {
                    "精算日": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "支払者": payer,
                    "金額": amount_to_pay,
                    "総支出": total_spent,
                }
            ]
        )
        save_settlement_history(history_sheet, history_data)

        # データクリア
        data = pd.DataFrame(columns=["Person", "Date", "Amount", "Content", "place"])
        save_data(sheet, data)

        st.success("精算が完了しました。")

with tabs[1]:
    data_histry = load_data(history_sheet)
    st.write(data_histry)

    pokemon_id = random.randrange(800)
    pokemon = get_pokemon(pokemon_id)
    # st.write(f"No.{pokemon_id} " + pokemon["name"])
    st.image(pokemon["image"])
