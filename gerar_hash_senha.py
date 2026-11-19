"""Utilitário de linha de comando para gerar o hash bcrypt de uma senha.

Uso: python gerar_hash_senha.py
Cole o hash gerado no campo "password" de .streamlit/secrets.toml.
"""
import getpass

import streamlit_authenticator as stauth

if __name__ == "__main__":
    senha = getpass.getpass("Digite a senha a ser hasheada: ")
    print(stauth.Hasher.hash(senha))
