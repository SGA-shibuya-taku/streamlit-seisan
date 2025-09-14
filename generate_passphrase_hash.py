#!/usr/bin/env python3
"""
パスフレーズのハッシュ値生成ユーティリティ

使用方法：
1. このスクリプトを実行
2. パスフレーズを入力
3. 生成されたハッシュ値をsecrets.tomlのPASSPHRASE_HASHに設定
"""

import hashlib


def generate_passphrase_hash():
    print("=== パスフレーズハッシュ生成ツール ===")
    print()
    print("セキュリティのため、パスフレーズはハッシュ化して保存されます。")
    print("このツールで生成したハッシュ値をsecrets.tomlに設定してください。")
    print()
    
    passphrase = input("パスフレーズを入力してください: ")
    
    if len(passphrase) < 8:
        print("⚠️  警告: パスフレーズは8文字以上にすることを推奨します")
    
    # SHA256ハッシュ生成
    hash_value = hashlib.sha256(passphrase.encode()).hexdigest()
    
    print()
    print("=== 生成結果 ===")
    print(f"パスフレーズ: {passphrase}")
    print(f"ハッシュ値: {hash_value}")
    print()
    print("secrets.tomlに以下の行を追加してください:")
    print(f'PASSPHRASE_HASH = "{hash_value}"')
    print()
    print("⚠️  パスフレーズは忘れないように安全な場所に保管してください！")


if __name__ == "__main__":
    generate_passphrase_hash()