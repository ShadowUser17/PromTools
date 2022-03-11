#!/bin/bash
[[ -n "$1" && -f "$1/requirements.txt" ]] && {
    [[ ! -d "./env" ]] && {
        python3 -m venv env && {
            ./env/bin/pip install --upgrade pip setuptools
            ./env/bin/pip install -r "$1/requirements.txt"
        }
    }

    [[ -d "./env" ]] && {
        ./env/bin/pip list
    }
}
