#!/bin/bash

commands=(
    "uv run python main.py './images/data_cleaned/ct/Covid (100).png' ./output.png --predictive-xor-8x8 --dump-stats --gray-pixels"
    "uv run python main.py './images/data_cleaned/ct/Covid (101).png' ./output.png --predictive-xor-8x8 --dump-stats --gray-pixels"
    "uv run python main.py './images/data_cleaned/ct/Covid (1000).png' ./output.png --predictive-xor-8x8 --dump-stats --gray-pixels"
    "uv run python main.py './images/data_cleaned/ct/Covid (1001).png' ./output.png --predictive-xor-8x8 --dump-stats --gray-pixels"
    "uv run python main.py './images/data_cleaned/ct/Covid (1002).png' ./output.png --predictive-xor-8x8 --dump-stats --gray-pixels"
    "uv run python main.py './images/data_cleaned/mri/1 no.jpeg' ./output.png --predictive-xor-8x8 --dump-stats --gray-pixels"
    "uv run python main.py './images/data_cleaned/mri/2 no.jpeg' ./output.png --predictive-xor-8x8 --dump-stats --gray-pixels"
    "uv run python main.py './images/data_cleaned/mri/17 no.jpg' ./output.png --predictive-xor-8x8 --dump-stats --gray-pixels"
    "uv run python main.py './images/data_cleaned/mri/18 no.jpg' ./output.png --predictive-xor-8x8 --dump-stats --gray-pixels"
    "uv run python main.py './images/data_cleaned/mri/19 no.jpg' ./output.png --predictive-xor-8x8 --dump-stats --gray-pixels"
    "uv run python main.py './images/data_cleaned/xray/IM-0001-0001.jpeg' ./output.png --predictive-xor-8x8 --dump-stats --gray-pixels"
    "uv run python main.py './images/data_cleaned/xray/IM-0003-0001.jpeg' ./output.png --predictive-xor-8x8 --dump-stats --gray-pixels"
    "uv run python main.py './images/data_cleaned/xray/IM-0005-0001.jpeg' ./output.png --predictive-xor-8x8 --dump-stats --gray-pixels"
    "uv run python main.py './images/data_cleaned/xray/IM-0006-0001.jpeg' ./output.png --predictive-xor-8x8 --dump-stats --gray-pixels"
    "uv run python main.py './images/data_cleaned/xray/IM-0007-0001.jpeg' ./output.png --predictive-xor-8x8 --dump-stats --gray-pixels"
)

for cmd in "${commands[@]}"; do
    echo ">>> $cmd"
    eval "$cmd"
    sleep 10
done
