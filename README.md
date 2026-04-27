# streamlit-seisan

Streamlit を使った資産管理・家計簿・精算アプリです。Google Sheets をバックエンドのデータストアとして使用します。

## 機能

| ファイル | 機能 |
|---|---|
| `app.py` | メインアプリ・認証管理 |
| `app_assets.py` | 資産管理 |
| `app_kakeibo.py` | 家計簿 |
| `app_local_save.py` | ローカル保存 |

## 技術スタック

- [Streamlit](https://streamlit.io/)
- [pandas](https://pandas.pydata.org/)
- [gspread](https://docs.gspread.org/) （Google Sheets API）
- [Plotly](https://plotly.com/python/)
- Google OAuth2（サービスアカウント認証）

## セットアップ

### 1. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 2. Streamlit Secrets の設定

`.streamlit/secrets.toml` を作成し、以下の内容を設定してください。

```toml
[AUTH]
PIN_CODE = "your_pin_code"
SESSION_TIMEOUT_MINUTES = 30

[gcp_service_account]
# Google サービスアカウントの認証情報（JSON キーの内容）
type = "service_account"
project_id = "your_project_id"
private_key_id = "..."
private_key = "..."
client_email = "..."
client_id = "..."
```

### 3. アプリの起動

```bash
streamlit run app.py
```

## 認証

PIN コード認証を使用しています。セッションタイムアウトはデフォルト 30 分です（`secrets.toml` の `SESSION_TIMEOUT_MINUTES` で変更可）。
